"""LLM enrichment via opencode.go (deepseek-v4-flash), OpenAI-compatible chat/completions.

Verified pitfalls (see plan Part 3.5): deepseek-v4-flash is a REASONING model —
max_tokens >= 8000 or content comes back empty (reasoning eats the budget),
timeout >= 180s, response_format json_object with one retry without it on HTTP 400,
tolerant JSON parse (strip fences), one retry per call.
"""
import json
import re

import httpx

from . import config

SYSTEM_PROMPT = (
    "You are an expert startup researcher. You receive evidence about a startup "
    "(GitHub repo metadata and/or homepage text). Produce a concise, accurate startup "
    "profile as JSON only, with exactly these keys:\n"
    '{"name": "human-friendly display name of the startup/product (e.g. \\"Notion\\", '
    'not the repo slug)",\n'
    '"tagline": "one line, at most 12 words, describing what it does",\n'
    '"description": "2-3 sentences: what it is, who it is for, what problem it solves",\n'
    '"category": "one of: productivity, ai, devtools, desktop, freelance, finance, '
    'health, education, ecommerce, social, media, other",\n'
    '"founded": "YYYY or YYYY-MM-DD founding year ONLY if the evidence states it '
    'explicitly (e.g. \\"Founded in 2015\\", \\"est. 2012\\", \\"since 2016\\"); otherwise null"}\n'
    "Use only evidence present in the input. Never invent facts. "
    "If a name is already provided in the input, use it as-is."
)


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def llm_json(user_content: str, max_tokens: int = 8000, timeout: float = 180.0) -> dict:
    """Call the LLM with a system prompt and return parsed JSON. Raises RuntimeError."""
    if not config.LLM_API_KEY:
        raise RuntimeError("OPENCODE_GO_API_KEY not set in backend/.env")
    url = f"{config.LLM_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # Bounded 2 attempts: retry once on ANY failure (gateway intermittently returns
    # empty/invalid completions; a second attempt usually succeeds). Attempt 2 drops
    # response_format for gateways that reject structured output.
    last_error: Exception | None = None
    for with_response_format in (True, False):
        body = {
            "model": config.LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
        if with_response_format:
            body["response_format"] = {"type": "json_object"}
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content") or ""
            if not content:
                raise RuntimeError(
                    f"LLM returned empty content (finish_reason={choice.get('finish_reason')})"
                )
            return _parse_json(content)
        except Exception as exc:  # noqa: BLE001 — retry once, then surface the real error
            last_error = exc
    raise RuntimeError(f"LLM call failed after retries: {last_error}") from last_error
