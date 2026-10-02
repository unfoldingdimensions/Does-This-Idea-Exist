"""Stage candidates from the sourcing channels — the Phase C workhorse.

    # what a channel would bring, writing nothing
    python scripts/source_candidates.py --channel bundles --dry-run

    # the real thing (a small sample, then the full pull with a bigger --limit)
    python scripts/source_candidates.py --all --limit 300
    python scripts/source_candidates.py --all --limit 3000

    # what came back
    python scripts/source_candidates.py --report

    # the documented rollback
    python scripts/source_candidates.py --truncate

Config lives in `backend/data/sourcing.json`: one spec per source, each labelled,
so a staged row can always be traced to the entry that produced it. Nothing in
this script can write to the archive — candidates go to the staging store, which
is its own file (see `backend/app/candidates.py`).
"""
import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))

from app import candidates, config, sources  # noqa: E402  (path set above)

DEFAULT_SOURCES = BACKEND / "data" / "sourcing.json"


def build_client():
    """A real HTTP client — created ONCE, reused across every channel.

    Imported here rather than at module scope so `--report`, `--truncate` and the
    tests never need httpx or a network.
    """
    import httpx

    return httpx.Client(follow_redirects=True)


def load_sources(path: Path) -> dict:
    """The sourcing registry. A missing or broken file is a loud error, not an empty run."""
    if not path.is_file():
        raise SystemExit(f"no sourcing registry at {path} — pass --sources")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain an object of channel -> [specs]")
    return {k: v for k, v in data.items() if not k.startswith("_")}


def specs_for(registry: dict, channel: str, only_label: str | None = None) -> list[dict]:
    """The specs to run for a channel (optionally one labelled source)."""
    entries = registry.get(channel) or []
    if not isinstance(entries, list):
        raise SystemExit(f"{channel}: expected a list of specs")
    if only_label:
        entries = [s for s in entries if (s or {}).get("label") == only_label]
        if not entries:
            raise SystemExit(f"{channel}: no source labelled {only_label!r}")
    return [dict(s or {}) for s in entries]


def run_channel(channel: str, specs: list[dict], *, limit: int, dry_run: bool,
                client, throttle_s: float, max_pages: int, conn=None,
                known: dict | None = None) -> dict:
    """Stage one channel's specs, up to `limit` candidates in total.

    The limit is applied ACROSS the channel's sources (not per source), because
    the caller's question is "how many candidates do I want to look at", and a
    per-source limit would make the answer depend on how many sources there are.
    """
    summary = {"channel": channel, "staged": 0, "duplicates": 0, "known": 0,
               "refused": 0, "errors": [], "sources": []}
    staged_rows: list[dict] = []
    for spec in specs:
        if limit and summary["staged"] + summary["duplicates"] + summary["known"] >= limit:
            break
        remaining = None if not limit else max(
            0, limit - (summary["staged"] + summary["duplicates"] + summary["known"]))
        produced = []
        for candidate in sources.collect(channel, spec, client, throttle_s=throttle_s,
                                         max_pages=max_pages):
            if "_error" in candidate:
                summary["errors"].append(candidate["_error"])
                continue
            if not candidate.get("source_url") and spec.get("source_url"):
                candidate["source_url"] = spec["source_url"]
            if not candidate.get("source") and spec.get("label"):
                candidate["source"] = f"{channel}:{spec['label']}"
            produced.append(candidate)
            if remaining is not None and len(produced) >= remaining:
                break
        summary["sources"].append({"label": spec.get("label"), "found": len(produced)})
        if dry_run:
            staged_rows.extend(produced)
            continue
        result = candidates.stage(produced, channel=channel, conn=conn, known=known)
        summary["staged"] += result["staged"]
        summary["duplicates"] += result["duplicates"]
        summary["known"] += result["known"]
        summary["refused"] += len(result["refused"])
        summary["errors"].extend(
            f"refused {r['candidate'].get('url', '?')}: {r['reason']}" for r in result["refused"])
    if dry_run:
        summary["dry_run_rows"] = staged_rows
        summary["staged"] = len(staged_rows)
    return summary


def render_report(report: dict) -> None:
    """The per-channel yield table — the phase's acceptance artifact."""
    print("\n" + "=" * 84)
    print("CANDIDATE YIELD — staged, not published")
    print("=" * 84)
    print(f"  {'channel':<16} {'found':>6} {'staged':>7} {'known':>6} {'judged':>7} "
          f"{'live':>6} {'walled':>7} {'dead':>6} {'yield':>7}")
    for channel in report["channels"]:
        yield_text = ("unknown" if channel["live_yield"] is None
                      else f"{channel['live_yield'] * 100:.1f}%")
        print(f"  {channel['channel']:<16} {channel['found']:>6} {channel['staged']:>7} "
              f"{channel['already_known']:>6} {channel['judged']:>7} {channel['live']:>6} "
              f"{channel['walled']:>7} {channel['dead']:>6} {yield_text:>7}")
    totals = report["totals"]
    if totals["found"]:
        print("-" * 84)
        total_yield = ("unknown" if totals["live_yield"] is None
                       else f"{totals['live_yield'] * 100:.1f}%")
        print(f"  {'TOTAL':<16} {totals['found']:>6} {totals['staged']:>7} "
              f"{totals['already_known']:>6} {totals['judged']:>7} {totals['live']:>6} "
              f"{'':>7} {'':>6} {total_yield:>7}")
    print(f"\n  {report['sample_note']}")
    print(f"  {report['cost_note']}")
    print("")


def stage_liveness(*, limit: int, workers: int, timeout_s: float) -> dict:
    """Judge staged candidates by RUNNING THE EXISTING AUDITOR, not by re-deciding.

    Liveness rules are the product's most load-bearing judgement (they decide
    whether a company looks real), and `scripts/site_liveness_audit.py` already
    owns them. Re-implementing a lighter version here would give the yield report
    a different definition of "live" from the one the funnel and the verify pass
    use — so this shells out to that CLI with the candidate list and reads its
    `states.json` back.

    Returns `{judged, by_state, run_dir}`; the states are written onto the
    candidate rows (the auditor's vocabulary is validated by `set_liveness`).
    """
    import subprocess
    import tempfile

    pending = candidates.pending_liveness(limit=limit)
    if not pending:
        return {"judged": 0, "by_state": {}, "run_dir": None,
                "note": "every staged candidate already has a liveness verdict"}
    workdir = Path(tempfile.mkdtemp(prefix="candidate-liveness-"))
    source = workdir / "candidates.json"
    source.write_text(json.dumps(
        [{"id": c["id"], "name": c["name"] or "", "url": c["url"]} for c in pending], indent=1),
        encoding="utf-8")
    run_dir = workdir / "run"
    cmd = [sys.executable, str(REPO / "scripts" / "site_liveness_audit.py"), "audit",
           "--file", str(source), "--out", str(run_dir), "--workers", str(workers),
           "--timeout", str(timeout_s), "--quiet"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # The auditor writes its run into a TIMESTAMPED subdirectory of --out
    # (<out>/liveness-YYYY-MM-DD-HHMM/states.json), so the states file is looked up
    # rather than assumed - which is what a first run got wrong.
    found = sorted(run_dir.rglob("states.json"))
    if not found:
        raise SystemExit("the auditor produced no states.json — nothing was judged:\n"
                         + (proc.stderr or proc.stdout or "")[-800:])
    states_path = found[-1]
    states = json.loads(states_path.read_text(encoding="utf-8"))
    by_state: dict[str, int] = {}
    for row in states:
        state = row.get("state")
        if not state:
            continue
        candidates.set_liveness(int(row["id"]), state)
        by_state[state] = by_state.get(state, 0) + 1
    return {"judged": len(states), "by_state": by_state, "run_dir": str(run_dir),
            "auditor_exit": proc.returncode}


def main(argv=None, *, client_factory=build_client) -> int:
    parser = argparse.ArgumentParser(description="Stage candidates from the sourcing channels.")
    parser.add_argument("--channel", choices=sorted(sources.CHANNELS),
                        help="one channel to run")
    parser.add_argument("--all", action="store_true", help="every channel in the registry")
    parser.add_argument("--source", help="one labelled source from the registry")
    parser.add_argument("--limit", type=int, default=0,
                        help="max candidates per channel (0 = no limit)")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES,
                        help="the sourcing registry (default: backend/data/sourcing.json)")
    parser.add_argument("--spec", help="a JSON spec, overriding the registry for one channel")
    parser.add_argument("--dry-run", action="store_true",
                        help="collect and print, write NOTHING to the staging store")
    parser.add_argument("--report", action="store_true", help="print the yield table and exit")
    parser.add_argument("--truncate", action="store_true",
                        help="the documented rollback: empty the staging store and exit")
    parser.add_argument("--throttle", type=float, default=1.0,
                        help="seconds between requests to the same source (default 1.0)")
    parser.add_argument("--max-pages", type=int, default=3,
                        help="page budget per source (default 3)")
    parser.add_argument("--liveness", action="store_true",
                        help="judge staged candidates with the liveness auditor, then report yield")
    parser.add_argument("--liveness-limit", type=int, default=200,
                        help="how many un-judged candidates to check (default 200)")
    parser.add_argument("--workers", type=int, default=12,
                        help="auditor concurrency for --liveness (default 12)")
    parser.add_argument("--json", action="store_true", help="machine-readable summary")
    args = parser.parse_args(argv)

    if args.report or args.liveness:
        judged = None
        if args.liveness:
            judged = stage_liveness(limit=args.liveness_limit, workers=args.workers,
                                    timeout_s=20.0)
            print(f"\nliveness: {judged['judged']} candidate(s) judged "
                  f"{json.dumps(judged['by_state'])}"
                  + (f" — {judged['note']}" if judged.get("note") else ""))
            if judged.get("run_dir"):
                print(f"  auditor run: {judged['run_dir']}")
        report = candidates.yield_report()
        if args.json:
            # Both halves, so a caller that asked for JSON gets the judgement AND
            # the table it feeds, not one of them.
            print(json.dumps({"liveness": judged, "yield_report": report},
                             indent=2, sort_keys=True))
            return 0
        render_report(report)
        return 0

    if args.truncate:
        removed = candidates.truncate()
        print(f"staging store emptied: {removed} candidate(s) removed. "
              f"The archive was not touched.")
        return 0

    if not args.channel and not args.all:
        parser.error("pick --channel NAME, --all, --report or --truncate")

    if args.channel and args.all:
        parser.error("--channel and --all are mutually exclusive")

    registry = load_sources(args.sources)
    channels = (sorted(registry) if args.all else [args.channel])
    for channel in channels:
        if channel not in sources.CHANNELS:
            raise SystemExit(f"{channel!r} is not a channel: {sorted(sources.CHANNELS)}")

    if args.spec:
        try:
            override = json.loads(args.spec)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"--spec is not valid JSON: {exc}") from exc
        channels = [channels[0]]
        registry[channels[0]] = [override]

    # One client for the whole run; `bundles` never touches it.
    needs_network = any(channel != "bundles" for channel in channels)
    client = client_factory() if needs_network else None

    t0 = time.time()
    summaries = []
    conn = None if args.dry_run else candidates.connect()
    try:
        known = None if args.dry_run else candidates.archive_identity()
        for channel in channels:
            specs = specs_for(registry, channel, args.source)
            if not specs:
                summaries.append({"channel": channel, "staged": 0, "duplicates": 0,
                                  "known": 0, "refused": 0,
                                  "errors": [f"{channel}: no sources in the registry"],
                                  "sources": []})
                continue
            summaries.append(run_channel(
                channel, specs, limit=args.limit, dry_run=args.dry_run, client=client,
                throttle_s=args.throttle, max_pages=args.max_pages, conn=conn, known=known))
    finally:
        if conn is not None:
            conn.close()
        if client is not None and hasattr(client, "close"):
            client.close()

    elapsed = time.time() - t0
    if args.json:
        print(json.dumps({"channels": summaries, "elapsed_s": round(elapsed, 2),
                          "dry_run": args.dry_run}, indent=2, sort_keys=True))
        return 0

    print("\n" + "=" * 84)
    print("SOURCING RUN" + (" (DRY RUN — nothing written)" if args.dry_run else ""))
    print("=" * 84)
    for summary in summaries:
        print(f"  {summary['channel']:<16} staged={summary['staged']:<5} "
              f"already-known={summary['known']:<5} duplicates={summary['duplicates']:<5} "
              f"refused={summary['refused']}")
        for source in summary.get("sources", []):
            if source.get("label"):
                print(f"      {source['label']:<28} found {source['found']}")
        for error in summary.get("errors", []):
            print(f"      ! {error}")
    if args.dry_run:
        for summary in summaries:
            for row in summary.get("dry_run_rows", [])[:5]:
                print(f"      would stage: {row['url']}  <- {row['source_url']}")
            extra = len(summary.get("dry_run_rows", [])) - 5
            if extra > 0:
                print(f"      ... and {extra} more")
    print(f"\n  {elapsed:.1f}s. Nothing was published: candidates are staged for review.")
    print("")

    if not args.dry_run:
        render_report(candidates.yield_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
