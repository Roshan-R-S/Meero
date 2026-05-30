import os
import time
import logging
from typing import Any, Dict, Optional

import httpx

from .base import ProviderBase
import config

logger = logging.getLogger(__name__)


class OpenAICompatProvider(ProviderBase):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: int = None):
        api_key = api_key or config.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        base_url = base_url or config.OPENAI_BASE_URL or os.environ.get("OPENAI_BASE_URL")
        super().__init__(api_key=api_key, base_url=base_url)
        self.timeout = timeout or config.PROVIDER_REQUEST_TIMEOUT

    def generate(self, user_input: str, history=None, memory_summary: str = None, model: str = "gpt-3.5-turbo", **kwargs) -> Dict[str, Any]:
        if not self.api_key or not self.base_url:
            logger.debug("OpenAICompatProvider not configured")
            return {"text": "", "raw": None}

        # Build messages array: system prompt could be added elsewhere; keep simple
        messages = []
        if history:
            for h in history:
                # history expected as list of (user, assistant) tuples or messages
                if isinstance(h, dict) and "role" in h:
                    messages.append(h)
                elif isinstance(h, (list, tuple)) and len(h) >= 2:
                    messages.append({"role": "user", "content": h[0]})
                    messages.append({"role": "assistant", "content": h[1]})

        messages.append({"role": "user", "content": user_input})

        body = {"model": model, "messages": messages}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        start = time.perf_counter()
        try:
            resp = httpx.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            # Normalize response: support choices[0].message.content or text
            text = ""
            if isinstance(data, dict):
                choices = data.get("choices") or []
                if choices:
                    msg = choices[0].get("message") if isinstance(choices[0], dict) else None
                    if msg and isinstance(msg, dict):
                        text = msg.get("content", "")
                    else:
                        text = choices[0].get("text", "")
            elapsed = time.perf_counter() - start
            return {"text": text, "raw": data, "latency": elapsed}
        except Exception:
            logger.exception("OpenAICompatProvider request failed")
            return {"text": "", "raw": None}
