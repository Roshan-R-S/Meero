"""Simple abstraction for optional external LLM providers.
This module is intentionally lightweight and resilient when provider SDKs
or network keys are not available.
"""
import os
import logging
from typing import Optional
import httpx
import config
from prompt_templates import build_external_payload

logger = logging.getLogger(__name__)


class ExternalLLM:
    def __init__(self):
        self.provider = getattr(config, "LLM_API_PROVIDER", None)
        self.api_key = os.environ.get("LLM_API_KEY")

        if not self.provider or not self.api_key:
            logger.info("External LLM not configured (provider=%s).", self.provider)
            self.enabled = False
        else:
            self.enabled = True

    def generate_response(
        self,
        user_input: str,
        history=None,
        memory_summary=None,
    ) -> Optional[str]:
        """Generate a response using the configured external LLM provider.

        Currently supports a simple HTTP POST interface. Returns None if
        not configured or if the provider is unsupported.
        """
        if not self.enabled:
            return None

        try:
            # Example for a generic provider endpoint; operator must provide
            # a compatible `LLM_API_URL` environment variable when using this.
            api_url = os.environ.get("LLM_API_URL")
            if not api_url:
                logger.warning("LLM_API_URL not set; cannot call external LLM.")
                return None

            payload = build_external_payload(user_input, history, memory_summary=memory_summary)
            headers = {"Authorization": f"Bearer {self.api_key}"}

            resp = httpx.post(api_url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response") or data.get("text")
            logger.error("External LLM returned %s: %s", resp.status_code, resp.text)
        except Exception:
            logger.exception("External LLM request failed")

        return None
