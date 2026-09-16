"""LLM enrichment via opencode.go (deepseek-v4-flash), OpenAI-compatible chat/completions.

Verified pitfalls (see plan Part 3.5): deepseek-v4-flash is a REASONING model —
max_tokens >= 8000 or content comes back empty (reasoning eats the budget),
timeout >= 180s, response_format json_object with one retry without it on HTTP 400,
tolerant JSON parse (strip fences), one retry per call.
"""
import json
import re

import httpx

from . import config, gateways

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

# F-06/F-07/F-08/F-09: the TEARDOWN prompt is a SECOND prompt, not an edit of the
# one above. It receives page text that was already fetched (by
# app/pages.py) and returns the four teardown blocks. The rules are in the
# prompt because they are the product's contract: a missing field becomes
# unknown, and a negative is an observation about a page that was actually read.
TEARDOWN_SYSTEM_PROMPT = """You are extracting a competitor teardown from page text that was \
ALREADY fetched for you. You cannot fetch anything: the only pages that exist for \
this task are the ones listed in the input, each with its URL.

Return JSON only, with exactly these keys:
{"features": ["5-10 short capability strings, ONE capability each, in the founder's \
terms ("local files", "public API") rather than marketing terms ("seamless delight")],
 "positioning": "one line: how they describe themselves and who for",
 "pricing": {"free_tier": "string, e.g. 'Free up to 3 docs' or 'No free tier'",
             "plans": [{"name": "string", "price": "string",
                        "period": "monthly|annual|one-time"}]},
 "negatives": [{"claim": "no self-host",
                "observed_on": "the URL of the page you read this on",
                "why": "pricing page lists Free / Pro / Team only"}]}

Rules, all of them binding:
- Use ONLY the supplied page text. Never invent a feature, a price or a plan.
- Use [] and "" when the text does not say. A missing field means UNKNOWN. Do not \
guess, and never treat an unreadable page as absence.
- One capability per item. No grouping, no marketing adjectives.
- A negative is an observation about a page that ENUMERATES the whole set (a pricing \
page listing every tier, a docs index listing every section). observed_on MUST be one \
of the supplied page URLs, and why MUST name what that page actually listed. Never \
write a verdict like "they have no self-host", and never derive absence from a page \
that could not be read.
- Partial output is valid and expected: return what the text supports."""


def teardown_brief(pages_brief: str, page_urls: "list[str] | None" = None) -> str:
    """The user message for the teardown call: the fetched text + the URL
    whitelist a negative may cite. Nothing else is added — the model gets no
    licence to look anything up."""
    urls = ", ".join(page_urls or []) or "(none)"
    return (
        "Pages fetched for this teardown (you may cite these URLs and no others):\n"
        f"{urls}\n\n"
        "Page text:\n"
        f"{pages_brief}"
    )


def llm_teardown(brief: str, max_tokens: int = 8000, timeout: float = 180.0) -> dict:
    """The teardown call (F-06/F-07/F-08, and the negative pass of F-09).

    Same client, same retry policy as llm_json; the only difference is the
    system prompt. Raises RuntimeError like every other LLM call — the caller
    (app/capture.py) turns that into `unknown` rather than retrying into invented
    content.
    """
    return llm_json(brief, max_tokens=max_tokens, timeout=timeout, system_prompt=TEARDOWN_SYSTEM_PROMPT)


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


def _client_config() -> dict:
    """Resolve the active LLM gateway at CALL time, and fail loudly if it is not
    usable.

    Resolved per call rather than at import: that is what makes switching
    gateway (or pasting a new key) in the admin panel take effect without a
    restart. `config.LLM_*` remains the default the resolver falls back to, so
    an install configured only through backend/.env behaves exactly as before.

    The message names the env var for the gateway the environment describes, so
    the old "set OPENCODE_GO_API_KEY" advice still applies to the old setup.
    """
    gateway = gateways.resolve()
    if not gateway["api_key"]:
        env_var = (gateway["env_vars"] or ["the API key"])[0]
        raise RuntimeError(
            f"{gateway['label']} has no API key — add one in Admin -> Settings -> "
            f"LLM gateways, or set {env_var} in backend/.env"
        )
    if not gateway["model"]:
        raise RuntimeError(
            f"{gateway['label']} has no model configured — set one in Admin -> "
            f"Settings -> LLM gateways"
        )
    return gateway


def llm_json(
    user_content: str,
    max_tokens: int = 8000,
    timeout: float = 180.0,
    system_prompt: str = SYSTEM_PROMPT,
) -> dict:
    """Call the active gateway and return parsed JSON. Raises RuntimeError.

    `system_prompt` defaults to the identity-profile prompt, so every existing
    caller keeps its behaviour. The teardown prompt is passed explicitly
    (llm_teardown below) rather than by editing SYSTEM_PROMPT itself: that prompt
    is shared with the GitHub seed path, which has no pricing page to read.
    """
    gateway = _client_config()
    # The key rides in the Authorization header only — never a query parameter,
    # which would put a secret into a URL and therefore into logs and exception
    # text (see app/gateways.py's note on Gemini's ?key=).
    url = f"{gateway['base_url'].rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {gateway['api_key']}",
        "Content-Type": "application/json",
        **gateway["extra_headers"],
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    # Bounded 2 attempts: retry once on ANY failure (gateway intermittently returns
    # empty/invalid completions; a second attempt usually succeeds). Attempt 2 drops
    # response_format for gateways that reject structured output.
    last_error: Exception | None = None
    for with_response_format in (True, False):
        body = {
            "model": gateway["model"],
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
    raise RuntimeError(
        f"LLM call to {gateway['label']} failed after retries: {last_error}"
    ) from last_error
