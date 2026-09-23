"""Search classification & match reasons (F-18) — the server-side contract.

`GET /api/search?q=…` answers *why* a row matched, not merely that it did.  The
classifier walks the plan's v1 ladder and stops at the first rung a row
satisfies:

    exact name → exact domain → phrase/name → tagline → problem-description
        → category/keyword → fuzzy

THE LADDER, MAPPED ONTO THE COLUMNS THAT EXIST TODAY (measured 2026-09-16 on a
migrated copy of the live archive, 1,282 rows):

    rung                matches on                          reachable today
    ------------------  ----------------------------------  --------------------
    exact name          name                                yes — 1,282 rows
    exact domain        the HOST of website_url             yes — 1,282 rows
                        (canonical_domain is written by
                        nothing, so it stays NULL — using it
                        would match zero rows forever)
    phrase / name       name + aliases                      yes — 1,282 rows
    tagline             tagline                             yes — 1,256 rows
    problem-description description; problem_statement /    yes — 1,258 rows
                        target_users once a phase writes   (description)
                        them (nothing does today)
    category / keyword  category; positioning +            category 1,282;
                        features_json when a teardown       keyword 0 today
                        exists                              (no row captured yet)
    fuzzy               the AND gate over the same fields   yes — always

Two consequences of that measurement shape the design:

  * `features_json` / `positioning` are populated only for a competitor a
    founder has actually requested (F-22).  They are legitimate *additional*
    evidence for the keyword rung — used when present, never required — and the
    rung is live on `category` regardless, so it never degrades into a rung that
    only fires for captured rows.
  * `problem_statement` / `target_users` are written by NO phase.  A rung built
    on them alone would match zero rows forever, so there is no rung built on
    them: they are extra fields *inside* the problem rung, which is live on
    `description` today.

DATA-AWARENESS — the one rule that makes a ladder honest.  A rung whose column
is empty for a row simply does not match that row, and the classifier falls
through to the next rung.  An empty column must never match everything: a
NULL LIKE '%%' degenerate rung would make every row look like an intentional
hit, which is the opposite of "this is why it matched".

MATCHING MODEL.  The query is split into WORD terms (`[^\W_]+`, so "note-taking"
→ note, taking and a punctuation-only query such as `%` or `_` yields no terms
at all).  Every term must match somewhere in the row's free text — AND across
terms, mirroring the client's `lib/search.ts` — and the row's score is the
WORST term's distance, never the average.  Distance is 0.0 for an exact word,
0.05 for a prefix ("note" → "notes"), 0.10 for a mid-word hit (4+ characters),
else 1 − SequenceMatcher ratio, and a term matches when its best distance is
≤ FUSE_THRESHOLD (0.3 — the client's own Fuse threshold).

ORDERING — the contracts that must match the client:

  * exact-name (and exact-domain) matches first, then the ladder in order;
  * dead and pivoted rows sink to the bottom, exactly as `scripts/sort-check.ts`
    pins for all five sort keys;
  * stars are a tie-break only — 57 of 1,282 rows even have them, so they can
    never be a ranking signal (a 0-star exact-name hit still beats a 9999-star
    fuzzy one);
  * multi-term queries are AND across terms and score by the worst term.

Deliberate, documented divergence from `lib/search.ts`: the client ranks purely
by Fuse score, so a strong fuzzy hit could outrank a weak phrase hit.  This
endpoint ranks by RUNG first (the ladder is the product requirement) and uses
the score only to order within a rung.  Every *invariant* above is identical,
so a user sees the same shape of answer; only the tie-break between different
rungs is stricter here.  A second, smaller divergence: a 1–2 character term
matches only a whole word (the client's Fuse would fuzzily match it), because a
binary substring rule on a single character matches most of the archive.

PURE READ — a search never triggers a capture.  `POST /api/compare` starts the
JIT capture (F-22); search must not.  A search that fetched pages and called the
LLM would be slow, non-deterministic and expensive on every keystroke, and it
would make "why did this match?" depend on the network.  Search reads stored
data only — do not "fix" this by wiring capture in here.

Done 2026-09-24 (Phase P task 4): the candidate path lives in `fts.py` (+ the
`sx_words` UDF in `udf.py`), which reproduces these exact admission bands so no
match this module would have admitted can be missed — the ranker below is
unchanged, so reasons stay F-18-frozen.  The scan in `rank` is no longer the
only path but is still the REFERENCE the fast path is parity-tested against,
and the live fallback (index unavailable, or a band over the candidate cap).
Measured at 10k: p95 523 ms over 8 query classes, narrow tokens 88-107 ms.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# The reason vocabulary — FROZEN.  Phase 6 renders these exact strings, so they
# live in one place and never change spelling.  Each one is a sentence fragment
# about the FIELD that matched; none of them is a rung name, a code or a score.
# The plan's own examples ("Exact name match", "Similar problem description",
# "Same audience, different approach") are kept verbatim.
# ---------------------------------------------------------------------------
REASON_EXACT_NAME = "Exact name match"
REASON_EXACT_DOMAIN = "Exact domain match"
REASON_NAME = "Name contains your search"
REASON_TAGLINE = "Tagline mentions it"
REASON_PROBLEM = "Similar problem description"
REASON_AUDIENCE = "Same audience, different approach"
REASON_CATEGORY = "Same category"
REASON_FUZZY = "Similar to your search"

# In ladder order.  A verifier pins that no response ever carries anything else.
REASONS: tuple[str, ...] = (
    REASON_EXACT_NAME,
    REASON_EXACT_DOMAIN,
    REASON_NAME,
    REASON_TAGLINE,
    REASON_PROBLEM,
    REASON_AUDIENCE,
    REASON_CATEGORY,
    REASON_FUZZY,
)

# Ladder rungs, strongest first.  Lower = earlier.
RUNG_EXACT_NAME = 0
RUNG_EXACT_DOMAIN = 1
RUNG_NAME_PHRASE = 2
RUNG_TAGLINE = 3
RUNG_PROBLEM_DESC = 4
RUNG_CATEGORY_KEYWORD = 5
RUNG_FUZZY = 6

RUNG_NAMES = {
    RUNG_EXACT_NAME: "exact name",
    RUNG_EXACT_DOMAIN: "exact domain",
    RUNG_NAME_PHRASE: "phrase/name",
    RUNG_TAGLINE: "tagline",
    RUNG_PROBLEM_DESC: "problem-description",
    RUNG_CATEGORY_KEYWORD: "category/keyword",
    RUNG_FUZZY: "fuzzy",
}

# The client's own Fuse setting (`lib/search.ts`: threshold 0.3).  0 = exact,
# 1 = no match; a term counts as present at or below this distance.
FUSE_THRESHOLD = 0.3
# A phrase rung needs the term to really be *in* that field — a literal word, a
# prefix of one, or a mid-word hit.  A pure fuzzy hit is not "name contains your
# search", so it falls through to the fuzzy rung instead of borrowing a reason
# that would be untrue.
PHRASE_DISTANCE = 0.10

_PREFIX_MIN_LEN = 3      # "no" as a prefix of "notes" is noise, not a match
_MIDWORD_MIN_LEN = 4     # mid-word matching only from 4 characters
_FUZZY_MIN_LEN = 3       # a 1-2 char typo is not a thing

_WORD_RE = re.compile(r"[^\W_]+")   # unicode-aware word runs, underscore excluded
_WS_RE = re.compile(r"\s+")

# Fields the free-text gate may match.  `website_url` is deliberately absent:
# the client's Fuse keys are name/tagline/description/category, and a domain
# query is served by the exact-domain rung instead (via the URL's host).
_FREE_TEXT_FIELDS = (
    "name",
    "aliases",
    "tagline",
    "description",
    "problem_statement",
    "target_users",
    "category",
    "positioning",
    "features_json",
)

# Which fields each rung reads.
_NAME_FIELDS = ("name", "aliases")
_DESCRIPTION_FIELDS = ("description", "problem_statement")
_KEYWORD_FIELDS = ("positioning", "features_json")


@lru_cache(maxsize=1 << 16)
def _ratio(a: str, b: str) -> float:
    """Cached SequenceMatcher ratio — the same word pair recurs across rows."""
    return SequenceMatcher(None, a, b).ratio()


def normalize(text: str | None) -> str:
    """Casefold + collapse whitespace.  Used for the equality rungs only."""
    return _WS_RE.sub(" ", (text or "").strip()).casefold()


def query_terms(q: str | None) -> list[str]:
    """The query as WORD terms.  Empty for a blank or punctuation-only query.

    This is why `q=%` and `q=_` cannot dump the archive: they are not words, so
    they are not terms, and they never become a LIKE pattern (this module builds
    no SQL at all — the archive is already in memory).
    """
    return _WORD_RE.findall(normalize(q))


def domain_key(value: str | None) -> str:
    """The host of a URL (or a bare domain), www-stripped and lowercased."""
    raw = (value or "").strip()
    if "://" in raw:
        host = urlparse(raw).hostname or ""
    else:
        host = raw.split("/", 1)[0]
    host = host.split(":", 1)[0].strip().lower()
    return host[4:] if host.startswith("www.") else host


def _looks_like_domain(q: str) -> bool:
    host = domain_key(q)
    return "." in host and " " not in q.strip() and not host.startswith(".")


def _words(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.casefold()))


@dataclass(frozen=True)
class _Field:
    """One column, precomputed once per row: the lowered text + its word set."""
    text: str
    words: frozenset[str]


def _distance(term: str, field: _Field) -> float:
    """Distance from `term` to the best occurrence inside one field.

    0.0 exact word / 0.05 prefix / 0.10 mid-word / 1-ratio fuzzy / 1.0 no match.
    """
    if not field.words:
        return 1.0
    if term in field.words:
        return 0.0
    if len(term) >= _PREFIX_MIN_LEN and term in field.text:
        # The term is only word characters, so an occurrence in the raw text
        # always sits inside a single word run — no boundary can be straddled.
        if any(w.startswith(term) for w in field.words):
            return 0.05
        if len(term) >= _MIDWORD_MIN_LEN:
            return 0.10
        return 1.0
    if len(term) >= _FUZZY_MIN_LEN:
        best = 1.0
        tlen = len(term)
        for word in field.words:
            if abs(len(word) - tlen) > 2:
                continue
            d = 1.0 - _ratio(term, word)
            if d < best:
                best = d
        return best
    return 1.0


def _best_over(term: str, fields: dict[str, _Field], names: tuple[str, ...]) -> float:
    best = 1.0
    for name in names:
        d = _distance(term, fields[name])
        if d < best:
            best = d
            if best == 0.0:
                break
    return best


@dataclass(frozen=True)
class Hit:
    """One classified row: the archive row, the rung it landed on, its score."""
    row: dict
    rung: int
    score: float
    reason: str


def _dead_order(row: dict) -> int:
    """Dead AND pivoted sink — the rule scripts/sort-check.ts pins for every
    sort key, kept identical here."""
    return 1 if row.get("status") in ("dead", "pivoted") else 0


def _order(hit: Hit) -> tuple:
    """Dead last, then the ladder, then the worst-term score, then — only then —
    stars as a tie-break, then a deterministic name/id tail so equal rows never
    swap places between calls."""
    row = hit.row
    return (
        _dead_order(row),
        hit.rung,
        hit.score,
        -(row.get("stars") or 0),
        (row.get("name") or "").casefold(),
        row.get("id") or 0,
    )


def classify_rows(rows: list[dict], q: str | None) -> list[Hit]:
    """Classify and order `rows` for `q`.  Empty when `q` has no word terms."""
    q_norm = normalize(q)
    terms = query_terms(q)
    if not terms:
        return []
    q_domain = domain_key(q_norm) if _looks_like_domain(q_norm) else None

    hits: list[Hit] = []
    for row in rows:
        fields = {
            name: _Field(text=(row.get(name) or "").casefold(), words=frozenset(_words(row.get(name) or "")))
            for name in _FREE_TEXT_FIELDS
        }
        # Per term: the best (smallest) distance across every free-text field.
        # The AND gate needs each term to land somewhere; the row's score is the
        # WORST term's distance, never the average.
        term_best = {term: _best_over(term, fields, _FREE_TEXT_FIELDS) for term in terms}
        gate = all(d <= FUSE_THRESHOLD for d in term_best.values())

        if normalize(row.get("name")) == q_norm:
            rung, reason = RUNG_EXACT_NAME, REASON_EXACT_NAME
        elif q_domain is not None and domain_key(row.get("website_url")) == q_domain:
            rung, reason = RUNG_EXACT_DOMAIN, REASON_EXACT_DOMAIN
        else:
            # Category is an equality match, so it survives even when the term
            # gate cannot fire (a short category slug like "ai" is a word, but
            # the gate would still need it in free text).
            category_hit = normalize(row.get("category")) == q_norm
            if not gate and not category_hit:
                continue
            if all(_best_over(t, fields, _NAME_FIELDS) <= PHRASE_DISTANCE for t in terms):
                rung, reason = RUNG_NAME_PHRASE, REASON_NAME
            elif all(_best_over(t, fields, ("tagline",)) <= PHRASE_DISTANCE for t in terms):
                rung, reason = RUNG_TAGLINE, REASON_TAGLINE
            elif all(_best_over(t, fields, _DESCRIPTION_FIELDS) <= PHRASE_DISTANCE for t in terms):
                rung, reason = RUNG_PROBLEM_DESC, REASON_PROBLEM
            elif all(_best_over(t, fields, ("target_users",)) <= PHRASE_DISTANCE for t in terms):
                # Latent today: nothing writes target_users.  Kept because it is
                # where the audience actually lives, and the reason is frozen.
                rung, reason = RUNG_PROBLEM_DESC, REASON_AUDIENCE
            elif category_hit:
                rung, reason = RUNG_CATEGORY_KEYWORD, REASON_CATEGORY
            elif all(_best_over(t, fields, _KEYWORD_FIELDS) <= PHRASE_DISTANCE for t in terms):
                # The keyword half of the rung: a teardown's own positioning /
                # feature text.  The vocabulary has no "keyword" string and
                # "Same category" would be false here, so the honest fragment is
                # the plan's own "Similar problem description" — the row's own
                # description of what it does.  (Judgement call, documented in
                # the ledger.)
                rung, reason = RUNG_CATEGORY_KEYWORD, REASON_PROBLEM
            elif gate:
                rung, reason = RUNG_FUZZY, REASON_FUZZY
            else:
                continue

        score = 0.0 if rung <= RUNG_EXACT_DOMAIN else max(term_best.values())
        hits.append(Hit(row=row, rung=rung, score=score, reason=reason))

    hits.sort(key=_order)
    return hits


def rank(rows: list[dict], q: str | None, limit: int | None = None) -> list[dict]:
    """The response payload: each row plus its `reason`, in ladder order."""
    hits = classify_rows(rows, q)
    if limit is not None:
        hits = hits[:limit]
    return [{**hit.row, "reason": hit.reason} for hit in hits]
