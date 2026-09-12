# Meero Python 2.0

[![CI](https://github.com/Roshan-R-S/Meero/actions/workflows/ci.yml/badge.svg)](https://github.com/Roshan-R-S/Meero/actions/workflows/ci.yml)
[![GitLab CI](https://gitlab.com/nil-group2811337/Meero/badges/main/pipeline.svg)](https://gitlab.com/nil-group2811337/Meero/-/pipelines)
[![Playwright E2E](https://github.com/Roshan-R-S/Meero/actions/workflows/playwright.yml/badge.svg)](https://github.com/Roshan-R-S/Meero/actions/workflows/playwright.yml)
[![Model Evaluation](https://github.com/Roshan-R-S/Meero/actions/workflows/eval-on-main.yml/badge.svg)](https://github.com/Roshan-R-S/Meero/actions/workflows/eval-on-main.yml)

**Meero** is a high-performance, local-first, privacy-focused voice desktop AI assistant. Built with a **FastAPI** backend and a cyberpunk **React + Vite** frontend, Meero delivers near-instant voice interactions with custom cloned voices, real-time live desktop controls, deterministic-first command routing (<2ms), neural intent classification, and offline GGUF LLM reasoning—without relying on any external cloud inference providers.

---

## 🌟 Key Features & Capabilities

### 🎙️ 1. Ultra-Low-Latency Local Voice Pipeline
* **Coqui XTTS v2 Voice Cloning**: Expressive cloned female voice generated directly from local reference samples (`reference.wav`, `reference1.wav`).
* **GPU Hardware Acceleration & Smart CPU Fallback**: Native **NVIDIA CUDA 12.1** support for RTX GPUs with intelligent auto-detection (`XTTS_USE_GPU=auto`). Automatically falls back to **Piper TTS** or **Windows SAPI** on CPU environments to prevent synthesis blocking.
* **Speaker Latents Caching & Background Pre-Warming**: Pre-computes and caches speaker conditioning latents during server startup in a non-blocking worker thread, eliminating first-utterance lag.
* **Streaming Audio Pipeline**: End-to-end NDJSON streaming (`/voice-command/stream`) with sentence-boundary chunking and parallel TTS synthesis, delivering fast time-to-first-audio (TTFA).
* **Client-Side Silero VAD (Voice Activity Detection)**: WebAssembly-powered Silero VAD model in the browser for voice start/end detection with zero server roundtrips and graceful RMS fallback.
* **Multi-Tiered TTS Failover**: Seamless automatic cascade from **XTTS v2** $\rightarrow$ **Piper TTS** $\rightarrow$ **Windows SAPI** $\rightarrow$ **Browser Web Speech API**.

### ⚡ 2. Deterministic-First Command Engine (<2ms)
* **Instant Action Routing**: Common queries bypass heavy neural models entirely, executing in under 2ms via optimized regex and token pattern matchers.
* **Conversational Courtesies**: Deterministic handlers for greetings (*"hello"*, *"good morning"*), wellbeing (*"how are you"*, *"how's it going"*), gratitude (*"thank you"*, *"thanks"*), compliments (*"you're awesome"*, *"great job"*), identity (*"who are you"*), and farewells (*"see you later"*, *"good night"*).
* **Voice Reminders & Scheduling**: Persistent SQLite-backed reminder scheduler with targeted cancellation by keyword (*"cancel my water reminder"*).
* **Live Weather Integration**: Instant weather reports (*"what is the weather in Chennai?"*, temperature, humidity, wind speed, condition summaries) via OpenWeatherMap.
* **Desktop Automation**: Launch and close desktop applications, manage window states, adjust master volume, mute/unmute, toggle media playback, capture screenshots, and perform web searches.

### 🧠 3. Hybrid 3-Tier AI Architecture
```
User Spoken / Text Input
          │
          ▼
┌─────────────────────────────────┐
│ Tier 1: Deterministic Router    │ ── Match ──► [Instant Response <2ms]
│ (Regex & Token Pattern Specs)   │
└─────────────────────────────────┘
          │ (No Match)
          ▼
┌─────────────────────────────────┐
│ Tier 2: Local Neural Net        │ ── High Conf ──► [Structured Action]
│ (TensorFlow Intent Classifier)  │
└─────────────────────────────────┘
          │ (Low Conf / Fallback)
          ▼
┌─────────────────────────────────┐
│ Tier 3: Local Offline LLM       │ ── Stream ──► [Synthesized Answer]
│ (GPT4All / GGUF with Token Cap) │
└─────────────────────────────────┘
```
* **Tier 1 — Deterministic Routing**: Pre-compiled regex patterns for zero-latency execution.
* **Tier 2 — Neural Classifier**: Fast local TensorFlow model trained on canonical user intents (`data/intents.json`).
* **Tier 3 — Local LLM Fallback**: Offline GGUF models (e.g. Llama-3.2-1B-Instruct) running via GPT4All with Windows memory-lock protections and voice-mode token caps (96 tokens for voice mode to ensure rapid conversational turnaround).
* **SQLite Conversation Memory**: Thread-safe persistent conversational context with sliding window summarization.

### 💻 4. Modern Cyberpunk UI & Dual-Mode Voice UX
* **Neon Cyberpunk Aesthetic**: High-contrast dark theme, animated neon visualizer rings, dynamic status chips, and custom cyan scrollbars.
* **Dual-Mode Voice Recognition**:
  * **Continuous Wake-Word Mode**: Hands-free listening for wake words (*"hey meero"*, *"hey miro"*, *"hey nero"*, *"hey mirror"*) with inline command execution.
  * **Push-to-Talk Mode**: Dedicated interactive mic button with Silero VAD automated endpointing.
* **Real-Time Latency Telemetry**: Live instrumentation showing time-to-first-audio, synthesis duration, STT processing time, and pipeline breakdown.

---

## 🔒 Security & Safety Controls

Meero is built on a **private-by-default, fail-closed** security model:

| Setting | Default | Description | Recommended Usage |
|---|---|---|---|
| `WEB_SAFE_MODE` | `true` | Completely blocks OS automation, system commands, and desktop execution | Cloud, container, or web deployments |
| `LOCAL_DESKTOP_MODE` | `false` | Enables local desktop automation (apps, volume, window controls) | Trusted personal desktop assistant |
| `APP_LAUNCH_ALLOWLIST` | *empty* | Comma-separated allowlist of permitted launch binaries | Fail-closed app launch security |
| `APP_CLOSE_ALLOWLIST` | *empty* | Comma-separated allowlist of permitted terminable binaries | Fail-closed app termination security |
| `APP_FORCE_CLOSE_ALLOWLIST` | *empty* | Binaries allowed to be terminated via force kill | Restrictive force-close permissions |
| `MEERO_API_KEY` | *unset* | Bearer token / X-API-Key requirement for all `/command` endpoints | Multi-user or networked setups |
| `REQUIRE_API_KEY` | `false` | Enforce API key requirement; fails closed if set true without key | Production Compose / networked setups |
| `RATE_LIMIT_FAIL_OPEN` | `true` | Allows requests if Redis is unreachable; set `false` in prod to fail closed | Standalone desktop (`true`), Prod (`false`) |
| `MEERO_USER_NAME` | `User` | Assistant owner's name, customized via environment variable | Personalization without hardcoding |
| `AUDIT_LOG_COMMAND_TEXT` | `false` | Keeps spoken voice and response text out of audit logs | Standard privacy compliance |

---

## 🚀 Quick Start

### 1. Prerequisites
* **Python 3.10+** (64-bit recommended)
* **Node.js 20+** and **pnpm**
* *(Optional)* NVIDIA GPU with **CUDA 12.1+** for GPU-accelerated XTTS v2 voice cloning

### 2. Environment Setup

Copy example configurations:
```powershell
copy .env.example .env
copy frontend\.env.example frontend\.env
```

Configure your `.env` for local desktop mode:
```env
# Desktop automation & safety
LOCAL_DESKTOP_MODE=true
WEB_SAFE_MODE=false
APP_LAUNCH_ALLOWLIST=notepad,calculator,paint,vscode,chrome,edge
APP_CLOSE_ALLOWLIST=notepad,calculator,paint,vscode,chrome,edge

# Voice TTS Engine
VOICE_TTS_PROVIDER=xtts
XTTS_USE_GPU=auto
VOICE_CLONE_REFERENCE_AUDIOS=data/voices/reference.wav,data/voices/reference1.wav

# Voice Latency & Streaming Settings
VOICE_LOW_LATENCY_MODE=true
VOICE_LLM_MAX_TOKENS=96
VOICE_STREAM_CHUNK_MIN_CHARS=60
VOICE_STREAM_CHUNK_MAX_CHARS=180

# Live Weather (Optional)
OPENWEATHERMAP_API_KEY=your_api_key_here
OPENWEATHERMAP_DEFAULT_CITY=Chennai
OPENWEATHERMAP_UNITS=metric
```

### 3. Backend Setup

```powershell
# Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install base dependencies
pip install -r requirements.txt

# (Optional: Install PyTorch with CUDA 12.1 for NVIDIA RTX GPU acceleration)
pip install --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Start the FastAPI server
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### 4. Frontend Setup

```powershell
cd frontend
pnpm install
pnpm run dev
```

Open `http://localhost:5173` in Google Chrome or Microsoft Edge for native Web Speech API microphone support.

---

## 📁 Repository Structure

```
Meero Python 2.0/
├── ai/
│   ├── intent_evaluator.py     # Intent evaluation & accuracy benchmarking
│   ├── llm_engine.py           # Thread-safe local GPT4All/GGUF runner with token budgets
│   └── neural_net.py           # Local TensorFlow neural intent classifier
├── backend/
│   ├── app.py                  # FastAPI application, middleware, endpoints & lifecycle
│   ├── command_service.py      # Multi-tier intent orchestrator & fallback pipeline
│   ├── orchestrator/           # Fallback policy & AI orchestration layer
│   └── voice/
│       ├── tts_service.py      # XTTS v2, Piper & SAPI TTS engine with GPU auto-detection
│       ├── voice_pipeline.py   # Streaming voice pipeline & latency telemetry
│       └── schemas.py          # Voice payload & telemetry data contracts
├── core/
│   ├── actions.py              # Deterministic actions (weather, system, apps, volume, media)
│   ├── actions_routing.py      # Deterministic regex & token route specifications
│   ├── memory_store.py         # SQLite conversation history & summarizer
│   └── response_collector.py   # Multi-part action response aggregator
├── data/
│   ├── intents.json            # Canonical training dataset for neural classifier
│   ├── intent_eval_cases.json  # Comprehensive intent regression test suite
│   ├── voice_eval_cases.json   # Voice command evaluation dataset
│   └── voices/                 # Reference audio samples for XTTS v2 voice cloning
├── frontend/                   # Cyberpunk React 18 + Vite client
│   ├── src/
│   │   ├── App.jsx             # Main application shell & audio visualizer
│   │   ├── api.js              # Streaming NDJSON and REST client
│   │   ├── hooks/
│   │   │   ├── useAudioRecorder.js    # Audio chunking & recording
│   │   │   ├── useSpeechRecognition.js# Wake-word & speech recognition
│   │   │   ├── useSpeechSynthesis.js  # Client TTS synthesis & audio queue
│   │   │   ├── useVAD.js              # Client Silero VAD with RMS fallback
│   │   │   └── useVoicePipeline.js    # High-level voice coordination hook
│   │   └── index.css           # Cyber styling, scrollbars & visualizer tokens
├── models/                     # Trained neural network weights, vocabularies & models
├── scripts/
│   ├── download_models.py      # Automated model downloader (XTTS, Vosk, Piper, GGUF)
│   ├── evaluate.py             # Model accuracy & intent evaluation script
│   ├── secret_scan.py          # Security verification script
│   └── train_and_package.py    # Training pipeline for neural intent model
├── tests/                      # Pytest suite (198 unit & integration tests)
├── AGENTS.md                   # Agent guidelines & repository invariants
└── verify_changes.py           # Quick sanity verification runner
```

---

## 🧪 Testing & Quality Assurance

Run the comprehensive test suite before submitting changes:

### Backend Validation
```powershell
# Quick sanity check
.\.venv\Scripts\python.exe verify_changes.py

# Full pytest suite (198 tests)
.\.venv\Scripts\python.exe -m pytest -q

# Security and secret scan
.\.venv\Scripts\python.exe scripts\secret_scan.py
```

### Frontend Validation
```powershell
cd frontend

# Run ESLint
pnpm lint

# Run Vitest suite (44 unit/hook tests)
pnpm exec vitest run

# Production build test
pnpm run build

# Playwright E2E tests
pnpm exec playwright test
```

---

## 🚢 Architecture & Invariants

* **Local-First & Private**: No external inference APIs. All models run entirely on-device.
* **Deterministic-First**: Queries matching deterministic patterns never touch neural or LLM fallbacks.
* **Fail-Closed Security**: App launches and terminations enforce strict allowlists in desktop mode.
* **Thread-Safe Concurrency**: Local LLM and TTS engines manage internal synchronization locks to prevent GPU/CPU memory conflicts.
