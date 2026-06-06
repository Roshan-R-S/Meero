import pytest
from starlette.testclient import TestClient
import config

def test_debug_errors_hidden_in_production(monkeypatch):
    monkeypatch.setattr(config, "DEBUG_ERRORS", False)
    import backend.app as server
    
    # We will trigger a 500 error by mocking an internal function
    def failing_health():
        raise RuntimeError("Secret database connection failed!")
        
    client = TestClient(server.app, raise_server_exceptions=False)
    
    # We need an endpoint that isn't protected by API key or we can provide one.
    # We can patch a harmless endpoint like /health
    monkeypatch.setattr(server, "health", failing_health)
    
    # Add a mock route if needed, or override existing
    @server.app.get("/error_test_endpoint")
    def trigger_error():
        raise RuntimeError("Secret error details")
        
    response = client.get("/error_test_endpoint")
    assert response.status_code == 500
    
    data = response.json()
    assert data["error"] == "Internal server error"
    assert "detail" not in data

def test_debug_errors_exposed_in_development(monkeypatch):
    monkeypatch.setattr(config, "DEBUG_ERRORS", True)
    import backend.app as server
    
    client = TestClient(server.app, raise_server_exceptions=False)
    
    @server.app.get("/error_test_endpoint_debug")
    def trigger_error_debug():
        raise RuntimeError("Secret error details")
        
    response = client.get("/error_test_endpoint_debug")
    assert response.status_code == 500
    
    data = response.json()
    assert data["error"] == "Internal server error"
    assert data["detail"] == "Secret error details"
