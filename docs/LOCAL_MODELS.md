# Local Model Setup

Downloaded models are ignored by Git and must be installed explicitly. Meero
never downloads models during application startup.

Preferred locations:

- GGUF: `models/local-llm/`
- Vosk or faster-whisper: `models/local-stt/`
- Piper: `models/local-tts/`

Use a trusted model URL and its published SHA-256 checksum:

```powershell
.\.venv\Scripts\python.exe scripts\download_models.py `
  --url <model-url> `
  --dest models\local-stt\vosk-en-us `
  --sha256 <published-sha256> `
  --extract-zip
```

Set `VOICE_STT_PROVIDER=faster-whisper` only when that local provider and model
are intentionally installed. External inference providers are not supported.
