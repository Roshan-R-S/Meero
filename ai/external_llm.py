"""Simple abstraction for optional external LLM providers.
This module is intentionally lightweight and resilient when provider SDKs
or network keys are not available.
"""
import logging
from typing import Optional

import config
from ai.providers.factory import get_provider
from core.prompt_templates import clean_llm_response

logger = logging.getLogger(__name__)


class ExternalLLM:
    def __init__(self):
        self.provider_name = getattr(config, "LLM_API_PROVIDER", None)
        self.provider = get_provider(self.provider_name)
        self.enabled = self.provider is not None
        if not self.enabled:
            logger.info("External LLM not configured (provider=%s).", self.provider_name)

    def generate_response(self, user_input: str, history=None, memory_summary=None, model: str = None) -> Optional[str]:
        """Generate a response from the configured external provider.

        Optional `model` is forwarded to the provider.generate() call when supported.
        """
        if not self.enabled:
            return None
        try:
            resp = self.provider.generate(user_input, history=history, memory_summary=memory_summary, model=model)
            if not resp:
                return None
            text = resp.get("text") or ""
            return clean_llm_response(text)
        except Exception:
            logger.exception("External LLM provider call failed")
            return None
