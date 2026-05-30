import json
from types import SimpleNamespace

import pytest

import config
import backend.app as app_module
from fastapi.testclient import TestClient


def setup_app(monkeypatch):
    # Ensure the app uses a predictable, test-only command executor
    def fake_execute_command(*args, **kwargs):
        return SimpleNamespace(
            response="ok",
            action_status="done",
            sentiment="neutral",
            pending_command=None,
            metadata={
                "engine": "test",
                "confidence": 1.0,
            },
        )

    monkeypatch.setattr(app_module, "execute_command", fake_execute_command)
    return TestClient(app_module.app)


def test_command_requires_api_key_and_rejects_wrong_key(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "s3cr3t")
    client = setup_app(monkeypatch)

    payload = {"command": "hello"}

    # No header -> 401
    r = client.post("/command", json=payload)
    assert r.status_code == 401
    assert r.json().get("detail") == "Invalid API key"

    # Wrong header -> 401
    r = client.post("/command", json=payload, headers={"x-meero-api-key": "wrong"})
    assert r.status_code == 401

    # Correct header -> 200 and our fake executor is used
    r = client.post("/command", json=payload, headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 200
    j = r.json()
    assert j["action_status"] == "done"
    assert j["metadata"]["engine"] == "test"


def test_debug_health_requires_api_key(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "s3cr3t")
    client = setup_app(monkeypatch)

    r = client.get("/debug/health")
    assert r.status_code == 401

    r = client.get("/debug/health", headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_metrics_protected_by_api_key_when_enabled(monkeypatch):
    # Enable protection and configure a key
    monkeypatch.setattr(config, "PROTECT_METRICS", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "s3cr3t")
    client = setup_app(monkeypatch)

    r = client.get("/metrics")
    assert r.status_code == 401

    r = client.get("/metrics", headers={"x-meero-api-key": "s3cr3t"})
    # If Prometheus client isn't installed the endpoint returns a text response,
    # but it should still accept a valid API key and respond successfully.
    assert r.status_code == 200
