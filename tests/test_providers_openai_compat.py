import json
import httpx
import pytest

from ai.providers.openai_compat import OpenAICompatProvider


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


def test_openai_compat_generate_monkeypatch(monkeypatch):
    provider = OpenAICompatProvider(api_key="key", base_url="https://api.test")

    sample = {"choices": [{"message": {"content": "Hello world"}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        assert url.endswith("/chat/completions")
        return DummyResponse(status_code=200, json_data=sample)

    monkeypatch.setattr("httpx.post", fake_post)
    out = provider.generate("hi there", history=[("hi","hello")])
    assert out["text"] == "Hello world"
