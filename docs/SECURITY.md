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

## Local Desktop Controls

Desktop actions such as app launch/close, screenshots, volume control, tab
control, and scrolling are blocked unless:

- the request is local, and
- `LOCAL_DESKTOP_MODE=true`, and
- `WEB_SAFE_MODE=false`.

Use `WEB_SAFE_MODE=true` for demos or environments where host control should be
disabled.

## Production Deployment

Production-style Docker configuration keeps desktop automation disabled. Do not
enable `LOCAL_DESKTOP_MODE=true` on a publicly reachable host. Production-style
deployments should use:

```env
WEB_SAFE_MODE=true
LOCAL_DESKTOP_MODE=false
REQUIRE_API_KEY=true
MEERO_API_KEY=<strong-random-value>
```

## Settings

`/settings` is local-only and accepts only the supported settings schema. Unknown
keys are rejected.

## Secrets

Run the repository secret scanner before publishing changes:

```powershell
python scripts/secret_scan.py
```
