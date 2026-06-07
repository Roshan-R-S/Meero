# Agent Guide

Meero is a local-first voice desktop assistant. Preserve its deterministic-first
command pipeline, local safety controls, and private-by-default behavior.

## Working Rules

- Do not add external inference providers.
- Do not weaken local-request, desktop-mode, API-key, allowlist, or confirmation
  checks.
- Treat app launch and close allowlists as fail-closed in local desktop mode.
- Keep spoken command and response text out of audit logs by default.
- Preserve raw user text for memory and local LLM fallback; normalize only for
  deterministic routing.
- Do not commit runtime databases, settings, audit logs, generated model
  reports, caches, or frontend build output.

## Task Entry Points

- Backend APIs and security: `backend/app.py`
- Command fallback pipeline: `backend/command_service.py`
- Deterministic actions and routing: `core/actions.py`, `core/actions_routing.py`
- App launch and close safety: `app_launcher.py`
- Browser voice UX: `frontend/src/hooks/useSpeechRecognition.js`,
  `frontend/src/hooks/useSpeechSynthesis.js`
- Model training and evaluation: `scripts/train_and_package.py`,
  `scripts/evaluate.py`
- Deployment and CI: Dockerfiles, Compose files, `.github/workflows/`

See `docs/REPO_MAP.md` for a fuller map.

## Validation

```powershell
.\.venv\Scripts\python.exe verify_changes.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\secret_scan.py
cd frontend
pnpm exec vitest run
pnpm lint
pnpm run build
pnpm exec playwright test
```

Use `requirements-test.txt` for lightweight PR checks and
`requirements-test-full.txt` for AI-backed validation.
