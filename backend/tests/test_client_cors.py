"""Browser access is explicitly configured and does not weaken token checks."""

import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from pydantic import ValidationError


def test_mobile_web_cors_allowlist_keeps_private_api_protected():
    with TestClient(
        create_app(Settings(_env_file=None, cors_allowed_origins=["http://localhost:8081"]))
    ) as client:
        headers = {
            "Origin": "http://localhost:8081",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        }
        response = client.options("/v1/routing/plan", headers=headers)
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:8081"
        assert "access-control-allow-credentials" not in response.headers
        assert client.post("/v1/routing/plan", json={}, headers=headers).status_code == 401
        headers["Origin"] = "https://untrusted.example"
        assert client.options("/v1/routing/plan", headers=headers).status_code == 400


def test_cors_is_disabled_by_default():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:8081"})
        assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("origin", ["*", "http://untrusted.example", "https://host/path"])
def test_invalid_browser_origins_fail_configuration(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_allowed_origins=[origin])
