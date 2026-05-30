from typing import Optional
import config
import os

from .base import ProviderBase
from .openai_compat import OpenAICompatProvider
from .openrouter import OpenRouterProvider
from .huggingface import HuggingFaceProvider


def get_provider(provider_name: Optional[str] = None) -> Optional[ProviderBase]:
    name = provider_name or config.LLM_API_PROVIDER
    if not name:
        return None
    name = name.lower()
    if name in {"openai", "openai_compat", "openai-compatible"}:
        return OpenAICompatProvider()
    if name in {"openrouter", "open_router"}:
        # prefer a dedicated OpenRouter adapter
        return OpenRouterProvider(api_key=config.OPENROUTER_API_KEY, base_url=config.OPENROUTER_BASE_URL)
    if name in {"huggingface", "hf", "hugging-face"}:
        return HuggingFaceProvider(api_key=config.HUGGINGFACE_API_KEY, base_url=config.HUGGINGFACE_BASE_URL)
    if name in {"nvidia", "moonshot", "kimi"}:
        # Attempt to use OpenAI-compat with NVIDIA endpoint if provided
        return OpenAICompatProvider(api_key=config.NVIDIA_API_KEY, base_url=config.NVIDIA_BASE_URL)

    # Unknown provider -> None
    return None
