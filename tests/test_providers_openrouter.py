import httpx
import pytest

from ai.providers.openrouter import OpenRouterProvider


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


def test_openrouter_generate(monkeypatch):
    provider = OpenRouterProvider(api_key="ok", base_url="https://openrouter.test")

    sample = {"output": "OR response"}

    def fake_post(url, json=None, headers=None, timeout=None):
        assert url == "https://openrouter.test"
        return DummyResponse(status_code=200, json_data=sample)

    monkeypatch.setattr("httpx.post", fake_post)
    out = provider.generate("hello")
    assert out["text"] == "OR response"
