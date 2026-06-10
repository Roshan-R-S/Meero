# Deployment Guide

Meero is safest as a local-first or private-network assistant. Pick one of these
deployment modes and keep the environment flags aligned with it.

## Local Desktop Assistant

Use this only on your own machine or trusted LAN.

```env
WEB_SAFE_MODE=false
LOCAL_DESKTOP_MODE=true
REQUIRE_API_KEY=false
PROTECT_METRICS=false
APP_LAUNCH_ALLOWLIST=notepad,calculator,paint,vscode
APP_CLOSE_ALLOWLIST=notepad,calculator,paint,vscode
APP_FORCE_CLOSE_ALLOWLIST=notepad
AUDIT_LOG_COMMAND_TEXT=false
MEERO_API_KEY=
```

Desktop automation is available only for local requests. Add `MEERO_API_KEY` and
matching `VITE_MEERO_API_KEY` if another browser or device can reach the backend.
Launch and close operations remain blocked until their explicit allowlists are
configured.

## Private Or VPN Hosted Assistant

Use this when Meero is reachable through a private network such as Tailscale,
WireGuard, or a reverse proxy with basic auth.

```env
WEB_SAFE_MODE=true
LOCAL_DESKTOP_MODE=false
REQUIRE_API_KEY=true
PROTECT_METRICS=true
MEERO_API_KEY=<strong-random-value>
AUDIT_LOG_COMMAND_TEXT=false
```

For browser builds, `VITE_MEERO_API_KEY` can send the matching key, but it is not
a public-web secret. Anyone with access to the browser bundle can inspect it.

## Public Safe Demo

Use this for portfolio demos where visitors may open the frontend.

```env
WEB_SAFE_MODE=true
LOCAL_DESKTOP_MODE=false
REQUIRE_API_KEY=true
PROTECT_METRICS=true
MEERO_API_KEY=<strong-random-value>
AUDIT_LOG_COMMAND_TEXT=false
```

Do not expose desktop automation. Put the app behind login, reverse-proxy auth,
or private access if commands should call protected backend endpoints. A public
frontend without real auth should be treated as a visual demo only.

## Docker Commands

Meero ships three backend image modes:

| Dockerfile | Runtime |
| --- | --- |
| `Dockerfile` | Full local desktop assistant: base, AI, safe actions, and GUI automation |
| `Dockerfile.websafe` | Web-safe API: base, AI, and safe non-GUI actions |
| `Dockerfile.voice` | Web-safe API plus local Vosk/faster-whisper/Piper providers |

Models are never baked into these images.

Development:

```powershell
docker compose up --build
```

Production-style:

```powershell
docker compose -f docker-compose.prod.yml up --build
```

The production Compose file uses `Dockerfile.websafe`, which keeps desktop
automation disabled. It mounts `./data` as writable local state and `./models`
read-only. `Dockerfile.voice` adds local voice dependencies but does not bundle
or download models.

Run the production topology with the local voice image and read-only model
mounts:

```powershell
docker compose -f docker-compose.prod.yml -f docker-compose.voice.yml up --build
```

Before publishing, verify the resolved configuration:

```powershell
docker compose config
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml -f docker-compose.voice.yml config
```

Piper, Windows SAPI, and synchronous desktop subprocesses use bounded
timeouts configured by `VOICE_TTS_TIMEOUT_SECONDS` and
`DESKTOP_SUBPROCESS_TIMEOUT_SECONDS`. Vosk, faster-whisper, and GPT4All remain
synchronous in-process providers; hard cancellation for those providers is
deferred until process isolation is introduced.

For local desktop mode, set `APP_LAUNCH_ALLOWLIST` and `APP_CLOSE_ALLOWLIST` to
the approved application names. Both operations fail closed when their
allowlists are empty. Use `APP_FORCE_CLOSE_ALLOWLIST` only for approved close
targets that may be terminated with force.

## Production Safety Checklist

- Keep `WEB_SAFE_MODE=true` and `LOCAL_DESKTOP_MODE=false` on reachable hosts.
- Set `REQUIRE_API_KEY=true`, `PROTECT_METRICS=true`, and a strong
  `MEERO_API_KEY`.
- Add real user authentication, HTTPS, and network controls before public
  exposure.
- Keep `VITE_MEERO_API_KEY` limited to local or private deployments because it
  is visible in the browser bundle.
- Set `RATE_LIMIT_FAIL_OPEN=false` when Redis failure should block requests.
- Keep `DEBUG_ERRORS=false` and `AUDIT_LOG_COMMAND_TEXT=false`.
- Run `python scripts/secret_scan.py` before publishing changes.

Desktop actions require a local request, `LOCAL_DESKTOP_MODE=true`, and
`WEB_SAFE_MODE=false`. Settings and voice endpoints are local-only. Voice audio
is bounded, validated, processed in request-scoped temporary files, and not
retained. External inference providers are not supported.

## Local Model Setup

Downloaded models are ignored by Git and must be installed explicitly. Meero
never downloads models during application startup.

Preferred locations:

- GGUF: `models/local-llm/`
- Vosk or faster-whisper: `models/local-stt/`
- Piper: `models/local-tts/`

Use a trusted model URL and its published SHA-256 checksum:

```powershell
.\.venv\Scripts\python.exe scripts\download_models.py `
  --url <model-url> `
  --dest models\local-stt\vosk-en-us `
  --sha256 <published-sha256> `
  --extract-zip
```

Set `VOICE_STT_PROVIDER=faster-whisper` only when that local provider and model
are intentionally installed.
