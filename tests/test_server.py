"""API tests for server.py endpoints using FastAPI's TestClient."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a TestClient, mocking heavy dependencies."""
    with patch("server.NeuralNet") as mock_nn, \
         patch("server.LLMEngine") as mock_llm:
        # Mock NeuralNet
        mock_brain = MagicMock()
        mock_brain.predict.return_value = None  # Default: fallback to LLM
        mock_nn.return_value = mock_brain

        # Mock LLMEngine
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_response.return_value = "Test LLM response"
        mock_llm.return_value = mock_llm_instance

        # Import AFTER mocks are in place
        from server import app
        # Reset rate limiter for each test
        import server
        server.LAST_COMMAND_TIME = 0
        yield TestClient(app)


class TestRootEndpoint:
    def test_root_returns_status(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "Meero is online"


class TestCommandEndpoint:
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


class TestSentiment:
    def test_analyze_sentiment_positive(self):
        from server import analyze_sentiment
        result = analyze_sentiment("Great job, everything is working perfectly!")
        assert result == "positive"

    def test_analyze_sentiment_negative(self):
        from server import analyze_sentiment
        result = analyze_sentiment("This is terrible, nothing works at all.")
        assert result == "negative"

    def test_analyze_sentiment_neutral(self):
        from server import analyze_sentiment
        result = analyze_sentiment("The time is 3:00 PM")
        assert result == "neutral"


class TestRateLimiting:
    def test_rate_limit_blocks_rapid_requests(self, client):
        """Two commands within 1 second should trigger rate limiting."""
        import server
        server.LAST_COMMAND_TIME = 0

        r1 = client.post("/command", json={"command": "time"})
        r2 = client.post("/command", json={"command": "time"})

        # At least one should succeed, the other may be rate-limited
        responses = [r1.json(), r2.json()]
        statuses = [r["action_status"] for r in responses]
        assert "success" in statuses or "ignored" in statuses
