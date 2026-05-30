from typing import Any, Dict, Optional


class ProviderBase:
    """Minimal provider interface for external LLM adapters.

    Implementations should return a normalized dict with at least a `text` key.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    def generate(self, user_input: str, history=None, memory_summary: str = None, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()
