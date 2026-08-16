# Roadmap And Release Notes

## Completed Foundations

- Single deterministic-first command orchestrator
- Fail-closed desktop app allowlists and confirmation checks
- Private-by-default audit logging and decision traces
- Local push-to-talk STT/TTS pipeline
- Web-safe and voice-specific container images
- Capability-specific dependency profiles and explicit data/model mounts
- Cached local STT models and privacy-safe voice-stage decision traces
- Bounded Piper, SAPI, and desktop subprocess execution
- Consolidated backend, frontend, browser, deployment, and evaluation CI

## Remaining Production Hardening

- Add real user authentication before any public deployment.
- Put public deployments behind HTTPS and network controls.
- Add streaming local wake-word support only after a privacy and resource
  review.
- Introduce process isolation before enforcing hard cancellation deadlines for
  Vosk, faster-whisper, or GPT4All.
- Replace base64 voice response audio with streaming or a separate synthesis
  request only when response sizes justify the added complexity.
- Consider Compose profiles only if the current explicit development,
  production, and voice-overlay commands become difficult to operate.
- Consider a dedicated voice orchestrator only if voice-specific policy grows
  beyond the current thin local pipeline around the command orchestrator.
- Establish signed model manifests and release provenance.

## v0.1.0-local

Status: release candidate. Tag only after every validation gate is green.

### Hardening

- Restored the internal command outcome schema and backend test baseline.
- Removed legacy global command timestamp state and wildcard CORS fallback.
- Added fail-closed launch and close allowlists with constrained force-close.
- Made audit logs omit command and response text by default.
- Enabled typed command input and retained it when speech is unavailable.

### Voice And Quality

- Added local push-to-talk Vosk/faster-whisper STT and Piper/SAPI TTS.
- Added wake-word, inline-command, push-to-talk, permission-error, and TTS
  restart tests.
- Added ASR-style voice routing and model evaluation cases.
- Added natural `screen shot`, `sound`, and browser-tab routing variants.

### Release Gate

- Backend imports, tests, and secret scan pass.
- Frontend unit tests, lint, build, and Playwright pass.
- Standard, unseen, and voice evaluations pass.
- Development and production Compose configurations validate.
