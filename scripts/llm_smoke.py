"""Small smoke script to verify external LLM provider configuration.

Usage: set environment variables (do NOT commit keys) and run:

LLM_API_PROVIDER=nvidia \
NVIDIA_API_KEY=<key> \
NVIDIA_BASE_URL=<base_url> \
LLM_MODEL_NAME=moonshotai/kimi-k2.6 \
python scripts/llm_smoke.py

The script calls `ai.external_llm.ExternalLLM.generate_response` with a short prompt.
"""
import os
import sys
import json
from ai.external_llm import ExternalLLM


def main():
    provider = os.environ.get("LLM_API_PROVIDER")
    model = os.environ.get("LLM_MODEL_NAME")

    print(f"LLM_API_PROVIDER={provider}")
    if model:
        print(f"LLM_MODEL_NAME={model}")

    ext = ExternalLLM()
    print("External LLM enabled:", ext.enabled)
    if not ext.enabled:
        print("Provider not configured. Check env vars (API key, provider name, base URL).")
        sys.exit(1)

    prompt = os.environ.get("LLM_SMOKE_PROMPT", "Say hello in one sentence.")
    print("Sending prompt:", prompt)
    resp = ext.generate_response(prompt, model=model)
    print("Response:\n", resp)


if __name__ == "__main__":
    main()
