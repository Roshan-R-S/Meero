# Repository Map

## Backend API And Security

- `backend/app.py`: FastAPI endpoints, CORS, auth, local-only checks, rate
  limiting, settings, model status, and metrics.
- `backend/schemas.py`: internal command-service outcome contract.
- `backend/telemetry.py`: private-by-default JSONL audit events.
- Relevant tests: `tests/test_server.py`, `tests/test_api_security.py`,
  `tests/test_cors.py`, `tests/test_telemetry.py`.

## Commands And Desktop Safety

- `backend/orchestrator/`: execution context, safety, deterministic actions,
  neural fallback, local LLM fallback, and privacy-safe decision traces.
- `backend/command_service.py`: compatibility facade for the orchestrator.
- `core/actions.py`: deterministic action implementations and matchers.
- `core/actions_routing.py`: ordered route definitions.
- `app_launcher.py`: launch, close, and force-close allowlists.
- Relevant tests: `tests/test_actions.py`, `tests/test_app_launcher.py`,
  `tests/test_command_service.py`.

## Frontend Voice UX

- `frontend/src/App.jsx`: assistant state, confirmations, and command flow.
- `frontend/src/hooks/useSpeechRecognition.js`: wake word, push-to-talk, and
  continued conversation.
- `frontend/src/hooks/useSpeechSynthesis.js`: browser TTS and restart callback.
- `frontend/src/hooks/useHealthSettings.js`: persisted UI settings.
- Relevant tests: hook tests, `frontend/src/App.test.jsx`, and
  `frontend/tests/e2e/app.spec.js`.

## Local Voice

- `backend/voice/`: bounded WAV validation, Vosk/faster-whisper STT,
  Piper/SAPI TTS, and the voice-command pipeline.
- `frontend/src/hooks/useAudioRecorder.js`: local 16 kHz mono WAV capture.
- `frontend/src/hooks/useVoicePipeline.js`: push-to-talk request and playback.
- `scripts/download_models.py`: explicit checksum-verified model installation.

## AI And Evaluation

- `ai/neural_net.py`: neural intent runtime.
- `ai/llm_engine.py`: local GPT4All/GGUF fallback.
- `scripts/train_and_package.py`: canonical training and packaging.
- `scripts/evaluate.py`: model accuracy, confidence, and latency reports.
- `scripts/evaluate_routes.py`: deterministic unseen and voice routing gates.
- `data/intent_eval_cases.json`: unseen deterministic routing and fallback
  boundary cases.
- `data/voice_eval_cases.json`: ASR-style voice evaluation cases.

## CI And Deployment

- `.github/workflows/ci.yml`: lightweight PR validation and full main-branch
  backend tests.
- `.github/workflows/eval-on-main.yml`: training and standard, unseen, and voice
  evaluation gates.
- `requirements-test.txt`: lightweight test dependencies.
- `requirements-test-full.txt`: lightweight plus AI dependencies.
- Dockerfiles and Compose files: local and production-style runtime variants.

## Generated Or Runtime Files

Do not commit caches, virtual environments, frontend build output, runtime
databases, `data/settings.json`, `data/audit.jsonl`, voice cache, downloaded
local models, generated model reports, or local GGUF files.
