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
enable `LOCAL_DESKTOP_MODE=true` on a publicly reachable host.

## Settings

`/settings` is local-only and accepts only the supported settings schema. Unknown
keys are rejected.

## Secrets

Run the repository secret scanner before publishing changes:

```powershell
python scripts/secret_scan.py
```
