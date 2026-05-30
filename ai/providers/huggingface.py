import time
import logging
from typing import Any, Dict, Optional

import httpx

from .base import ProviderBase
import config

logger = logging.getLogger(__name__)


class HuggingFaceProvider(ProviderBase):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: int = None):
        api_key = api_key or config.HUGGINGFACE_API_KEY
        base_url = base_url or config.HUGGINGFACE_BASE_URL
        super().__init__(api_key=api_key, base_url=base_url)
        self.timeout = timeout or config.PROVIDER_REQUEST_TIMEOUT

    def generate(self, user_input: str, history=None, memory_summary: str = None, model: str = "gpt2", **kwargs) -> Dict[str, Any]:
        if not self.api_key or not self.base_url:
            logger.debug("HuggingFaceProvider not configured")
            return {"text": "", "raw": None}

        url = f"{self.base_url.rstrip('/')}/{model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": user_input}

        start = time.perf_counter()
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            text = ""
            # HF may return a list of dicts with 'generated_text'
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    text = first.get("generated_text") or first.get("text", "")
            elif isinstance(data, dict):
                text = data.get("generated_text") or data.get("text", "")
            elapsed = time.perf_counter() - start
            return {"text": text, "raw": data, "latency": elapsed}
        except Exception:
            logger.exception("HuggingFaceProvider request failed")
            return {"text": "", "raw": None}
