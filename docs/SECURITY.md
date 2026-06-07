# Security Notes

Meero is designed as a local-first assistant. Do not expose the backend to the
public internet without adding stronger authentication, HTTPS, and network
controls.

## Safe Defaults

The default configuration is web-safe:

- `LOCAL_DESKTOP_MODE=false`
- `WEB_SAFE_MODE=true`

Development environments can opt into local desktop automation explicitly.

## API Key

Set `MEERO_API_KEY` to require the `x-meero-api-key` request header for
`/command` and `/settings`.

If `MEERO_API_KEY` is unset, API-key auth is disabled for local development.
For browser use, set the same value as `VITE_MEERO_API_KEY`.

Set `REQUIRE_API_KEY=true` in production-style environments. With that flag
enabled, protected endpoints fail if `MEERO_API_KEY` is missing instead of
silently accepting unauthenticated requests.

`VITE_MEERO_API_KEY` is bundled into browser JavaScript by Vite. Use it only for
local/private deployments. For public exposure, add real user authentication,
reverse-proxy auth, or private network access.

## Metrics

`/metrics` is public by default for local development. Set
`PROTECT_METRICS=true` in production-style environments to require the same
`x-meero-api-key` protection used by `/command`, `/settings`, and
`/debug/health`.

## Rate Limiting

Redis-backed rate limiting is the distributed control. The in-memory
`CLIENT_COMMAND_TIMES` cooldown is process-local and should be treated as a
local usability guard, not a multi-replica production rate limiter.

## Local Desktop Controls

Desktop actions such as app launch/close, screenshots, volume control, tab
control, and scrolling are blocked unless:

- the request is local, and
- `LOCAL_DESKTOP_MODE=true`, and
- `WEB_SAFE_MODE=false`.

Use `WEB_SAFE_MODE=true` for demos or environments where host control should be
disabled.

App launch and close permissions use separate fail-closed allowlists in local
desktop mode:

```env
APP_LAUNCH_ALLOWLIST=notepad,calculator,paint,vscode
APP_CLOSE_ALLOWLIST=notepad,calculator,paint,vscode
APP_FORCE_CLOSE_ALLOWLIST=notepad
```

An empty launch or close allowlist blocks that operation when
`LOCAL_DESKTOP_MODE=true`. Force-close entries only take effect for apps also
listed in `APP_CLOSE_ALLOWLIST`.

## Production Deployment

Production-style Docker configuration keeps desktop automation disabled. Do not
enable `LOCAL_DESKTOP_MODE=true` on a publicly reachable host. Production-style
deployments should use:

```env
WEB_SAFE_MODE=true
LOCAL_DESKTOP_MODE=false
REQUIRE_API_KEY=true
PROTECT_METRICS=true
MEERO_API_KEY=<strong-random-value>
```

## Settings

`/settings` is local-only and accepts only the supported settings schema. Unknown
keys are rejected.

## Local Voice

`/voice/transcribe`, `/voice/synthesize`, and `/voice-command` are local-only
and use the same API-key dependency as other protected endpoints. Audio is
bounded, validated as mono PCM WAV, processed in request-scoped temporary
files, and not retained. Transcripts and synthesized response text remain
excluded from audit logs by default.

## Secrets

Run the repository secret scanner before publishing changes:

```powershell
python scripts/secret_scan.py
```

## Error Details

By default, unhandled exceptions return only `{"error": "Internal server error"}`
without revealing internal details. Set `DEBUG_ERRORS=true` only in development
to include `detail` in error responses. **Never** enable this in production.

## Rate Limiter Resilience

`RATE_LIMIT_FAIL_OPEN=true` (default) allows requests through when the Redis
rate limiter is unavailable. In production, set `RATE_LIMIT_FAIL_OPEN=false`
to fail closed and return 503 when the rate limiter cannot be reached.

## External LLM Providers

External LLM providers (OpenRouter, NVIDIA, HuggingFace, OpenAI-compatible)
have been removed. Meero uses only local GGUF models via GPT4All for LLM
fallback. No API keys or external network calls are made for inference.

## Audit Logging

Audit events omit command and response text by default. Set
`AUDIT_LOG_COMMAND_TEXT=true` only for local debugging when storing spoken
content is acceptable. Keep it false for normal and production-style use.
