# Local Voice Pipeline

Meero's preferred voice path is local push-to-talk:

1. The browser records a 16 kHz mono 16-bit PCM WAV.
2. `POST /voice-command` validates bounded audio and transcribes it locally.
3. The transcript enters the same orchestrator used by `POST /command`.
4. Piper, or Windows SAPI as fallback, may synthesize the response locally.
5. Request audio and temporary files are discarded.

Voice endpoints are local-only and API-key protected. Audit logs and decision
traces exclude audio, transcripts, commands, and response text by default.
Continuous wake-word mode is available only through the explicitly enabled
browser speech fallback.
