import json
import urllib.error
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from conftest import auth, make_profile
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm


def test_missing_auth_is_rejected_before_database():
    from app.config import Settings
    from app.main import create_app
    from fastapi.testclient import TestClient

    with TestClient(
        create_app(Settings(_env_file=None, database_url=None, supabase_url=None))
    ) as client:
        assert client.get("/v1/me").status_code == 401
        assert client.get("/v1/me", headers=auth("fake")).status_code == 503
        assert client.get("/health").status_code == 200
        assert client.get("/health/ready").status_code == 503


@pytest.mark.parametrize(
    "changes",
    [
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        {"iat": datetime.now(timezone.utc) + timedelta(hours=1)},
        {"iss": "https://attacker.invalid/auth/v1"},
        {"aud": "wrong"},
        {"sub": "not-a-uuid"},
        {"role": "service_role"},
        {"role": "anon"},
        {"is_anonymous": True},
        {"exp": None},
        {"app_metadata": {"nammamove_role": "root"}},
    ],
)
def test_invalid_claims_fail_closed(secured, changes):
    app, client, engine, token, *_ = secured
    response = client.get("/v1/me", headers=auth(token(**changes)))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_required_claim_signature_and_algorithm_checks(secured):
    app, client, engine, token, keys, private, user = secured
    good = token()
    claims = jwt.decode(good, options={"verify_signature": False})
    del claims["exp"]
    missing = jwt.encode(claims, private, algorithm="ES256", headers={"kid": "test-key"})
    other_key = ec.generate_private_key(ec.SECP256R1())
    tampered = jwt.encode(claims, other_key, algorithm="ES256", headers={"kid": "test-key"})
    unsigned = jwt.encode(claims, key="", algorithm="none", headers={"kid": "test-key"})
    hmac = jwt.encode(
        claims,
        key="test-only-fake-shared-key-32-bytes-long",
        algorithm="HS256",
        headers={"kid": "test-key"},
    )
    for invalid in [missing, tampered, unsigned, hmac, "malformed", "x" * 8193]:
        assert client.get("/v1/me", headers=auth(invalid)).status_code == 401


def test_untrusted_user_metadata_cannot_elevate_roles(secured):
    app, client, engine, token, *_ = secured
    commuter = token(user_metadata={"nammamove_role": "admin"})
    make_profile(client, commuter)
    assert (
        client.post("/v1/operators", headers=auth(commuter), json={"name": "Test"}).status_code
        == 403
    )
    make_profile(client, token(role="admin"))
    assert (
        client.post(
            "/v1/operators", headers=auth(token(role="admin")), json={"name": "Test"}
        ).status_code
        == 201
    )


def test_jwks_rotation_revocation_and_provider_outage(secured, monkeypatch):
    app, client, engine, token, keys, private, user = secured
    make_profile(client, token())
    new_key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(new_key.public_key()))
    public.update({"kid": "rotated", "alg": "ES256", "use": "sig"})
    claims = jwt.decode(token(), options={"verify_signature": False})
    rotated = jwt.encode(claims, new_key, algorithm="ES256", headers={"kid": "rotated"})
    keys["keys"] = [public]
    # Model expiry of the 60s JWKS set cache; key-level immortal cache is disabled.
    app.state.verifier.jwks.jwk_set_cache.put(None)
    assert client.get("/v1/me", headers=auth(rotated)).status_code == 200
    assert client.get("/v1/me", headers=auth(token())).status_code == 401
    app.state.verifier.jwks.jwk_set_cache.put(None)

    def offline(*args, **kwargs):
        raise urllib.error.URLError("sensitive-provider-internal-error")

    monkeypatch.setattr("urllib.request.OpenerDirector.open", offline)
    result = client.get("/v1/me", headers=auth(rotated))
    assert result.status_code == 503
    assert "sensitive" not in result.text


def test_production_config_requires_https_and_fails_without_credentials():
    from app.config import Settings
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", database_url=None, supabase_url=None)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, supabase_url="http://untrusted.invalid")
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url="password-sensitive-invalid-url")
    assert "password-sensitive-invalid-url" not in str(error.value)
    assert (
        Settings(
            _env_file=None, app_env="test", database_url=None, supabase_url="http://localhost:54321"
        ).issuer
        == "http://localhost:54321/auth/v1"
    )


def test_simulation_can_be_disabled(secured):
    app, client, engine, token, *_ = secured
    app.state.settings.simulation_enabled = False
    assert client.get("/network").status_code == 404
    assert client.get("/services/status?operator_cancelled=true").status_code == 404
    assert (
        client.post("/journeys/plan", json={"origin": "A", "destination": "B"}).status_code == 404
    )
    assert client.get("/health").json() == {"status": "ok", "mode": "simulation"}
    make_profile(client, token())
    assert (
        client.post(
            "/v1/journeys", headers=auth(token()), json={"origin": "A", "destination": "B"}
        ).status_code
        == 503
    )
