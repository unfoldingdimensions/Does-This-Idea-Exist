"""SQL UDFs registered on every archive/founder connection.

Phase P task 4: the search ladder (app/search.py) admits a row through
WORD-level distances — term vs the row's words. FTS5's porter tokenizer
cannot answer that (its vocab is stemmed; stemming loses the ladder's
mid-word admissions — probe 2026-09-23: 'base' is inside 'databasely' but
NOT inside stem('databasely')='databas'). The fast path therefore keeps its
own raw-word inverted table, `app_search_word(word, startup_id)`, filled by
triggers that call these UDFs:

  * sx_words(text)   -> JSON array of lowercase word runs ([^\\W_]+ on the
                        casefolded text) — the SAME token shape the ladder's
                        _WORD_RE produces, as JSON so a trigger can walk it.
  * sx_json_len(j)   -> array length (the trigger's loop bound).

Keeping the tokenizer HERE, next to the ladder's regex, is the whole point:
one token definition, provably the ladder's own word space.
"""
from __future__ import annotations

import json
import re

# Identical pattern to search._WORD_RE (import would be circular at module
# level for the API app; the functional suite pins the two in sync).
_WORD_RE = re.compile(r"[^\W_]+")


def words(text) -> str:
    """The text's word runs, casefolded, as a JSON array of strings."""
    if not text:
        return "[]"
    if not isinstance(text, str):
        text = str(text)
    return json.dumps(_WORD_RE.findall(text.casefold()))


def json_len(value) -> int:
    """Length of a JSON string array (a trigger's loop bound)."""
    if value is None:
        return 0
    try:
        parsed = json.loads(value)
        return len(parsed) if isinstance(parsed, list) else 0
    except Exception:  # noqa: BLE001 — a bad payload indexes as zero words
        return 0


def register(conn) -> None:
    """Attach the UDFs to a connection (idempotent per connection)."""
    conn.create_function("sx_words", 1, words)
    conn.create_function("sx_json_len", 1, json_len)
