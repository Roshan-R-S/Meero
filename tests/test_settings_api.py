import json
from pathlib import Path

import pytest

import config
import backend.app as app_module
from fastapi.testclient import TestClient


def make_client(monkeypatch):
    # Ensure API key checks behave as configured in tests
    return TestClient(app_module.app)


def test_get_and_update_settings_writes_file(tmp_path, monkeypatch):
    # Configure API key requirement and set a key
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "s3cr3t")

    settings_file = tmp_path / "settings.json"
    # Point the app to the temp settings path
    monkeypatch.setattr(app_module, "_settings_path", lambda: str(settings_file))

    client = make_client(monkeypatch)

    # Initially no file -> GET returns empty dict
    r = client.get("/settings", headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 200
    assert r.json() == {}

    payload = {"wake_word_enabled": True, "voice_rate": 1.1}
    r = client.post("/settings", json=payload, headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 200
    assert settings_file.exists()

    data = json.loads(settings_file.read_text(encoding="utf-8"))
    # Only provided keys appear
    assert data.get("wake_word_enabled") is True
    assert abs(data.get("voice_rate") - 1.1) < 1e-6

    # GET now returns the saved settings
    r = client.get("/settings", headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 200
    assert r.json().get("wake_word_enabled") is True


def test_settings_endpoint_requires_local_request(monkeypatch):
    # Make the request appear non-local
    monkeypatch.setattr(app_module, "_is_local_request", lambda req: False)
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "s3cr3t")

    client = make_client(monkeypatch)
    r = client.get("/settings", headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 403


def test_settings_rejects_unknown_fields(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "s3cr3t")
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(app_module, "_settings_path", lambda: str(settings_file))

    client = make_client(monkeypatch)

    # Unknown extra field should be rejected by Pydantic (422)
    payload = {"wake_word_enabled": True, "not_a_valid_field": 123}
    r = client.post("/settings", json=payload, headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 422


def test_settings_validates_voice_rate_range(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "s3cr3t")
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(app_module, "_settings_path", lambda: str(settings_file))

    client = make_client(monkeypatch)

    # voice_rate below minimum (0.5) should be rejected
    payload = {"voice_rate": 0.1}
    r = client.post("/settings", json=payload, headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 422

    # voice_rate above maximum (2.0) should be rejected
    payload = {"voice_rate": 3.0}
    r = client.post("/settings", json=payload, headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 422

    # voice_rate within range should be accepted
    payload = {"voice_rate": 1.5}
    r = client.post("/settings", json=payload, headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 200

