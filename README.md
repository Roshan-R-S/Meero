# Meero Python 2.0

Meero is a local-first AI desktop assistant with a FastAPI backend and a
React + Vite frontend. The browser UI handles speech recognition, typed
commands, and speech synthesis. The backend routes commands through deterministic
actions, neural intent fallback, optional local/external LLM fallback, memory,
metrics, and safety checks.

## Local-First Safety

Meero can control local desktop features such as apps, tabs, scrolling, volume,
and screenshots. Treat it as a local assistant unless you add stronger
authentication and deployment controls.

Desktop automation is guarded by environment flags:

- `LOCAL_DESKTOP_MODE=true` enables desktop-control commands.
- `WEB_SAFE_MODE=true` blocks desktop-control commands even when local mode is
  configured.
- `/settings` is local-only and accepts only validated settings keys.
- Optional API-key auth protects `/command` and `/settings` when
  `MEERO_API_KEY` is configured.

## Safety Modes

| Mode | Description |
|---|---|
| `WEB_SAFE_MODE=true` | Blocks desktop/system control |
| `LOCAL_DESKTOP_MODE=true` | Allows local desktop automation for local requests |

For public or production-style deployment:

```env
WEB_SAFE_MODE=true
LOCAL_DESKTOP_MODE=false
```

For local assistant use:

```env
WEB_SAFE_MODE=false
LOCAL_DESKTOP_MODE=true
```

## Features

- React + Vite assistant interface with voice and typed command input
- Browser Speech Recognition and SpeechSynthesis support
- FastAPI command API with confirmation for sensitive actions
- Local desktop action routing guarded by desktop mode
- Neural intent fallback for trained conversational intents
- Optional local GPT4All and external LLM fallback
- SQLite conversation memory
- Prometheus metrics
- Optional Redis-backed distributed rate limiting plus per-client local cooldown

## Requirements

- Python 3.10+
- Node.js 20.19+
- `pnpm`
- Docker Desktop, optional
- Redis, optional outside Docker

## Environment

Copy the examples if you need to customize local defaults:

```powershell
copy .env.example .env
copy frontend\.env.example frontend\.env
```

Backend variables:

```env
PYTHONUNBUFFERED=1
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:5173
RATE_LIMIT_COOLDOWN=1.0
LOCAL_DESKTOP_MODE=false
WEB_SAFE_MODE=true
MEERO_API_KEY=change-this-local-key
LLM_API_PROVIDER=
LLM_API_KEY=
LLM_API_URL=
MEMORY_MAX_INTERACTIONS=20
MEMORY_SUMMARY_MAX_CHARS=1200
```

Frontend variables:

```env
VITE_API_URL=http://localhost:8000
VITE_MEERO_API_KEY=change-this-local-key
```

If `MEERO_API_KEY` is unset, API-key auth is disabled for local convenience. If
it is set, the frontend should send the same value through `VITE_MEERO_API_KEY`.

## Quick Start

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
pnpm install
pnpm run dev
```

Open `http://localhost:5173`.

Speech recognition works best in Chrome or Edge. If browser speech recognition
is unavailable, use the typed command input.

## Docker

Development compose runs the backend, Vite dev server, and Redis with bind
mounts:

```powershell
docker compose up --build
```

Production-style compose builds static frontend assets with nginx and keeps
desktop automation disabled:

```powershell
docker compose -f docker-compose.prod.yml up --build
```

## Project Structure

- `backend/app.py` - FastAPI application entry point
- `backend/command_service.py` - command orchestration and fallback flow
- `core/actions.py` - deterministic action engine
- `core/actions_routing.py` - command route specifications
- `core/memory_store.py` - SQLite-backed memory
- `ai/neural_net.py` - neural intent runtime
- `ai/llm_engine.py` - optional local GPT4All fallback
- `frontend/` - React + Vite UI
- `scripts/train_and_package.py` - canonical model training/packaging
- `scripts/evaluate.py` - model evaluation with accuracy gating

See [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) for the runtime flow.

## Checks

Backend:

```powershell
python -m pytest -q
python scripts/secret_scan.py
```

Frontend:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm lint
pnpm exec vitest run
pnpm run build
pnpm exec playwright test
```

Optional S3 upload dependencies:

```powershell
pip install -r requirements-cloud.txt
```

## CI

This repo runs:

- backend pytest
- secret scan
- frontend Vitest
- frontend lint
- frontend build
- Playwright E2E
- model evaluation on main

## Training And Evaluation

Train canonical model artifacts after changing `intents.json`:

```powershell
python scripts/train_and_package.py --epochs 100 --batch 8 --out-dir models
```

Evaluate with the default minimum accuracy gate of `0.85`:

```powershell
python scripts/evaluate.py --out models/local_eval.json
```

The evaluation report includes accuracy, confidence stats, latency stats, and a
per-intent classification report.

Override the gate when needed:

```powershell
python scripts/evaluate.py --out models/local_eval.json --min-accuracy 0.80
```

See [TRAINING.md](./TRAINING.md) for deterministic runner options.

## Known Limitations

- Desktop automation should not be exposed publicly.
- Speech recognition depends on browser support and microphone permission.
- Local GPT4All fallback requires the configured model file to exist.
- Production Docker is a starting point, not a complete hosted deployment.

## Roadmap

- [x] Voice assistant UI
- [x] FastAPI command backend
- [x] Neural intent fallback
- [x] Local LLM fallback
- [x] SQLite memory
- [x] Redis rate limiting
- [x] Prometheus metrics
- [x] CI pipeline
- [x] API-key authentication
- [x] Production Docker Compose
- [x] Conversation history UI
- [x] Better model evaluation reports
- [ ] Demo GIF
- [ ] Architecture diagram image
- [ ] Public deployment hardening
