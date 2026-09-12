"""Tests for spoofed headers, /debug/health local-only enforcement, and close_app allowlist guard."""

import pytest
from fastapi.testclient import TestClient
from backend.app import app
import config

client = TestClient(app)


class TestDebugHealthLocalOnly:
    """Verify /debug/health requires local request after the hardening change."""

    def test_debug_health_accessible_locally(self, monkeypatch):
        monkeypatch.setattr(config, "REQUIRE_API_KEY", False)
        resp = client.get("/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_debug_health_returns_internal_state(self, monkeypatch):
        monkeypatch.setattr(config, "REQUIRE_API_KEY", False)
        resp = client.get("/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm_loaded" in data
        assert "local_desktop_mode" in data


class TestSpoofedHeaders:
    """Verify that spoofed X-Forwarded-For headers cannot bypass local-only guards."""

    def test_local_only_endpoint_with_spoofed_header(self, monkeypatch):
        """The local-only check uses request.client.host, not X-Forwarded-For.
        
        Even with a spoofed header, the testclient should still be considered
        local because its actual client.host is 'testclient'.
        """
        monkeypatch.setattr(config, "REQUIRE_API_KEY", False)
        resp = client.get(
            "/memory",
            headers={"X-Forwarded-For": "8.8.8.8"},
        )
        # TestClient is always 'testclient' which is in LOCAL_HOSTS,
        # so the request should succeed regardless of X-Forwarded-For.
        assert resp.status_code == 200

    def test_local_only_ignores_xff_for_auth(self, monkeypatch):
        """Verify is_local_request does not trust X-Forwarded-For header."""
        from backend.middleware.auth import is_local_request
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {"X-Forwarded-For": "127.0.0.1"}

        # Should NOT be considered local because client.host is not local
        assert is_local_request(mock_request) is False


class TestCloseAppAllowlistGuard:
    """Verify close_app_by_name rejects unknown apps in LOCAL_DESKTOP_MODE."""

    def test_unknown_app_rejected_in_desktop_mode(self, monkeypatch):
        import app_launcher
        monkeypatch.setattr(config, "LOCAL_DESKTOP_MODE", True)
        monkeypatch.setattr(config, "APP_CLOSE_ALLOWLIST", ("notepad",))
        success, message = app_launcher.close_app_by_name("totally_unknown_app")
        assert success is False
        assert "not in the known process list" in message or "not allowed" in message

    def test_known_app_allowed_in_desktop_mode(self, monkeypatch):
        import app_launcher
        monkeypatch.setattr(config, "LOCAL_DESKTOP_MODE", True)
        monkeypatch.setattr(config, "APP_CLOSE_ALLOWLIST", ("notepad",))
        # notepad is both in the allowlist AND in the process_map
        success, message = app_launcher.close_app_by_name("notepad")
        # It might fail to actually close (not running), but it should not be blocked
        assert "not in the known process list" not in message
