"""Simple abstraction for optional external LLM providers.
This module is intentionally lightweight and resilient when provider SDKs
or network keys are not available.
"""
import logging
import os
from typing import Optional

import httpx

import config
from core.prompt_templates import build_external_payload, clean_llm_response

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
        if not self.enabled:
            return None

        try:
            api_url = os.environ.get("LLM_API_URL")
            if not api_url:
                logger.warning("LLM_API_URL not set; cannot call external LLM.")
                return None

            payload = build_external_payload(user_input, history, memory_summary=memory_summary)
            headers = {"Authorization": f"Bearer {self.api_key}"}

            resp = httpx.post(api_url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return clean_llm_response(data.get("response") or data.get("text"))
            logger.error("External LLM returned %s: %s", resp.status_code, resp.text)
        except Exception:
            logger.exception("External LLM request failed")

        return None
