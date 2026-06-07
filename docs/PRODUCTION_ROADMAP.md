# Production Roadmap

## Completed Foundations

- Single deterministic-first command orchestrator
- Fail-closed desktop app allowlists and confirmation checks
- Private-by-default audit logging and decision traces
- Local push-to-talk STT/TTS pipeline
- Web-safe and voice-specific container images
- Consolidated backend, frontend, browser, and evaluation CI

## Remaining Hardening

- Add real user authentication before any public deployment.
- Put public deployments behind HTTPS and network controls.
- Add streaming local wake-word support only after a dedicated privacy and
  resource-usage review.
- Establish signed model manifests and release provenance.
