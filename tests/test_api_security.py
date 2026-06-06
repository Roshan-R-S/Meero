import pytest
from fastapi.testclient import TestClient
from backend.app import app
import config

client = TestClient(app)

def test_memory_requires_auth_and_local(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "test-key")
    # Public request, no auth
    resp = client.get("/memory")
    assert resp.status_code in [401, 403]
    
    resp = client.delete("/memory")
    assert resp.status_code in [401, 403]

def test_model_status_requires_auth_and_local(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "test-key")
    resp = client.get("/model/status")
    assert resp.status_code in [401, 403]

def test_settings_requires_auth_and_local(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "test-key")
    resp = client.get("/settings")
    assert resp.status_code in [401, 403]
    
    resp = client.post("/settings", json={"text_output_enabled": True})
    assert resp.status_code in [401, 403]

def test_authenticated_local_model_status(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "test-key")
    
    resp = client.get(
        "/model/status", 
        headers={"x-meero-api-key": "test-key", "host": "localhost:8000"}
    )
    # 200 OK because it is local (localhost) and has the correct API key
    assert resp.status_code == 200
    data = resp.json()
    assert "gguf_llm" in data
    assert "neural_net" in data
