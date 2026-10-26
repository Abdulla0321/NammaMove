"""Opt-in genuine Supabase Auth + PostgreSQL acceptance; no mocks or overrides."""

import json
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import jwt
import pytest
from app.config import Settings
from app.main import create_app
from app.models import utcnow
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.engine import make_url


@pytest.mark.supabase
def test_real_supabase_sign_in_roles_and_persistent_ownership():
    config_path = os.environ.get("NAMMAMOVE_SUPABASE_ACCEPTANCE_CONFIG")
    if not config_path:
        pytest.skip(
            "Set NAMMAMOVE_SUPABASE_ACCEPTANCE_CONFIG to ignored local acceptance credentials"
        )
    config = json.loads(Path(config_path).read_text())
    database_url = make_url(config["database_url"])
    assert database_url.database and database_url.database.endswith("_test")
    assert database_url.host in {"localhost", "127.0.0.1"}
    assert urlsplit(config["supabase_url"]).hostname in {"localhost", "127.0.0.1"}
    sessions = []
    with httpx.Client(base_url=config["supabase_url"] + "/auth/v1", timeout=10) as auth:
        assert auth.get("/health").status_code == 200
        jwks = auth.get("/.well-known/jwks.json")
        assert jwks.status_code == 200
        assert any(key.get("alg") == "ES256" for key in jwks.json()["keys"])
        for user in config["users"]:
            signed_in = auth.post(
                "/token?grant_type=password",
                json={"email": user["email"], "password": user["password"]},
            )
            assert signed_in.status_code == 200
            data = signed_in.json()
            assert jwt.get_unverified_header(data["access_token"])["alg"] == "ES256"
            sessions.append(
                (data["user"]["id"], {"Authorization": "Bearer " + data["access_token"]})
            )
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=SecretStr(config["database_url"]),
        supabase_url=config["supabase_url"],
        simulation_enabled=True,
    )
    with TestClient(create_app(settings)) as api:
        assert api.get("/health/ready").status_code == 200
        for subject, headers in sessions:
            saved = api.put(
                "/v1/me", headers=headers, json={"display_name": "Synthetic Supabase acceptance"}
            )
            assert saved.status_code == 200
            assert saved.json()["id"] == subject
        first, second, moderator = (item[1] for item in sessions)
        catalog = api.get("/v1/transit/feeds", headers=first)
        assert catalog.status_code == 200
        assert catalog.json()["service_status"] == "unknown"
        assert catalog.json()["realtime_status"] == "unavailable"
        assert api.get("/v1/transit/feeds").status_code == 401
        # User one has malicious user_metadata, but no server-granted admin role.
        assert (
            api.post(
                "/v1/operators", headers=first, json={"name": "Untrusted elevation"}
            ).status_code
            == 403
        )
        assert api.get("/v1/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
        journey = api.post(
            "/v1/journeys",
            headers=first,
            json={"origin": "Electronic City", "destination": "MG Road"},
        )
        assert journey.status_code == 201
        assert journey.json()["data_mode"] == "simulation"
        path = "/v1/journeys/" + journey.json()["id"]
        assert api.get(path, headers=first).status_code == 200
        assert api.get(path, headers=second).status_code == 404
        assert api.delete(path, headers=second).status_code == 404
        report = api.post(
            "/v1/disruptions",
            headers=first,
            json={
                "kind": "delay",
                "summary": "Synthetic actual Auth test",
                "data_mode": "simulation",
            },
        )
        assert report.status_code == 201
        verification = "/v1/disruptions/" + report.json()["id"] + "/verification"
        evidence = {
            "decision": "verified",
            "evidence_source": "Synthetic operator evidence",
            "confidence": 0.9,
            "expires_at": (utcnow() + timedelta(minutes=10)).isoformat(),
        }
        assert api.post(verification, headers=first, json=evidence).status_code == 403
        assert api.post(verification, headers=moderator, json=evidence).status_code == 200
        assert api.delete(path, headers=first).status_code == 204
