# Meero Python 2.0

Meero Python 2.0 is a voice-enabled AI assistant with a Python FastAPI backend and a React frontend. It supports speech input, text-to-speech, automation, and local AI fallback responses.

## Features

- Voice interaction with speech-to-text and text-to-speech
- React frontend with an animated assistant UI
- Rule-based command handling for apps, websites, and system actions
- Neural network and LLM fallback for general conversation
- Offline speech recognition support with Vosk

## Project Structure

- `server.py` - FastAPI backend entry point
- `actions.py` - Rule-based command engine
- `neural_net.py` - Neural network fallback
- `llm_engine.py` - Local GPT4All fallback
- `main.py` - Legacy console-only entry point
- `frontend/` - React + Vite web UI

See [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) for a full breakdown.

## Requirements

- Python 3.8+
- Node.js 20+
- `pnpm` recommended for the frontend

## Setup

### Backend

From the project root:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
pnpm install
```

## How to Run

Run the backend and frontend in two separate terminals.

### Terminal 1: Backend

```bash
python server.py
```

Or run the FastAPI app directly with uvicorn:

```bash
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend

```bash
cd frontend
pnpm run dev
```

Open `http://localhost:5173` in your browser.

## Docker

Bring up the backend, frontend, and Redis in one shot:

```bash
docker compose up --build
```

If you only want the backend stack (and Redis for the rate limiter), you can run:

```bash
docker compose up --build backend redis
```

## Windows PowerShell Quick Start

```powershell
cd "E:\Meero Python 2.0"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend
pnpm install
```

Then open two terminals:

```powershell
cd "E:\Meero Python 2.0"
.\.venv\Scripts\Activate.ps1
python server.py
```

Or:

```powershell
cd "E:\Meero Python 2.0"
.\.venv\Scripts\Activate.ps1
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

```powershell
cd "E:\Meero Python 2.0\frontend"
pnpm run dev
```

If you are using the local speech backend, make sure your browser allows microphone access.

## Training the Model

If you modify `intents.json`, retrain the AI:

```bash
python model_train.py
```

## Legacy Console Mode

To run without the web UI:

```bash
python main.py
```

## Offline Speech Recognition (Vosk)

Meero supports an offline STT backend using Vosk. By default the project prefers Vosk when available and falls back to Google Online STT.

```powershell
pip install -r requirements.txt
```

```powershell
python scripts/setup_vosk.py
python scripts/setup_vosk.py --verify-only
```

```powershell
# Point to a custom model path for the current session
$env:VOSK_MODEL_PATH = "E:\path\to\models\vosk-model-small-en-us-0.15"
# Or force online Google backend
$env:SPEECH_BACKEND = "google"
```

- Vosk runs fully offline but requires downloading a language model.
- If Vosk fails or is unavailable, Meero will automatically fall back to the Google recognizer.

## Model Packaging and Release Automation

Build versioned intent-model artifacts locally:

```powershell
python scripts/train_and_package.py --epochs 5 --batch 32 --out-dir build/model-artifacts
```

Quantize a Hugging Face model directory or source GGUF with llama.cpp tools:

```powershell
python scripts/package_gguf.py --input path\to\hf-model --out-dir build\model-artifacts\gguf --quantization Q4_K_M
```

Tagged pushes (`v*`) and published GitHub releases build and package artifacts, attach them to the workflow or release, and optionally publish to Hugging Face when `HF_TOKEN` and `HF_REPO` secrets are configured.

## Security and Formatting

Install local hooks:

```powershell
pip install -r requirements-test.txt
pre-commit install
```

Run the secret scanner manually:

```powershell
python scripts/secret_scan.py
```

Rotate GitHub Actions secrets by setting replacement values in `NEW_<SECRET_NAME>` environment variables, for example `NEW_HF_TOKEN`, then running:

```powershell
python scripts/rotate_tokens.py --secret HF_TOKEN --repo owner/repo
```
