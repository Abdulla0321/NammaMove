import io
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from app.config import Settings
from app.main import create_app
from app.models import Base
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ISSUER = "https://example.supabase.co/auth/v1"


@pytest.fixture
def secured(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(private_key.public_key()))
    public.update({"kid": "test-key", "alg": "ES256", "use": "sig"})
    keys = {"keys": [public]}

    def urlopen(opener, request, **kwargs):
        assert request.full_url == ISSUER + "/.well-known/jwks.json"
        return io.BytesIO(json.dumps(keys).encode())

    monkeypatch.setattr("urllib.request.OpenerDirector.open", urlopen)
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=None,
        supabase_url="https://example.supabase.co",
        simulation_enabled=True,
    )
    application = create_app(settings)
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": {"nammamove": None}},
    )

    @event.listens_for(engine, "connect")
    def fk_on(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    application.state.database.engine = engine
    application.state.database.sessions = sessionmaker(engine, expire_on_commit=False)
    user_id = uuid4()

    def token(subject=None, role="commuter", **changes):
        now = datetime.now(timezone.utc)
        claims = {
            "sub": str(subject or user_id),
            "iss": ISSUER,
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "role": "authenticated",
            "app_metadata": {"nammamove_role": role},
        }
        claims.update(changes)
        return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": "test-key"})

    with TestClient(application) as client:
        yield application, client, engine, token, keys, private_key, user_id
    engine.dispose()


def auth(token):
    return {"Authorization": "Bearer " + token}


def make_profile(client, token, name="Commuter"):
    response = client.put("/v1/me", headers=auth(token), json={"display_name": name})
    assert response.status_code == 200, response.text
    return response.json()
