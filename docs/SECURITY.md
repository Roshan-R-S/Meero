# Security Notes

Meero is designed as a local-first assistant. Do not expose the backend to the
public internet without adding stronger authentication and network controls.

## Local Desktop Controls

Desktop actions such as app launch/close, screenshots, volume control, tab
control, and scrolling are blocked unless:

- the request is local, and
- `LOCAL_DESKTOP_MODE=true`, and
- `WEB_SAFE_MODE=false`.

Use `WEB_SAFE_MODE=true` for demos or environments where host control should be
disabled.

## Settings

`/settings` is local-only and accepts only the supported settings schema. Unknown
keys are rejected.

## Secrets

Run the repository secret scanner before publishing changes:

```powershell
python scripts/secret_scan.py
```
