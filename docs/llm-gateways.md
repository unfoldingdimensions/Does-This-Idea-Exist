# LLM gateways — backend + admin panel contract

**Status:** backend shipped (`feat/llm-gateway-settings`); the frontend section **is built** — `components/admin-llm-section.tsx` and the fourth `llm` entry in `components/admin-panel.tsx`, landed with Phase 6 (2026-09-16, ledger `PASS`). §4 below is the contract it was built to, unchanged.
**Read with:** `docs/codebase-comprehension.md` §4.2 (HTTP surface) · `docs/backend-checklist.md` §6 (the invariants that must not regress) · `backend/app/gateways.py` (the registry and the resolver).

---

## 1. What this is

The backend talks to exactly one OpenAI-compatible chat-completions surface. Which provider that is used to be hardcoded in `backend/.env` (`LLM_BASE_URL` + `LLM_MODEL` + `OPENCODE_GO_API_KEY`) and read once at import. An operator holding keys for several providers had no way to switch without editing `.env` and restarting, and no way to check that a key works.

Now the owner can, from the admin panel:

* see every known gateway and its state,
* paste / replace / clear an API key per gateway,
* override the model and the base URL per gateway,
* make one gateway **active** (the one every seed and every teardown capture then uses),
* **test** a gateway with a real one-line completion before switching to it.

Five gateways ship in the registry:

| id | label | default base URL | env fallback |
|---|---|---|---|
| `opencode-go` | OpenCode Go | `https://opencode.ai/zen/go/v1` | `OPENCODE_GO_API_KEY` |
| `opencode-zen` | OpenCode Zen | `https://opencode.ai/zen/v1` | `OPENCODE_ZEN_API_KEY` |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| `gemini` | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY`, `GOOGLE_API_KEY` |
| `command-code` | Command Code | `https://api.commandcode.ai/provider/v1` | `COMMAND_CODE_API_KEY` |

All five are OpenAI-compatible and authenticate with a bearer token. Every base URL is **overridable per gateway** from the panel, so when a provider moves an endpoint that is a settings edit rather than a code change.

**Resolution order, at call time:** stored settings → environment variable → registry default. Because settings win, the panel always describes reality; because the environment is still the fallback, an install that has only ever edited `.env` behaves exactly as it did before, and nothing needs migrating.

---

## 2. The four rules the API obeys

These are enforced in the backend and the UI must not fight them:

1. **A stored key is write-only.** No response ever contains it. The API reports `has_key`, `key_source` (`settings` | `env` | `none`) and `key_hint` (last 4 characters, e.g. `…cdef`; short keys report the literal string `set` instead, because 4 characters of an 8-character key is half the key). The UI must never render a key it did not receive — show the hint and an empty password field.
2. **The key never travels in a URL.** Gemini's *native* API takes `?key=…`; a query-param secret ends up in URLs, logs and exception text, so the backend deliberately uses Gemini's OpenAI-compatible surface with a bearer token instead. There is no query-param auth mode to opt into.
3. **Switching is guarded.** Making a gateway active is refused (`400`) when that gateway has no key or no model, because the switch would silently break every seed and capture. A refusal with a reason beats a broken product.
4. **The outbound call is SSRF-guarded.** The base URL is admin-settable now, so the request that carries the key gets the same `netguard` rule every page fetch already gets: loopback, private, link-local, CGNAT and cloud-metadata targets are refused **before a socket opens**. Both `llm_json` and the Test button go through the one guard (`gateways.guard_outbound`). The Test button reports a blocked target as an ordinary failure result (`ok: false` plus the reason), so the panel should render it like any other connection error rather than as a server fault.
   - `ALLOW_PRIVATE_LLM_BASE=1` in `backend/.env` steps the guard aside for a deliberately local model server (Ollama, LM Studio, vLLM on `127.0.0.1`). It is opt-in and documented because it re-opens exactly the target class the guard closes.
   - **Honest limitation, stated rather than implied:** this does not stop a stolen admin token from pointing a gateway at a *public* host the attacker controls and harvesting the key on the next call. The token already governs the archive — treat it as equivalent to control of the keys.

---

## 3. Endpoints

All of these are **admin-gated** (`X-Admin-Token`, the same token the rest of the panel already uses) and rate-limited. They all live under `/api/admin/settings`.

### `GET /api/admin/settings/gateways`

The whole panel state in one call.

```jsonc
{
  "active": "opencode-go",
  "effective": {                       // what an LLM call would use right now
    "gateway_id": "opencode-go",
    "label": "OpenCode Go",
    "base_url": "https://opencode.ai/zen/go/v1",
    "model": "deepseek-v4-flash",
    "has_key": true,
    "key_source": "env",               // settings | env | none
    "ready": true                      // has_key && model — the switch guard
  },
  "gateways": [
    {
      "id": "opencode-go",
      "label": "OpenCode Go",
      "default_base_url": "https://opencode.ai/zen/go/v1",
      "default_model": "deepseek-v4-flash",
      "suggested_models": ["deepseek-v4-flash", "qwen3-coder", "kimi-k2", "grok-code"],
      "docs_url": "https://opencode.ai/docs/go/",
      "notes": "The $10/month OpenCode Go subscription. …",
      "env_vars": ["OPENCODE_GO_API_KEY"],

      "base_url": "https://opencode.ai/zen/go/v1",   // effective
      "model": "deepseek-v4-flash",                  // effective
      "has_key": true,
      "key_source": "env",
      "key_hint": "…cdef",
      "ready": true,
      "is_active": true,

      "overrides": { "api_key": false, "model": false, "base_url": false }
    }
    // …one object per gateway, in registry order
  ]
}
```

Use `default_*` to render "Reset to default" affordances, and `overrides` to show where the operator has diverged. `suggested_models` is a convenience list for a datalist/combobox — the model field is **free text** because providers add models faster than this list changes.

### `GET /api/admin/settings/gateways/{gateway_id}`

One gateway, same object shape as a `gateways[]` entry. `404` for an unknown id.

### `PUT /api/admin/settings/gateways/{gateway_id}`

Patch one gateway. All fields optional:

```jsonc
{ "api_key": "sk-…", "model": "openai/gpt-5", "base_url": "https://openrouter.ai/api/v1" }
```

* **Omitted field** → left alone.
* **`null` or `""`** → clears the override, falling back to the environment, then the registry default. This is how "stop using this pasted key" works without deleting anything else.
* Returns the updated gateway object (same shape as above). `404` unknown id · `400` invalid value · `422` unknown body field.
* `base_url` is validated: must be `http(s)`, no credentials in the URL, no query string or fragment. A trailing slash is normalised away.

### `POST /api/admin/settings/gateways/active`

```jsonc
{ "gateway_id": "openrouter" }
```

Returns the full `GET /api/admin/settings/gateways` payload. `400` when the gateway is not `ready` (the message names the env var when there is one) · `404` unknown id.

### `POST /api/admin/settings/gateways/active/reset`

No body. Returns the full payload with the active gateway back to the environment-described default (`opencode-go` unless the environment says otherwise).

### `POST /api/admin/settings/gateways/{gateway_id}/test`

Runs one real, tiny completion (`"Reply with the single word: ok"`, `max_tokens: 16`) against **that** gateway — active or not, so a key can be verified before switching. Always `200` unless the id is unknown (`404`); success and failure are both results:

```jsonc
{ "ok": true,  "gateway_id": "openrouter", "label": "OpenRouter",
  "model": "openai/gpt-5", "base_url": "https://openrouter.ai/api/v1",
  "latency_ms": 812, "http_status": 200, "reply": "ok", "model_echoed": "openai/gpt-5" }

{ "ok": false, "gateway_id": "openrouter", "label": "OpenRouter",
  "model": "openai/gpt-5", "base_url": "https://openrouter.ai/api/v1",
  "latency_ms": 500, "http_status": 401, "error": "{\"error\":{\"message\":\"No auth credentials found\"…" }
```

`error` carries the provider's own text — a wrong model and a bad key are told apart by it, so show it rather than a generic failure line. A keyless gateway returns `ok: false` with `error: "no API key configured for this gateway"` **without making any network call**.

---

## 4. Frontend work

The panel is a `Dialog` with one collapsible `SectionHeader` per area (`components/admin-panel.tsx`: `seed`, `verify`, `health`). This becomes a fourth.

**Suggested shape (follow the existing house style):**

1. `lib/types.ts` — add `LlmGateway`, `LlmGatewaysView` (`{active, effective, gateways}`), `LlmGatewayPatch`, `LlmGatewayTestResult`.
2. `lib/api.ts` — five functions through the existing `adminJson` helper (it already attaches the token and turns a `403` into `AdminUnauthorized`, which is what makes the panel lock itself):
   ```ts
   fetchLlmGateways(): Promise<LlmGatewaysView>                       // GET
   updateLlmGateway(id, patch: LlmGatewayPatch): Promise<LlmGateway>  // PUT
   setActiveLlmGateway(id): Promise<LlmGatewaysView>                  // POST
   resetActiveLlmGateway(): Promise<LlmGatewaysView>                  // POST
   testLlmGateway(id): Promise<LlmGatewayTestResult>                  // POST
   ```
   `testLlmGateway` is a POST, so it already gets the 90 s write deadline; the others are fast local reads/writes.
3. `components/admin-panel.tsx` — add `"llm"` to `AdminSection` and a fourth entry to `sections`, e.g. `<KeyRound />` / "LLM gateways", with a badge when the active gateway is not `ready`.
4. `components/admin-llm-section.tsx` — the new section, matching `admin-health-section.tsx` in structure (a card per gateway, monospace for URLs/models, inline status rows).

**Behaviour that matters:**

* **One card per gateway.** Show: label, `base_url` (mono, wrap), `model`, a key-state pill (`Saved` when `key_source === "settings"`, `From .env` for `env`, `Not set` for `none`), and `Active` on the one that is `is_active`.
* **Key field is write-only.** A `type="password"` input that always starts empty; when `has_key`, the placeholder shows the hint — e.g. `Saved …cdef — paste a new key to replace`. Two explicit actions: **Save key** (`PUT {api_key}`) and **Clear key** (`PUT {api_key: ""}`). Never populate the field with a value the API returned, because it never returns one.
* **Test before you switch.** A **Test** button per card, showing `ok` + `latency_ms` + `reply`, or the provider's `error` text verbatim. This is the button that turns "my key is wrong" into a diagnosis.
* **Make active** on a card that is not `is_active` and is `ready`; disabled with a tooltip ("needs a key" / "needs a model") when it is not — matching the `400` the API would return, so the UI never offers an action that will fail.
* **A switch takes effect on the next LLM call — including calls inside a run already in flight.** A seed job working through 40 candidates resolves the gateway per call, so changing the active gateway mid-run switches it partway through. That is real and worth a one-line note in the section, not a hidden surprise.
* **Switching affects seeds *and* teardown captures.** They share one client. Say so in the section's description line.
* **Reset to default per field**, using `default_base_url` / `default_model` for the placeholder so it is obvious what "empty" means.
* After any successful write, re-render from the response (it is the fresh view) rather than patching state locally.

---

## 5. Operator notes

* **Where the keys live.** `backend/data/settings.db` (`SETTINGS_DB_PATH`), its own SQLite file — never the archive. The archive file gets copied around, backed up and shared, so a secret must not sit in it; the same reasoning that put the founder's app in its own file. The settings file holds **plaintext keys**: this is a local-first, single-user app with no key-management service, so at-rest encryption is not attempted and the honest control is file permissions plus excluding the file from backups. A hosted instance must exclude both `FOUNDER_DB_PATH` and `SETTINGS_DB_PATH`.
* **The env vars are a fallback, not a second source of truth.** If a key is stored for a gateway, the env var for that gateway is ignored. Deleting the stored key falls back to the env var again.
* **A gateway only needs a key in one place.** Setting `GEMINI_API_KEY` in `.env` is enough to make Gemini selectable — the panel is for overrides and switching, not a requirement.
* **The old error message still applies.** When the active gateway is the env-described default and has no key, the LLM error names the env var (`OPENCODE_GO_API_KEY`) as before, so existing runbooks still read correctly.

---

## 6. Deliberately not included

* **No key read-back, ever** — not even masked-with-reveal. Rotation is "paste a new one".
* **No query-parameter auth**, for the reason in §2.
* **No multi-key rotation, no per-job gateway choice, no usage/cost accounting.** One active gateway, resolved per call.
* **No `enabled` flag.** An earlier draft stored one; it gated nothing, so it was removed rather than shipped as a knob that does nothing. If the panel wants a "hide the gateways I don't use" preference, keep it in the client.

---

## 7. Coverage

`backend/tests/functional.py` covers this surface offline (32 checks): the five ids and their base URLs, the admin gate, the resolver's three-step precedence (settings → env → default), the single-env-key fallback, hint-not-key in every response, the switch guard for a keyless and a modelless gateway, unknown-id `404`s, base-URL validation (non-http, credentials, query string, trailing slash), unknown body fields, clearing an override, the settings file being separate from the archive and the founder store, that `llm_json` really posts to the **active** gateway's URL with the key in the `Authorization` header and the active model in the body, that a keyless gateway fails loudly naming its env var, and that testing a keyless gateway never opens a socket.
