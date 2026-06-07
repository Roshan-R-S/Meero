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

Development:

```powershell
docker compose up --build
```

Production-style:

```powershell
docker compose -f docker-compose.prod.yml up --build
```

Before publishing, verify the resolved configuration:

```powershell
docker compose config
docker compose -f docker-compose.prod.yml config
```

For local desktop mode, set `APP_LAUNCH_ALLOWLIST` and `APP_CLOSE_ALLOWLIST` to
the approved application names. Both operations fail closed when their
allowlists are empty. Use `APP_FORCE_CLOSE_ALLOWLIST` only for approved close
targets that may be terminated with force.
