"""LLM gateways — the provider registry, its admin-managed settings, and the
runtime resolution every LLM call goes through.

The product talks to one OpenAI-compatible chat-completions surface, but an
operator may hold keys for several providers and want to switch between them
without editing `backend/.env` and restarting. This module is that switch.

Three layers, deliberately separate:

  * **The registry** (`GATEWAYS`) is CODE: which gateways exist, their default
    base URL, their env-var names, their doc link. Adding a provider is one
    entry here, not a new code path.
  * **The settings store** is DATA, in its OWN SQLite file
    (`config.SETTINGS_DB_PATH`, never the archive): the operator's key, model
    override and base-URL override per gateway, plus which
    gateway is active. Secrets do not belong in the archive file — that file
    gets copied, backed up and shared (the phase verifiers copy it around), and
    hosting already treats the founder DB as excluded from backups. Same
    reasoning, same treatment.
  * **The resolution** (`resolve()`) merges the two at call time: settings win,
    then the environment, then the registry default. That order is what makes
    the feature additive — with an empty settings store and today's `.env`, the
    resolved gateway is exactly the one `config.py` has always described, so
    nothing about the current setup changes.

Security rules that are not negotiable here:

  * **The key is never returned to a client.** The admin surface exposes
    `has_key` and a `key_hint` (last 4 characters); the raw value is write-only.
  * **The key never travels in a URL.** Gemini's native API takes `?key=…`,
    which would put the secret in the `httpx` URL — and therefore into any
    exception message or log line. The OpenAI-compatible surface takes a bearer
    token, so every gateway here uses `Authorization`. A query-param auth mode
    is deliberately not supported.
  * **The key is never logged** — not on write, not on error.

`test_gateway()` is the one place that makes a real outbound call, and it is
admin-gated and rate-limited; it never raises, so a bad key is a result rather
than a 500.
"""
import json
import logging
import os
import sqlite3
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from . import config, db

log = logging.getLogger("ideasexist")

# Reserved name for "this key does not name a stored override".
UNSET = object()

# Every gateway is OpenAI-compatible; the few that differ do so only in their
# base URL and in optional attribution headers. Kept as a tuple for a stable
# `GET` order, and keyed by id for lookup.
GATEWAYS: dict[str, dict[str, Any]] = {
    "opencode-go": {
        "label": "OpenCode Go",
        "base_url": "https://opencode.ai/zen/go/v1",
        "env_vars": ("OPENCODE_GO_API_KEY",),
        "env_default": True,          # the LLM_* env vars describe THIS gateway
        "default_model": "deepseek-v4-flash",
        "suggested_models": ("deepseek-v4-flash", "qwen3-coder", "kimi-k2", "grok-code"),
        "docs_url": "https://opencode.ai/docs/go/",
        "notes": "The $10/month OpenCode Go subscription. This is the gateway the "
                 "backend has always used, so an empty settings store resolves here.",
    },
    "opencode-zen": {
        "label": "OpenCode Zen",
        "base_url": "https://opencode.ai/zen/v1",
        "env_vars": ("OPENCODE_ZEN_API_KEY",),
        "default_model": "",
        "suggested_models": ("claude-sonnet-4-5", "gpt-5", "qwen3-coder", "kimi-k2"),
        "docs_url": "https://opencode.ai/docs/zen/",
        "notes": "OpenCode's curated, pay-as-you-go model list. Same auth as Go, a "
                 "different path.",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "env_vars": ("OPENROUTER_API_KEY",),
        "default_model": "",
        "suggested_models": ("anthropic/claude-sonnet-4.5", "openai/gpt-5",
                             "google/gemini-2.5-flash", "deepseek/deepseek-chat"),
        "docs_url": "https://openrouter.ai/docs",
        "notes": "Model ids are vendor-prefixed (vendor/model). Sends the optional "
                 "HTTP-Referer / X-Title attribution headers.",
    },
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_vars": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "default_model": "gemini-2.5-flash",
        "suggested_models": ("gemini-2.5-flash", "gemini-2.5-pro",
                             "gemini-2.5-flash-lite"),
        "docs_url": "https://ai.google.dev/gemini-api/docs/openai",
        "notes": "Uses Gemini's OpenAI-compatible surface with a bearer token. The "
                 "native API's ?key= query parameter is deliberately NOT used — a "
                 "secret in a URL leaks into logs and error messages.",
    },
    "command-code": {
        "label": "Command Code",
        "base_url": "https://api.commandcode.ai/provider/v1",
        "env_vars": ("COMMAND_CODE_API_KEY",),
        "default_model": "",
        "suggested_models": ("claude-sonnet-4-5", "gpt-5", "kimi-k2", "qwen3-coder"),
        "docs_url": "https://commandcode.ai/docs/provider",
        "notes": "Command Code's OpenAI-compatible provider surface. The base URL is "
                 "from their provider docs and is overridable per gateway, so a "
                 "change there is a settings edit rather than a code change.",
    },
}

ACTIVE_KEY = "active_gateway"


# --- the settings store -----------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS gateway_settings (
  gateway_id TEXT PRIMARY KEY,
  api_key    TEXT,
  model      TEXT,
  base_url   TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS app_settings (
  key        TEXT PRIMARY KEY,
  value      TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    """The settings store: its own file, the same WAL/busy-timeout settings."""
    return db.connect_path(config.SETTINGS_DB_PATH)


def init_settings_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _stored(gateway_id: str) -> dict:
    """The stored row for a gateway, or empty defaults."""
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM gateway_settings WHERE gateway_id = ?", (gateway_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {"api_key": "", "model": "", "base_url": ""}
    return {
        "api_key": row["api_key"] or "",
        "model": row["model"] or "",
        "base_url": row["base_url"] or "",
    }


def _store(gateway_id: str, values: dict) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO gateway_settings (gateway_id, api_key, model, base_url, "
            "updated_at) VALUES (?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT(gateway_id) DO UPDATE SET "
            "api_key = excluded.api_key, model = excluded.model, "
            "base_url = excluded.base_url, "
            "updated_at = excluded.updated_at",
            (gateway_id, values["api_key"], values["model"], values["base_url"]),
        )
        conn.commit()
    finally:
        conn.close()


def _app_setting(key: str, value: str | None = None) -> str:
    conn = connect()
    try:
        if value is None:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            return (row["value"] or "") if row else ""
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, value),
        )
        conn.commit()
        return value
    finally:
        conn.close()


# --- helpers ----------------------------------------------------------------

def _require(gateway_id: str) -> dict:
    entry = GATEWAYS.get((gateway_id or "").strip().lower())
    if not entry:
        raise ValueError(
            f"unknown gateway {gateway_id!r}; known: {sorted(GATEWAYS)}"
        )
    return entry


def _norm_base_url(value: str) -> str:
    """An http(s) origin with an optional path — never a scheme we would then
    hand to `httpx` blindly, and never something that could smuggle a key."""
    raw = (value or "").strip().rstrip("/")
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(
            f"base_url must be an http(s) URL, got {value!r}"
        )
    if parsed.username or parsed.password:
        raise ValueError("base_url must not carry credentials in the URL")
    if parsed.query or parsed.fragment:
        raise ValueError("base_url must not carry a query string or fragment")
    return raw


def _env_key(entry: dict) -> str:
    for name in entry.get("env_vars") or ():
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def key_hint(key: str) -> str:
    """A write-only secret's readable fingerprint: never the key itself.

    Short values are not hinted at all — 4 characters of an 8-character key is
    half the key.
    """
    if not key:
        return ""
    if len(key) < 12:
        return "set"
    return f"…{key[-4:]}"


def resolve(gateway_id: str | None = None) -> dict:
    """The gateway an LLM call should use right now.

    Precedence, and it is the whole point of the module:
        settings (stored key/model/base_url)
          → environment (for the gateway the LLM_* vars describe)
          → the registry default.

    Returns `api_key` — the only function here that does, and the only caller is
    the LLM client. Never hand this dict to a response model.
    """
    gid = (gateway_id or _active_id()).strip().lower()
    entry = _require(gid)
    stored = _stored(gid)

    if stored["api_key"]:
        api_key, key_source = stored["api_key"], "settings"
    else:
        env_key = _env_key(entry)
        api_key, key_source = (env_key, "env") if env_key else ("", "none")

    base_url = stored["base_url"]
    model = stored["model"]
    if entry.get("env_default"):
        # This gateway IS what backend/.env describes, so an operator who has
        # only ever edited .env keeps exactly today's behaviour.
        if not base_url:
            base_url = (os.getenv("LLM_BASE_URL") or "").strip().rstrip("/")
        if not model:
            model = (os.getenv("LLM_MODEL") or "").strip()

    return {
        "gateway_id": gid,
        "label": entry["label"],
        "api_key": api_key,
        "key_source": key_source,
        "base_url": base_url or entry["base_url"],
        "model": model or entry["default_model"],
        "is_default": bool(entry.get("env_default")),
        "env_vars": list(entry.get("env_vars") or ()),
        "extra_headers": _extra_headers(gid),
    }


def _extra_headers(gateway_id: str) -> dict:
    """Attribution headers, where the provider documents them. Nothing secret."""
    if gateway_id == "openrouter":
        return {
            "HTTP-Referer": config.FRONTEND_ORIGIN,
            "X-Title": "IdeaExists",
        }
    return {}


def _active_id() -> str:
    stored = _app_setting(ACTIVE_KEY)
    if stored and stored in GATEWAYS:
        return stored
    # Nothing chosen yet: the gateway the environment already describes, or the
    # first one that actually has a key, so a fresh install with only
    # GEMINI_API_KEY set does something sensible.
    for gid, entry in GATEWAYS.items():
        if entry.get("env_default") and _env_key(entry):
            return gid
    for gid, entry in GATEWAYS.items():
        if _env_key(entry):
            return gid
    return next(iter(GATEWAYS))


def active_id() -> str:
    return _active_id()


def public_view(gateway_id: str) -> dict:
    """One gateway as the admin panel sees it — no secret, ever."""
    entry = _require(gateway_id)
    stored = _stored(gateway_id)
    resolved = resolve(gateway_id)
    return {
        "id": gateway_id,
        "label": entry["label"],
        "default_base_url": entry["base_url"],
        "default_model": entry["default_model"],
        "suggested_models": list(entry.get("suggested_models") or ()),
        "docs_url": entry.get("docs_url", ""),
        "notes": entry.get("notes", ""),
        "env_vars": list(entry.get("env_vars") or ()),
        # effective config
        "base_url": resolved["base_url"],
        "model": resolved["model"],
        "has_key": bool(resolved["api_key"]),
        "key_source": resolved["key_source"],
        "key_hint": key_hint(resolved["api_key"]),
        "ready": bool(resolved["api_key"]) and bool(resolved["model"]),
        # what the operator has actually overridden
        "overrides": {
            "api_key": bool(stored["api_key"]),
            "model": bool(stored["model"]),
            "base_url": bool(stored["base_url"]),
        },
        "is_active": gateway_id == _active_id(),
    }


def list_gateways() -> dict:
    """The whole admin view: every gateway, plus what is in effect."""
    resolved = resolve()
    return {
        "active": _active_id(),
        "effective": {
            "gateway_id": resolved["gateway_id"],
            "label": resolved["label"],
            "base_url": resolved["base_url"],
            "model": resolved["model"],
            "has_key": bool(resolved["api_key"]),
            "key_source": resolved["key_source"],
            "ready": bool(resolved["api_key"]) and bool(resolved["model"]),
        },
        "gateways": [public_view(gid) for gid in GATEWAYS],
    }


# --- writes -----------------------------------------------------------------

def update_gateway(
    gateway_id: str,
    *,
    api_key: Any = UNSET,
    model: Any = UNSET,
    base_url: Any = UNSET,
) -> dict:
    """Patch one gateway's stored settings. Omitted fields are left alone.

    `api_key=""` / `model=""` / `base_url=""` CLEAR the override and fall back
    to the environment and the registry default — that is how an operator
    stops using a pasted key without deleting the row.
    """
    _require(gateway_id)
    stored = _stored(gateway_id)

    if api_key is not UNSET:
        if api_key is None:
            stored["api_key"] = ""
        elif isinstance(api_key, str):
            stored["api_key"] = api_key.strip()
        else:
            raise ValueError("api_key must be a string")
    if model is not UNSET:
        if model is None:
            stored["model"] = ""
        elif isinstance(model, str):
            stored["model"] = model.strip()[:120]
        else:
            raise ValueError("model must be a string")
    if base_url is not UNSET:
        if base_url is None:
            stored["base_url"] = ""
        elif isinstance(base_url, str):
            stored["base_url"] = _norm_base_url(base_url)
        else:
            raise ValueError("base_url must be a string")
    _store(gateway_id, stored)
    # The key is never logged — only the fact that one was stored or cleared.
    log.info(
        "gateway %s updated (key=%s model=%s base_url=%s)",
        gateway_id,
        "stored" if stored["api_key"] else "cleared",
        "stored" if stored["model"] else "default",
        "stored" if stored["base_url"] else "default",
    )
    return public_view(gateway_id)


def set_active(gateway_id: str) -> dict:
    """Choose the gateway every LLM call uses.

    Refuses a gateway that would immediately break the LLM paths: no key and no
    model means every seed and capture would answer 502. Better a 400 with the
    reason than a switch that silently breaks the product.
    """
    entry = _require(gateway_id)
    resolved = resolve(gateway_id)
    if not resolved["api_key"]:
        raise ValueError(
            f"{entry['label']} has no API key — paste one first "
            f"(or set {entry['env_vars'][0]} in backend/.env), then make it active"
        )
    if not resolved["model"]:
        raise ValueError(
            f"{entry['label']} has no model — set one before making it active"
        )
    _app_setting(ACTIVE_KEY, gateway_id)
    log.info("active LLM gateway → %s", gateway_id)
    return list_gateways()


def clear_active() -> dict:
    """Go back to the environment-described default."""
    _app_setting(ACTIVE_KEY, "")
    return list_gateways()


# --- connectivity test ------------------------------------------------------

def test_gateway(gateway_id: str, *, timeout: float = 30.0) -> dict:
    """One real, tiny completion against a gateway. Never raises.

    This is the panel's "Test connection" button, and the only place the backend
    makes an LLM call outside a seed/capture. It deliberately does NOT touch the
    capture or seed paths, and it reports the provider's own error text so a bad
    key or a wrong model is diagnosable from the panel.
    """
    resolved = resolve(gateway_id)
    started = time.perf_counter()

    def done(ok: bool, **extra) -> dict:
        return {
            "ok": ok,
            "gateway_id": resolved["gateway_id"],
            "label": resolved["label"],
            "model": resolved["model"],
            "base_url": resolved["base_url"],
            "latency_ms": int((time.perf_counter() - started) * 1000),
            **extra,
        }

    if not resolved["api_key"]:
        return done(False, error="no API key configured for this gateway")
    if not resolved["model"]:
        return done(False, error="no model configured for this gateway")

    url = f"{resolved['base_url'].rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {resolved['api_key']}",
        "Content-Type": "application/json",
        **resolved["extra_headers"],
    }
    body = {
        "model": resolved["model"],
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 16,
        "temperature": 0,
    }
    try:
        r = httpx.post(url, headers=headers, json=body, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — a failed test is a result, not a 500
        return done(False, error=f"{type(exc).__name__}: {exc}"[:300])
    if r.status_code >= 400:
        return done(False, http_status=r.status_code, error=(r.text or "")[:300])
    try:
        payload = r.json()
        choice = (payload.get("choices") or [{}])[0]
        reply = ((choice.get("message") or {}).get("content") or "").strip()
        echoed = payload.get("model") or resolved["model"]
    except Exception as exc:  # noqa: BLE001
        return done(False, http_status=r.status_code, error=f"unparseable body: {exc}"[:300])
    return done(True, http_status=r.status_code, reply=reply[:200], model_echoed=echoed)
