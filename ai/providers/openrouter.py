import time
import logging
from typing import Any, Dict, Optional

import httpx

from .base import ProviderBase
import config

logger = logging.getLogger(__name__)


class OpenRouterProvider(ProviderBase):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: int = None):
        api_key = api_key or config.OPENROUTER_API_KEY
        base_url = base_url or config.OPENROUTER_BASE_URL
        super().__init__(api_key=api_key, base_url=base_url)
        self.timeout = timeout or config.PROVIDER_REQUEST_TIMEOUT

    def generate(self, user_input: str, history=None, memory_summary: str = None, model: str = "openrouter-gpt", **kwargs) -> Dict[str, Any]:
        if not self.api_key or not self.base_url:
            logger.debug("OpenRouterProvider not configured")
            return {"text": "", "raw": None}

        payload = {"model": model, "input": user_input}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        start = time.perf_counter()
        try:
            resp = httpx.post(f"{self.base_url}", json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            # OpenRouter responses vary; try common shapes
            text = ""
            if isinstance(data, dict):
                # try data['output'] or data.get('choices') style
                if "output" in data:
                    text = data.get("output")
                else:
                    choices = data.get("choices") or []
                    if choices and isinstance(choices[0], dict):
                        text = choices[0].get("text") or choices[0].get("message", {}).get("content", "")
            elapsed = time.perf_counter() - start
            return {"text": text, "raw": data, "latency": elapsed}
        except Exception:
            logger.exception("OpenRouterProvider request failed")
            return {"text": "", "raw": None}
