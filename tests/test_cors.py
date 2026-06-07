from fastapi.testclient import TestClient

import config
from backend.app import app


client = TestClient(app)


def test_configured_origin_receives_cors_header():
    origin = config.CORS_ORIGINS[0]

    response = client.get("/", headers={"origin": origin})

    assert response.headers["access-control-allow-origin"] == origin


def test_unapproved_origin_does_not_receive_cors_header():
    response = client.get("/", headers={"origin": "https://unapproved.example"})

    assert "access-control-allow-origin" not in response.headers
