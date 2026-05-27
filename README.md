# Meero Python 2.0

Meero Python 2.0 is a browser-based AI assistant with a FastAPI backend and a
React frontend. The backend handles command routing, memory, local model
fallbacks, and optional LLM responses. The frontend owns microphone input,
speech synthesis, and the interactive assistant UI.

## Features

- React + Vite voice assistant interface
- FastAPI command API with action routing and confirmation for sensitive actions
- Neural intent model fallback for trained conversational intents
- Optional local GPT4All model fallback
- Conversation memory backed by SQLite runtime state
- Prometheus metrics and optional Redis-backed distributed rate limiting

## Project Structure

- `backend/app.py` - FastAPI application entry point
- `core/actions.py` - Rule-based command engine
- `core/actions_routing.py` - Command route specifications
- `ai/neural_net.py` - Neural intent model runtime
- `ai/llm_engine.py` - Optional local GPT4All fallback
- `core/memory_store.py` - SQLite-backed conversation memory
- `frontend/` - React + Vite web UI
- `scripts/train_and_package.py` - Canonical model training and packaging script

See [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) for a fuller breakdown.

## Requirements

- Python 3.10+
- Node.js 20.19+
- `pnpm` for frontend dependency management
- Redis is optional; without it, distributed rate limiting is skipped and the
  backend still uses its local cooldown guard.

## Setup

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend

```powershell
cd frontend
pnpm install
```

## Run Locally

Run backend and frontend in separate terminals.

### Terminal 1: Backend

```powershell
cd "E:\Meero Python 2.0"
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend

```powershell
cd "E:\Meero Python 2.0\frontend"
pnpm run dev
```

Open `http://localhost:5173` in your browser.

## Docker

Bring up the backend, frontend, and Redis:

```powershell
docker compose up --build
```

## Training

When `intents.json` changes, train and package the canonical model artifacts:

```powershell
python scripts/train_and_package.py --epochs 100 --batch 8 --out-dir models
```

The script writes versioned artifacts, updates `models/manifest.json`, and
refreshes the canonical runtime files:

- `models/chat_model.h5`
- `models/tokenizer.pkl`
- `models/label_encoder.pkl`

See [TRAINING.md](./TRAINING.md) for deterministic runner options.

## Checks

```powershell
python -m pytest -q
cd frontend
pnpm exec vitest run
pnpm lint
```

Run the secret scanner manually:

```powershell
python scripts/secret_scan.py
```
