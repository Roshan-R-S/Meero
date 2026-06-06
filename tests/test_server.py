"""API tests for the FastAPI backend using TestClient."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a TestClient, mocking heavy dependencies."""
    with patch("backend.app.NeuralNet") as mock_nn, \
         patch("backend.app.LLMEngine") as mock_llm:
        # Mock NeuralNet
        mock_brain = MagicMock()
        mock_brain.predict.return_value = None  # Default: fallback to LLM
        mock_nn.return_value = mock_brain

        # Mock LLMEngine
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_response.return_value = "Test LLM response"
        mock_llm.return_value = mock_llm_instance

        # Import AFTER mocks are in place
        from backend.app import app
        # Reset rate limiter for each test
        import backend.app as server
        server.LAST_COMMAND_TIME = 0
        server.CLIENT_COMMAND_TIMES.clear()
        server.config.MEERO_API_KEY = ""
        server.config.REQUIRE_API_KEY = False
        server.config.PROTECT_METRICS = False
        yield TestClient(app)


class TestRootEndpoint:
    def test_root_returns_status(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "Meero is online"


class TestCommandEndpoint:
    def test_health_returns_status(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_metrics_public_by_default(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "PROTECT_METRICS", False)
        response = client.get("/metrics")

        assert response.status_code == 200

    def test_metrics_requires_api_key_when_protected(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "PROTECT_METRICS", True)
        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.get("/metrics")

        assert response.status_code == 401

    def test_metrics_accepts_valid_api_key_when_protected(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "PROTECT_METRICS", True)
        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.get("/metrics", headers={"x-meero-api-key": "secret-key"})

        assert response.status_code == 200

    def test_metrics_fails_closed_when_key_required_but_missing(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "PROTECT_METRICS", True)
        monkeypatch.setattr(server.config, "REQUIRE_API_KEY", True)
        monkeypatch.setattr(server.config, "MEERO_API_KEY", "")
        response = client.get("/metrics")

        assert response.status_code == 500
        assert response.json()["detail"] == "API key is required but not configured"

    def test_debug_health_requires_api_key_when_configured(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.get("/debug/health")

        assert response.status_code == 401

    def test_debug_health_returns_detailed_status_with_valid_api_key(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.get("/debug/health", headers={"x-meero-api-key": "secret-key"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "web_safe_mode" in data

    def test_valid_command_returns_200(self, client):
        response = client.post("/command", json={"command": "what time is it"})
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "action_status" in data
        assert "sentiment" in data

    def test_time_command(self, client):
        response = client.post("/command", json={"command": "what time is it"})
        assert response.status_code == 200
        data = response.json()
        assert data["action_status"] == "success"
        # Actions handles this directly and speaks via mock,
        # so the response comes from the mock engine captured output
        assert len(data["response"]) > 0

    def test_joke_command(self, client):
        response = client.post("/command", json={"command": "tell me a joke"})
        assert response.status_code == 200
        data = response.json()
        assert data["action_status"] == "success"
        assert len(data["response"]) > 0

    def test_unknown_command_uses_fallback(self, client):
        response = client.post("/command", json={"command": "what is the meaning of life"})
        assert response.status_code == 200
        data = response.json()
        assert data["action_status"] == "success"
        # Should contain the mocked LLM response
        assert len(data["response"]) > 0

    def test_response_has_sentiment(self, client):
        response = client.post("/command", json={"command": "tell me a joke"})
        data = response.json()
        assert data["sentiment"] in ["positive", "negative", "neutral"]

    def test_empty_command_body_returns_422(self, client):
        response = client.post("/command", json={})
        assert response.status_code == 422  # Validation error

    def test_sensitive_command_requires_confirmation(self, client, monkeypatch):
        monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
        monkeypatch.setattr("config.WEB_SAFE_MODE", False)
        response = client.post("/command", json={"command": "open settings"})
        assert response.status_code == 200
        data = response.json()
        assert data["action_status"] == "confirmation_required"
        assert data.get("pending_command") == "open settings"

    def test_delete_command_requires_confirmation(self, client):
        response = client.post("/command", json={"command": "delete all files"})
        assert response.status_code == 200
        data = response.json()
        assert data["action_status"] == "confirmation_required"
        assert data.get("pending_command") == "delete all files"

    @patch("core.actions.app_launcher.find_and_open_app", return_value=(True, "Opening settings."))
    def test_sensitive_command_executes_after_confirm(self, mock_open, client, monkeypatch):
        monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
        monkeypatch.setattr("config.WEB_SAFE_MODE", False)
        # Step 1: request confirmation
        client.post("/command", json={"command": "open settings"})

        # Step 2: explicit confirmation executes the pending command
        response = client.post(
            "/command",
            json={
                "command": "yes",
                "confirm": True,
                "pending_command": "open settings",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action_status"] == "success"
        mock_open.assert_called_once()

    def test_command_requires_api_key_when_configured(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.post("/command", json={"command": "time"})

        assert response.status_code == 401

    def test_command_rejects_wrong_api_key_when_configured(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.post(
            "/command",
            json={"command": "time"},
            headers={"x-meero-api-key": "wrong-key"},
        )

        assert response.status_code == 401

    def test_command_accepts_valid_api_key_when_configured(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.post(
            "/command",
            json={"command": "time"},
            headers={"x-meero-api-key": "secret-key"},
        )

        assert response.status_code == 200
        assert response.json()["action_status"] == "success"

    def test_command_requires_configured_key_when_required(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "")
        monkeypatch.setattr(server.config, "REQUIRE_API_KEY", True)
        response = client.post("/command", json={"command": "time"})

        assert response.status_code == 500
        assert response.json()["detail"] == "API key is required but not configured"

    def test_desktop_command_blocked_in_web_safe_mode(self, client, monkeypatch):
        monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
        monkeypatch.setattr("config.WEB_SAFE_MODE", True)

        response = client.post("/command", json={"command": "volume up"})

        assert response.status_code == 200
        data = response.json()
        assert data["action_status"] == "blocked"
        assert data["metadata"]["fallback_reason"] == "desktop_mode_disabled"


class TestSentiment:
    def test_analyze_sentiment_positive(self):
        from backend.app import analyze_sentiment
        result = analyze_sentiment("Great job, everything is working perfectly!")
        assert result == "positive"

    def test_analyze_sentiment_negative(self):
        from backend.app import analyze_sentiment
        result = analyze_sentiment("This is terrible, nothing works at all.")
        assert result == "negative"

    def test_analyze_sentiment_neutral(self):
        from backend.app import analyze_sentiment
        result = analyze_sentiment("The time is 3:00 PM")
        assert result == "neutral"


class TestRateLimiting:
    def test_rate_limit_blocks_rapid_requests(self, client, monkeypatch):
        """Two commands within 1 second should trigger rate limiting."""
        import backend.app as server
        server.LAST_COMMAND_TIME = 0
        server.CLIENT_COMMAND_TIMES.clear()
        monkeypatch.setattr(server, "RATE_LIMIT_COOLDOWN", 60.0)

        r1 = client.post("/command", json={"command": "time"})
        r2 = client.post("/command", json={"command": "time"})

        # At least one should succeed, the other may be rate-limited
        responses = [r1.json(), r2.json()]
        statuses = [r["action_status"] for r in responses]
        assert "success" in statuses
        assert "rate_limited" in statuses

    def test_rate_limit_is_per_client(self, monkeypatch):
        from backend.app import app
        import backend.app as server

        server.LAST_COMMAND_TIME = 0
        server.CLIENT_COMMAND_TIMES.clear()
        monkeypatch.setattr(server, "RATE_LIMIT_COOLDOWN", 60.0)

        first_client = TestClient(app, client=("127.0.0.1", 5000))
        second_client = TestClient(app, client=("127.0.0.2", 5000))

        first = first_client.post("/command", json={"command": "time"})
        second = second_client.post("/command", json={"command": "time"})

        assert first.json()["action_status"] == "success"
        assert second.json()["action_status"] == "success"

    def test_rate_limit_fail_open_false(self, monkeypatch):
        from backend.app import app
        import backend.app as server

        server.LAST_COMMAND_TIME = 0
        server.CLIENT_COMMAND_TIMES.clear()
        monkeypatch.setattr(server.config, "RATE_LIMIT_FAIL_OPEN", False)

        async def failing_limiter(request):
            raise RuntimeError("Redis connection failed")
            
        monkeypatch.setattr(server.FastAPILimiter, "redis", True) # Mock initialized state
        monkeypatch.setattr(server, "_RATE_LIMITER_READY", True)
        monkeypatch.setattr(server.RateLimiter, "__call__", lambda self, req: failing_limiter(req))

        client = TestClient(app)
        response = client.post("/command", json={"command": "time"})
        
        assert response.status_code == 503
        assert response.json().get("detail") == "Rate limiter unavailable"


class TestSettingsEndpoint:
    def test_settings_rejects_unknown_keys(self, client):
        response = client.post("/settings", json={"unknown": True})

        assert response.status_code == 422

    @patch("backend.app.os.replace")
    @patch("json.dump")
    @patch("builtins.open")
    def test_settings_accepts_valid_schema(self, mock_open, mock_dump, mock_replace, client):
        response = client.post(
            "/settings",
            json={
                "wake_word_enabled": True,
                "voice_rate": 1.1,
                "voice_pitch": 0.9,
            },
        )

        assert response.status_code == 200
        assert mock_open.call_args.args[0].endswith("settings.json.tmp")
        mock_dump.assert_called_once()
        assert mock_dump.call_args.args[0] == {
            "wake_word_enabled": True,
            "voice_rate": 1.1,
            "voice_pitch": 0.9,
        }
        assert mock_replace.call_args.args[0].endswith("settings.json.tmp")
        assert mock_replace.call_args.args[1].endswith("settings.json")

    def test_settings_post_requires_api_key_when_configured(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.post("/settings", json={"wake_word_enabled": True})

        assert response.status_code == 401

    def test_settings_write_failure_cleans_temp_file(self, client, monkeypatch, tmp_path):
        import backend.app as server

        settings_path = tmp_path / "settings.json"
        tmp_settings_path = tmp_path / "settings.json.tmp"
        monkeypatch.setattr(server, "_settings_path", lambda: str(settings_path))

        def fail_replace(_src, _dst):
            raise OSError("disk full")

        monkeypatch.setattr(server.os, "replace", fail_replace)

        response = client.post("/settings", json={"wake_word_enabled": True})

        assert response.status_code == 500
        assert not settings_path.exists()
        assert not tmp_settings_path.exists()

    def test_settings_is_local_only(self):
        from backend.app import app

        remote_client = TestClient(app, client=("203.0.113.10", 5000))
        response = remote_client.get("/settings")

        assert response.status_code == 403

    def test_settings_requires_api_key_when_configured(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.get("/settings")

        assert response.status_code == 401

    def test_settings_accepts_valid_api_key_when_configured(self, client, monkeypatch):
        import backend.app as server

        monkeypatch.setattr(server.config, "MEERO_API_KEY", "secret-key")
        response = client.get("/settings", headers={"x-meero-api-key": "secret-key"})

        assert response.status_code == 200
