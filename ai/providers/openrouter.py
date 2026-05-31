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

    @staticmethod
    def _chat_url(base_url: str) -> str:
        base = base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    @staticmethod
    def _build_messages(user_input: str, history=None, memory_summary: str = None) -> list[dict[str, str]]:
        messages = []
        if memory_summary:
            messages.append({"role": "system", "content": f"Conversation summary:\n{memory_summary}"})
        if history:
            for item in history:
                if isinstance(item, dict) and "role" in item:
                    messages.append(item)
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    messages.append({"role": "user", "content": str(item[0])})
                    messages.append({"role": "assistant", "content": str(item[1])})
        messages.append({"role": "user", "content": user_input})
        return messages

    def generate(self, user_input: str, history=None, memory_summary: str = None, model: str = None, **kwargs) -> Dict[str, Any]:
        if not self.api_key or not self.base_url:
            logger.debug("OpenRouterProvider not configured")
            return {"text": "", "raw": None}

        selected_model = model or getattr(config, "LLM_MODEL_NAME", None) or "openrouter/auto"
        payload = {
            "model": selected_model,
            "messages": self._build_messages(user_input, history=history, memory_summary=memory_summary),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        referer = kwargs.get("http_referer")
        title = kwargs.get("x_title")
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title

        start = time.perf_counter()
        try:
            resp = httpx.post(self._chat_url(self.base_url), json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            # OpenRouter's chat response is OpenAI-compatible, but keep a small
            # fallback for older response shapes used by local tests.
            text = ""
            if isinstance(data, dict):
                choices = data.get("choices") or []
                if choices and isinstance(choices[0], dict):
                    message = choices[0].get("message")
                    if isinstance(message, dict):
                        text = message.get("content", "")
                    else:
                        text = choices[0].get("text", "")
                elif "output" in data:
                    text = data.get("output")
            elapsed = time.perf_counter() - start
            return {"text": text, "raw": data, "latency": elapsed}
        except Exception:
            logger.exception("OpenRouterProvider request failed")
            return {"text": "", "raw": None}
