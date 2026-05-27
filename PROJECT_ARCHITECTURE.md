# Project Architecture: Meero Python 2.0

## 1. Frontend

The frontend is a React + Vite browser app. It owns browser microphone input,
speech synthesis, assistant state, and the visual assistant experience.

Key modules:

- `frontend/src/App.jsx` coordinates UI state, browser speech hooks, and backend
  `/command` calls.
- `frontend/src/hooks/useSpeechRecognition.js` handles Web Speech API input.
- `frontend/src/hooks/useSpeechSynthesis.js` handles browser text-to-speech.
- `frontend/src/components/ThreeOrb.jsx`, `Background.jsx`, and
  `HologramOverlay.jsx` render the assistant UI.

## 2. Backend

The backend is a FastAPI app exposed from `backend.app:app`.

Key modules:

- `backend/app.py` exposes `/`, `/health`, `/command`, `/settings`, and
  `/metrics`.
- `core/actions.py` handles deterministic commands such as opening websites,
  controlling tabs, reporting time/date, screenshots, jokes, and system status.
- `core/actions_routing.py` defines command route specs used by the action
  engine and intent evaluation tests.
- `core/mock_engine.py` captures action responses for API responses instead of
  speaking them through a local desktop TTS engine.
- `core/memory_store.py` persists conversation history and summaries in a local
  SQLite database that is created at runtime.
- `ai/neural_net.py` loads canonical model artifacts for trained intent fallback.
- `ai/llm_engine.py` and `ai/external_llm.py` provide optional LLM fallbacks.

## 3. Runtime Data Flow

1. The browser captures speech or user interaction and produces text.
2. The frontend sends text to `POST /command`.
3. The backend runs rule-based actions first.
4. If no action route matches, the backend tries the neural intent model.
5. If the neural model cannot answer confidently, the backend tries local or
   external LLM fallback.
6. The backend returns text, action status, sentiment, and metadata.
7. The frontend displays and speaks the response in the browser.

## 4. Model Artifacts

Runtime model loading uses canonical artifact paths:

- `models/chat_model.h5`
- `models/tokenizer.pkl`
- `models/label_encoder.pkl`
- `models/manifest.json`

Training and packaging are handled by `scripts/train_and_package.py`. Generated
experiment artifacts, diagnostics, and local runtime databases are not part of
the source architecture.
