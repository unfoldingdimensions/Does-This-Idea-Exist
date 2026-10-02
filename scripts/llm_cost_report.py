"""What did that batch cost per row? — the §7.4 report, on the command line.

Phase D's whole deliverable is a measured $/row, so this prints the number with
everything needed to judge it: the denominator it divided by, how much of the
ledger was actually priced, and the rate table version those rows used.

    python scripts/llm_cost_report.py                  # everything, all time
    python scripts/llm_cost_report.py --days 7         # the last week
    python scripts/llm_cost_report.py --job <job-id>   # one batch
    python scripts/llm_cost_report.py --strict         # exit 1 unless confident

READ-ONLY: it opens the archive and the settings store and only SELECTs.
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))

from app import meter  # noqa: E402  (path set above, deliberately after)


def money(value) -> str:
    """`unknown` is not `$0.00` — a missing price must never read as free."""
    return f"${value:,.8f}".rstrip("0").rstrip(".") if isinstance(value, (int, float)) else "unknown"


def num(value, digits: int = 0) -> str:
    if not isinstance(value, (int, float)):
        return "unknown"
    return f"{value:,.{digits}f}"


def render(report: dict) -> str:
    scope = report["scope"]
    where = f"job {scope['job_id']}" if scope["job_id"] else (
        f"since {scope['since']}" if scope["since"] else "all time")
    # The completeness tag has three states, not two: a window with no attempts is
    # EMPTY (nothing to be a floor of), and saying "FLOOR" there would invent doubt
    # about a figure that does not exist.
    if not report["attempts"]:
        cost_tag = "[nothing to report]"
    elif report["cost_complete"]:
        cost_tag = "[complete]"
    else:
        cost_tag = "[FLOOR — some calls are unpriced]"
    lines = [
        "",
        "=" * 72,
        f"LLM SPEND REPORT — {where}",
        "=" * 72,
        "",
        f"  attempts            {num(report['attempts'])}"
        f"  ({num(report['ok_attempts'])} ok, {num(report['failed_attempts'])} failed)",
        f"  retried             {num(report['retried_attempts'])}"
        f"  (share {num(report['retried_share'], 3) if report['retried_share'] is not None else 'unknown'})",
        f"  tokens              {num(report['total_tokens'])}"
        f"  (cached {num(report['cached_tokens'])}, share "
        f"{num(report['cached_share'], 3) if report['cached_share'] is not None else 'unknown'})",
        "",
        f"  total cost          {money(report['cost_usd'])}   {cost_tag}",
        f"  rows                {num(report['rows'])} from the ledger"
        + (f", {num(report['denominator'])} used as the denominator"
           if report['denominator'] != report['rows'] else ""),
        f"  denominator         {report['denominator_source']}",
        f"  TOKENS / ROW        {num(report['tokens_per_row'], 1)}",
        f"  $ / ROW             {money(report['cost_per_row'])}",
        "",
    ]
    counters = report.get("job_counters")
    if counters:
        lines += [
            f"  job                 {counters['status']}"
            + (f" · stop_reason={counters['stop_reason']}" if counters.get("stop_reason") else "")
            + f" · {counters['ok']} filed, {counters['skipped']} already filed,"
              f" {counters['failed']} failed, {counters['done']}/{counters['total']} done",
            "",
        ]
    lines += ["  rates used by these rows:"]
    for version in report["rate_versions"] or [{"price_used": "(no rows)", "attempts": 0}]:
        lines.append(f"    {version['price_used']:<48} {version['attempts']} attempts")
    rates = report["rates"]
    lines += [
        f"    table: {rates['origin']} · version {rates['version']}"
        + (f" · {rates['as_of']}" if rates.get("as_of") else ""),
    ]
    throughput = report.get("throughput") or {}
    if throughput.get("attempts_per_call_second") is not None:
        lines.append(f"  calls               {num(throughput['timed_attempts'])} timed, "
                     f"avg {num(throughput['avg_call_ms'], 0)} ms, "
                     f"{num(throughput['attempts_per_call_second'], 2)} calls/sec of real work")
    failures = report.get("metering_failure_share")
    if not report["metering_failures"]:
        lines.append("  metering failures   0 — nothing was lost")
    elif failures is not None:
        lines.append(f"  metering failures   {num(report['metering_failures'])} — share of "
                     f"attempts {num(failures, 5)}")
    else:
        lines.append(f"  metering failures   {num(report['metering_failures'])} — "
                     f"{report.get('metering_failure_share_scope', 'share not computable')}")
    lines.append("")

    print("\n".join(lines))

    caveats = report["caveats"]
    if caveats:
        print("  READ THIS BEFORE QUOTING THE NUMBER:")
        for caveat in caveats:
            print(f"    - {caveat}")
        print("")
    else:
        print("  No caveats: every attempt in this window was priced and carried usage.\n")

    verdict = "CONFIDENT" if report["confident"] else "NOT CONFIDENT — the $ is a floor"
    print("=" * 72)
    print(f"  VERDICT: {verdict}")
    print(f"     priced {num(report['priced_share'], 3)} · usage present "
          f"{num(report['usage_share'], 3)} · threshold {report['min_share']}")
    print("=" * 72)
    print("")
    return verdict


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="The §7.4 LLM spend report.")
    parser.add_argument("--job", help="one batch id (see the Usage panel or the jobs table)")
    parser.add_argument("--days", type=float, help="window: the last N days")
    parser.add_argument("--min-share", type=float, default=0.9,
                        help="how much of the ledger must be priced/usage-bearing to "
                             "count as confident (default 0.9)")
    parser.add_argument("--json", action="store_true", help="the raw report as JSON")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 unless the report is confident")
    args = parser.parse_args(argv)

    since = meter.window_since(days=args.days) if args.days else None
    report = meter.cost_report(job_id=args.job, since=since, min_share=args.min_share)

    if args.json:
        import json

        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        render(report)

    if args.strict and not report["confident"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
