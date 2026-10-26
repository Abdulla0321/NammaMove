"""Offline DDL is always tested; real PostGIS tests require a disposable *_test DB."""

import io
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.models import Commuter, Operator, Stop, Vehicle
from conftest import auth, make_profile
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[2]


def migration_config(output=None):
    return Config(str(ROOT / "alembic.ini"), output_buffer=output)


def test_postgresql_ddl_contains_spatial_constraints_and_rls(monkeypatch):
    # This is SQL generation, not evidence of a running PostgreSQL server.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/nammamove_test")
    buffer = io.StringIO()
    command.upgrade(migration_config(buffer), "head", sql=True)
    ddl = buffer.getvalue()
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in ddl
    assert "geography(Point,4326)" in ddl
    assert "USING gist(location)" in ddl
    assert "cancellation_requires_evidence" in ddl
    assert "ENABLE ROW LEVEL SECURITY" in ddl
    assert "current_setting('nammamove.user_id', true)" in ddl
    assert "CREATE TABLE nammamove.alembic_version" in ddl
    assert "CREATE TABLE nammamove.commuters" in ddl
    downgrade = io.StringIO()
    command.downgrade(migration_config(downgrade), "0001_phase01:base", sql=True)
    assert "DROP TABLE nammamove.commuters" in downgrade.getvalue()
    assert "DROP EXTENSION" not in downgrade.getvalue()


@pytest.mark.postgres
def test_real_postgis_constraints_migration_roundtrip(postgres):
    engine, config = postgres
    command.check(config)
    with Session(engine) as db:
        assert (
            db.scalar(text("SELECT extname FROM pg_extension WHERE extname='postgis'")) == "postgis"
        )
        operator = Operator(name="Synthetic operator")
        db.add(operator)
        db.flush()
        stop = Stop(
            operator_id=operator.id,
            external_id="synthetic",
            name="Test stop",
            latitude=12.97,
            longitude=77.59,
        )
        db.add(stop)
        db.flush()
        assert (
            db.scalar(text("SELECT public.ST_SRID(location::public.geometry) FROM nammamove.stops"))
            == 4326
        )
        assert (
            db.scalar(
                text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname='nammamove' AND indexname='ix_stops_location'"
                )
            )
            == "ix_stops_location"
        )
        for bad in [
            Stop(operator_id=operator.id, external_id="bad", name="Bad", latitude=91, longitude=77),
            Stop(
                operator_id=operator.id,
                external_id="synthetic",
                name="Duplicate",
                latitude=13,
                longitude=77,
            ),
            Vehicle(
                operator_id=operator.id,
                external_id="cancelled",
                service_status="confirmed_cancelled",
                feed_status="unavailable",
            ),
            Stop(
                operator_id=uuid4(), external_id="orphan", name="Orphan", latitude=13, longitude=77
            ),
        ]:
            with pytest.raises(IntegrityError), db.begin_nested():
                db.add(bad)
                db.flush()
        # Unavailable GPS remains independently uncertain and valid.
        db.add(
            Vehicle(
                operator_id=operator.id,
                external_id="unknown",
                feed_status="unavailable",
                service_status="uncertain",
            )
        )
        db.flush()
        db.rollback()
    command.downgrade(config, "base")
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='nammamove' AND table_name='commuters'"
                )
            )
            == 0
        )
    command.upgrade(config, "head")


@pytest.mark.postgres
def test_real_rls_blocks_cross_user_and_missing_identity(postgres):
    engine, config = postgres
    a, b = uuid4(), uuid4()
    with Session(engine) as db:
        db.add_all(
            [Commuter(id=a, display_name="Synthetic A"), Commuter(id=b, display_name="Synthetic B")]
        )
        db.commit()
    role = "nm_test_" + uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
            connection.execute(text(f"GRANT USAGE ON SCHEMA nammamove TO {role}"))
            connection.execute(
                text(
                    f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA nammamove TO {role}"
                )
            )
            connection.execute(text(f"SET LOCAL ROLE {role}"))
            assert connection.scalar(text("SELECT count(*) FROM nammamove.commuters")) == 0
            connection.execute(
                text(
                    "SELECT set_config('nammamove.user_id', :uid, true), set_config('nammamove.role', 'commuter', true)"
                ),
                {"uid": str(a)},
            )
            assert connection.execute(
                text("SELECT id FROM nammamove.commuters")
            ).scalars().all() == [a]
            assert (
                connection.execute(
                    text("UPDATE nammamove.commuters SET display_name=:name WHERE id=:id"),
                    {"name": "Attempted edit", "id": b},
                ).rowcount
                == 0
            )
        finally:
            transaction.rollback()  # Removes temporary role/grants and transaction-local identity.
    with engine.connect() as connection:
        assert not connection.scalar(
            text("SELECT NULLIF(current_setting('nammamove.user_id', true),'')")
        )


@pytest.mark.postgres
def test_real_persistent_api_and_readiness(postgres, secured):
    engine, config = postgres
    app, client, sqlite_engine, token, *_ = secured
    app.state.database.engine = engine
    app.state.database.sessions = sessionmaker(engine, expire_on_commit=False)
    make_profile(client, token())
    result = client.post(
        "/v1/journeys",
        headers=auth(token()),
        json={"origin": "Electronic City", "destination": "MG Road"},
    )
    assert result.status_code == 201
    assert client.get("/v1/journeys", headers=auth(token(subject=uuid4()))).json() == []
    assert client.get("/health/ready").status_code == 200


@pytest.mark.postgres
def test_failed_migration_rolls_back_all_revision_ddl(postgres, monkeypatch):
    engine, config = postgres
    command.downgrade(config, "base")
    from alembic.operations import Operations

    original = Operations.execute

    def fail_at_spatial_index(self, sql, *args, **kwargs):
        if str(sql).startswith("CREATE INDEX ix_stops_location"):
            raise RuntimeError("Injected migration failure")
        return original(self, sql, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Operations, "execute", fail_at_spatial_index)
        with pytest.raises(RuntimeError, match="Injected migration failure"):
            command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='nammamove' AND table_name='commuters'"
                )
            )
            == 0
        )
    command.upgrade(config, "head")


@pytest.mark.postgres
def test_non_owner_runtime_api_and_pool_identity_reset(postgres, secured):
    engine, config = postgres
    app, client, sqlite_engine, token, *_ = secured
    role = "nm_runtime_" + uuid4().hex
    # Execute the checked-in grant script itself, using an isolated test role.
    grant_script = (ROOT / "backend/sql/runtime_role.sql").read_text()
    grant_sql = "\n".join(
        line for line in grant_script.splitlines() if not line.lstrip().startswith("--")
    )
    with engine.begin() as connection:
        for statement in grant_sql.replace("nammamove_api", role).split(";"):
            if statement.strip():
                connection.execute(text(statement))
    runtime = create_engine(
        engine.url,
        connect_args={"options": f"-c role={role}"},
        hide_parameters=True,
        pool_size=1,
        max_overflow=0,
    )
    app.state.database.engine = runtime
    app.state.database.sessions = sessionmaker(runtime, expire_on_commit=False)
    try:
        with runtime.connect() as connection:
            flags = connection.execute(
                text(
                    "SELECT rolsuper, rolbypassrls, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user"
                )
            ).one()
            assert not any(flags)
            assert connection.scalar(
                text("SELECT has_schema_privilege(current_user, 'nammamove', 'USAGE')")
            )
            assert not connection.scalar(
                text("SELECT has_schema_privilege(current_user, 'nammamove', 'CREATE')")
            )
            assert connection.scalar(
                text(
                    "SELECT has_table_privilege(current_user, 'nammamove.alembic_version', 'SELECT')"
                )
            )
            assert not connection.scalar(
                text(
                    "SELECT has_table_privilege(current_user, 'nammamove.alembic_version', 'UPDATE')"
                )
            )
            for table in ("audit_events", "disruption_evidence"):
                for privilege in ("UPDATE", "DELETE"):
                    assert not connection.scalar(
                        text("SELECT has_table_privilege(current_user, :table, :privilege)"),
                        {"table": "nammamove." + table, "privilege": privilege},
                    )
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='nammamove' AND c.relkind='r' AND c.relrowsecurity"
                    )
                )
                == 27
            )
        mine = token()
        other = token(subject=uuid4())
        make_profile(client, mine)
        make_profile(client, other)
        saved = client.post(
            "/v1/journeys",
            headers=auth(mine),
            json={"origin": "Electronic City", "destination": "MG Road"},
        )
        assert saved.status_code == 201
        assert client.get("/v1/journeys", headers=auth(other)).json() == []
        assert (
            client.get("/v1/journeys/" + saved.json()["id"], headers=auth(other)).status_code == 404
        )
        assert len(client.get("/v1/journeys", headers=auth(mine)).json()) == 1
        with runtime.connect() as connection:
            assert not connection.scalar(
                text("SELECT NULLIF(current_setting('nammamove.user_id', true),'')")
            )
            assert connection.scalar(text("SELECT count(*) FROM nammamove.journeys")) == 0
        assert client.delete("/v1/me", headers=auth(mine)).status_code == 204
    finally:
        runtime.dispose()
        with engine.begin() as connection:
            connection.execute(text(f"DROP OWNED BY {role}"))
            connection.execute(text(f"DROP ROLE {role}"))
