import pytest

import config
import backend.app as app_module
from fastapi.testclient import TestClient


def make_client(monkeypatch):
    return TestClient(app_module.app)


def test_metrics_accessible_without_key_when_not_protected(monkeypatch):
    monkeypatch.setattr(config, "PROTECT_METRICS", False)
    client = make_client(monkeypatch)

    r = client.get("/metrics")
    assert r.status_code == 200


def test_metrics_requires_key_when_protected(monkeypatch):
    monkeypatch.setattr(config, "PROTECT_METRICS", True)
    monkeypatch.setattr(config, "MEERO_API_KEY", "s3cr3t")
    client = make_client(monkeypatch)

    # No key -> 401
    r = client.get("/metrics")
    assert r.status_code == 401

    # Wrong key -> 401
    r = client.get("/metrics", headers={"x-meero-api-key": "wrong"})
    assert r.status_code == 401

    # Correct key -> 200
    r = client.get("/metrics", headers={"x-meero-api-key": "s3cr3t"})
    assert r.status_code == 200
