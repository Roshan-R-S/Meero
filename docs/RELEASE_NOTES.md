# Release Notes

## v0.1.0-local

Status: release candidate. Tag only after every validation gate is green.

### Hardening

- Restored the internal command outcome schema and backend test baseline.
- Removed legacy global command timestamp state.
- Removed wildcard CORS fallback.
- Added fail-closed launch and close allowlists with constrained force-close.
- Made audit logs omit command and response text by default.
- Enabled typed command input by default and retained it when speech is
  unavailable.

### Voice And Quality

- Added wake-word, inline-command, push-to-talk, permission-error, and TTS
  restart hook tests.
- Added ASR-style voice routing and model evaluation cases.
- Added natural `screen shot`, `sound`, and browser-tab routing variants.

### CI And Documentation

- Split lightweight and full AI-backed test dependencies.
- Added a full main-branch backend job and voice evaluation gate.
- Added agent guidance, repository map, and local Vosk/Piper/SAPI roadmap.

### Release Gate

- Backend imports, tests, and secret scan pass.
- Frontend unit tests, lint, build, and Playwright pass.
- Standard, unseen, and voice evaluations pass.
- Development and production Compose configurations validate.
