import httpx
import pytest

from ai.providers.huggingface import HuggingFaceProvider


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


def test_huggingface_generate(monkeypatch):
    provider = HuggingFaceProvider(api_key="hf", base_url="https://hf.test/models")

    sample = [{"generated_text": "HF response"}]

    def fake_post(url, json=None, headers=None, timeout=None):
        assert url.endswith("/gpt2")
        return DummyResponse(status_code=200, json_data=sample)

    monkeypatch.setattr("httpx.post", fake_post)
    out = provider.generate("hello", model="gpt2")
    assert out["text"] == "HF response"
