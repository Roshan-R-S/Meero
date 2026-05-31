# Provider Adapters

This folder contains adapters that normalize external LLM provider payloads and responses for Meero.

Overview
- `base.py` — provider interface (`ProviderBase`) that adapters implement.
- `openai_compat.py` — adapter for OpenAI-compatible HTTP APIs (POST /chat/completions).
- `openrouter.py` — adapter for OpenRouter-style endpoints.
- `huggingface.py` — adapter for Hugging Face Inference API.
- `factory.py` — simple factory to obtain a provider instance based on `config.LLM_API_PROVIDER`.

Configuration
Set provider-specific environment variables (recommended via `.env` or your deployment system):

- `LLM_API_PROVIDER` — provider key used by the factory (e.g. `openai`, `openrouter`, `huggingface`, `nvidia`).
- `LLM_MODEL_NAME` — optional model id to send to the configured provider (for example, `openrouter/owl-alpha`).
- `OPENAI_API_KEY`, `OPENAI_BASE_URL` — for OpenAI-compatible providers.
- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` — for OpenRouter provider. The default base URL is `https://openrouter.ai/api/v1`.
- `HUGGINGFACE_API_KEY`, `HUGGINGFACE_BASE_URL` — for Hugging Face Inference API.
- `NVIDIA_API_KEY`, `NVIDIA_BASE_URL` — if using NVIDIA Moonshot-style endpoints.
- `PROVIDER_REQUEST_TIMEOUT` — per-request timeout in seconds (default set in `config.py`).

Security / Local-Only mode
- By default external providers are disabled in Meero. To enable remote providers set `ENABLE_EXTERNAL_PROVIDER=true` and provide the appropriate API keys via environment variables or your secret manager. This prevents accidental leakage of keys or unexpected external network calls when running locally.

Usage
The rest of the app interacts with `ai/external_llm.ExternalLLM`, which obtains a provider via the factory and calls `provider.generate(...)`. The provider returns a normalized dict with at least a `text` key and optional `raw` and `latency` fields.

Adding a new provider
1. Create a new module `ai/providers/your_provider.py` implementing `ProviderBase` and a `generate` method that returns a dict like `{"text": "...", "raw": <provider response>}`.
2. Update `ai/providers/factory.py` to map a provider name to your new class.
3. Add unit tests under `tests/` that mock `httpx.post` and validate normalization.
4. Add any required config vars to `config.py` and document them here.

Testing
Unit tests for adapters live in `tests/test_providers_*.py` and are executed by CI. Adapter tests should mock HTTP calls and not require real API keys.

Security
- Never commit API keys. Use environment variables and secrets managers.
- Rotate any leaked keys immediately and update your deployment secrets.
