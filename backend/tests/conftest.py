import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from app.config import Settings
from app.main import create_app
from app.models import Base
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
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


@pytest.fixture
def postgres(monkeypatch):
    url = os.environ.get("NAMMAMOVE_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set NAMMAMOVE_TEST_DATABASE_URL to an empty disposable PostgreSQL/PostGIS *_test database"
        )
    parsed = make_url(url)
    if (
        parsed.drivername != "postgresql+psycopg"
        or not parsed.database
        or not parsed.database.endswith("_test")
    ):
        pytest.fail("Refusing integration DDL outside a dedicated *_test PostgreSQL database")
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})
    with engine.connect() as connection:
        exists = connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name='nammamove')"
            )
        )
        if exists:
            pytest.fail(
                "Refusing to modify an existing nammamove schema; use a new empty test database"
            )
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, "head")
    try:
        yield engine, config
    finally:
        command.downgrade(config, "base")
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE nammamove.alembic_version"))
            connection.execute(text("DROP SCHEMA nammamove"))
        engine.dispose()
