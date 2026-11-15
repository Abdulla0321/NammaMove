"""Genuine source-scoped worker and explicit scheduled operations acceptance."""

from concurrent.futures import ThreadPoolExecutor
from copy import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from alembic import command
from app.realtime.durable import DurableIngestion
from app.realtime.maintenance import IngestionMaintenance
from app.realtime.models import IngestionGeneration, IngestionSource
from app.transit.ingestion import ingest
from app.transit.models import TransitFeed
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_realtime_durable import clear_cache, durable, snap, static_values
from test_realtime_ingestion import NOW, at, feed, wire
from test_realtime_redis import redis_state
from test_transit import archive, manifest

__all__ = ["durable", "redis_state"]
pytestmark = [pytest.mark.postgres, pytest.mark.redis]


@pytest.fixture
def scoped(durable):
    owner, engine, _ = durable
    role = "nm_worker_" + uuid4().hex
    group_created = False
    with engine.begin() as connection:
        if not connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nammamove_ingestion')")
        ):
            script = Path("backend/sql/ingestion_role.sql").read_text()
            script = "\n".join(
                line for line in script.splitlines() if not line.lstrip().startswith("--")
            )
            for statement in script.split(";"):
                if statement.strip():
                    connection.execute(text(statement))
            group_created = True
        else:
            # Existing group can outlive a disposable schema; reapply grants only.
            script = Path("backend/sql/ingestion_role.sql").read_text()
            for statement in script.splitlines():
                if statement.startswith("GRANT "):
                    connection.execute(text(statement))
        connection.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
        connection.execute(text(f"GRANT nammamove_ingestion TO {role}"))
        connection.execute(
            text("INSERT INTO nammamove.ingestion_workers VALUES (:role,:source)"),
            {"role": role, "source": owner.adapter.source_id},
        )
    restricted = create_engine(engine.url, hide_parameters=True)

    @event.listens_for(restricted, "checkout")
    def identity(connection, record, proxy):
        with connection.cursor() as cursor:
            cursor.execute(f"SET ROLE {role}")
        connection.commit()

    worker = DurableIngestion(restricted, owner.cache, owner.dataset_id)
    try:
        yield worker, owner, engine, role
    finally:
        restricted.dispose()
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM nammamove.ingestion_workers WHERE worker_name=:role"),
                {"role": role},
            )
            connection.execute(text(f"DROP OWNED BY {role}"))
            connection.execute(text(f"DROP ROLE {role}"))
            if group_created:
                connection.execute(text("DROP OWNED BY nammamove_ingestion"))
                connection.execute(text("DROP ROLE nammamove_ingestion"))


def test_nonowner_acceptance_recovery_retention_and_original_ttl(scoped):
    worker, _, _, _ = scoped
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    assert worker.ingest(wire(feed()), now=at(1)) == "duplicate"
    clear_cache(worker)
    assert worker.recover(now=at(2))
    assert snap(worker, 2).tracking.service == "delayed"
    assert snap(worker, 91).tracking.service == "unknown"
    assert worker.retain(now=at(86400), apply=True) == {"evidence": 1, "payloads": 3}
    assert snap(worker, 86400).tracking.observed_position is None


@pytest.mark.parametrize("spoof", [False, True])
def test_catalog_scope_survives_spoofed_admin_and_accidental_grants(scoped, spoof):
    worker, owner, engine, role = scoped
    with Session(engine) as db, db.begin():
        other = ingest(db, archive(static_values()), manifest(version="other-version")).id
        db.add(TransitFeed(id="unassigned:simulation", provider="bmtc", data_mode="simulation"))
    assert other != owner.dataset_id
    with engine.begin() as connection:
        # Every static table may accidentally be readable; restrictive scope wins.
        connection.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA nammamove TO {role}"))
    with worker.engine.begin() as connection:
        if spoof:
            connection.execute(
                text(
                    "SELECT set_config('nammamove.user_id',:uid,true),set_config('nammamove.role','admin',true),set_config('nammamove.source_id','other',true)"
                ),
                {"uid": str(uuid4())},
            )
        assert connection.scalar(text("SELECT current_user")) == role
        assert connection.execute(
            text("SELECT id FROM nammamove.transit_feeds")
        ).scalars().all() == ["synthetic:simulation"]
        assert connection.execute(
            text("SELECT id FROM nammamove.transit_datasets")
        ).scalars().all() == [owner.dataset_id]
        for table in (
            "gtfs_agencies",
            "gtfs_calendar_dates",
            "gtfs_frequencies",
            "gtfs_routes",
            "gtfs_services",
            "gtfs_shape_points",
            "gtfs_shapes",
            "gtfs_stop_times",
            "gtfs_stops",
            "gtfs_transfers",
            "gtfs_trips",
        ):
            assert (
                connection.scalar(
                    text(f"SELECT count(*) FROM nammamove.{table} WHERE dataset_id=:other"),
                    {"other": other},
                )
                == 0
            )
        assert connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_worker_scope")) == 1
    with engine.begin() as connection:
        connection.execute(text(f"REVOKE SELECT ON ALL TABLES IN SCHEMA nammamove FROM {role}"))


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE nammamove.ingestion_sources SET binding_digest=repeat('0',64)",
        "UPDATE nammamove.ingestion_sources SET evidence_seconds=900",
        "UPDATE nammamove.ingestion_sources SET dataset_id=gen_random_uuid()",
        "DELETE FROM nammamove.ingestion_sources",
        "DELETE FROM nammamove.ingestion_workers",
        "UPDATE nammamove.ingestion_generations SET expires_at=statement_timestamp()",
        "UPDATE nammamove.transit_datasets SET state='validated'",
    ],
)
def test_worker_cannot_change_registration_binding_policy_or_evidence(scoped, statement):
    worker, _, _, _ = scoped
    with worker.engine.begin() as connection:
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(text(statement))
    with pytest.raises(ValueError, match="maintenance owner"):
        worker.register()


def test_unexpired_evidence_cannot_be_deleted_even_with_future_caller_clock(scoped):
    worker, _, engine, _ = scoped
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    future = datetime.now(UTC) + timedelta(days=2)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE nammamove.ingestion_generations SET expires_at=:future"),
            {"future": future},
        )
    with worker.engine.begin() as connection:
        assert connection.execute(text("DELETE FROM nammamove.ingestion_generations")).rowcount == 0
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_generations")) == 1


def test_unassigned_group_identity_and_wrong_static_binding_fail_closed(scoped):
    worker, _, _, _ = scoped
    assert not DurableIngestion(worker.engine, worker.cache, uuid4()).recover(now=NOW)
    with worker.engine.begin() as connection:
        connection.execute(text("SET LOCAL ROLE nammamove_ingestion"))
        connection.execute(
            text(
                "SELECT set_config('nammamove.role','admin',true),set_config('nammamove.user_id','spoof',true)"
            )
        )
        assert connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_sources")) == 0
        assert connection.scalar(text("SELECT count(*) FROM nammamove.transit_datasets")) == 0


def test_cross_source_read_write_delete_and_assignment_denied(scoped):
    worker, owner, engine, _ = scoped
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    with Session(engine) as db, db.begin():
        source = db.get(IngestionSource, owner.adapter.source_id)
        db.add(
            IngestionSource(
                id="other-source",
                dataset_id=source.dataset_id,
                binding_digest=source.binding_digest,
                evidence_seconds=900,
                max_generations=10,
            )
        )
        db.flush()
        db.add(
            IngestionGeneration(
                source_id="other-source",
                identity="a" * 64,
                fingerprint="b" * 64,
                outcome="rejected",
                received_at=NOW,
                expires_at=at(900),
            )
        )
    with worker.engine.begin() as connection:
        connection.execute(
            text(
                "SELECT set_config('nammamove.user_id','spoof',true),set_config('nammamove.role','admin',true),set_config('nammamove.source_id','other-source',true)"
            )
        )
        assert connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_sources")) == 1
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM nammamove.ingestion_generations WHERE source_id='other-source'"
                )
            )
            == 0
        )
        assert (
            connection.execute(
                text(
                    "UPDATE nammamove.ingestion_sources SET checkpoint=NULL WHERE id='other-source'"
                )
            ).rowcount
            == 0
        )
        assert (
            connection.execute(
                text("DELETE FROM nammamove.ingestion_generations WHERE source_id='other-source'")
            ).rowcount
            == 0
        )
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO nammamove.ingestion_generations(source_id,identity,fingerprint,outcome,received_at,expires_at,data_mode) VALUES ('other-source',repeat('c',64),repeat('d',64),'rejected',statement_timestamp(),statement_timestamp()+interval '1 hour','simulation')"
                )
            )
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text("INSERT INTO nammamove.ingestion_workers VALUES (current_user,'other-source')")
            )


@pytest.mark.parametrize(
    "field,value",
    [("prefix", "nammamove:simulation:other:"), ("version", "other-version"), ("policy", "0" * 64)],
)
def test_worker_cannot_change_registered_cache_binding(scoped, field, value):
    worker, _, _, _ = scoped
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    cache = copy(worker.cache)
    setattr(cache, field, value)
    altered = DurableIngestion(worker.engine, cache, worker.dataset_id)
    assert not altered.recover(now=at(1))
    assert altered.ingest(wire(feed(1)), now=at(1)) == "unavailable"
    assert snap(worker, 1).received_at == NOW


def test_scheduled_sql_failure_rolls_back_retention_then_retries(scoped):
    worker, _, engine, _ = scoped
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    scheduler = IngestionMaintenance(worker)

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE nammamove.ingestion_sources"):
            raise RuntimeError("private failure after evidence delete")

    event.listen(worker.engine, "before_cursor_execute", fail)
    try:
        assert scheduler.tick(now=at(86400)).status == "retry"
    finally:
        event.remove(worker.engine, "before_cursor_execute", fail)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_generations")) == 1
    assert scheduler.tick(now=at(86401)).status == "completed"
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_generations")) == 0


def test_scheduled_tick_retries_exhausts_and_resumes_without_ttl_renewal(scoped, monkeypatch):
    worker, _, _, _ = scoped
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    scheduler = IngestionMaintenance(worker, max_attempts=3)
    clear_cache(worker)
    with monkeypatch.context() as patch:
        patch.setattr(worker, "recover", lambda **kwargs: False)
        assert scheduler.tick(now=at(1)).status == "retry"
        assert scheduler.tick(now=at(1)).status == "idle"
        assert scheduler.tick(now=at(2)).status == "retry"
        assert scheduler.tick(now=at(4)).status == "exhausted"
        assert scheduler.tick(now=at(63)).status == "idle"
    assert scheduler.tick(now=at(64)).status == "completed"
    assert snap(worker, 64).received_at == NOW
    assert snap(worker, 91).tracking.service == "unknown"
    assert scheduler.tick(now=at(86400)).evidence == 1
    with pytest.raises(ValueError, match="regression"):
        scheduler.tick(now=NOW)


def test_scheduled_faults_are_sanitized_and_stoppable(scoped, monkeypatch):
    worker, _, _, _ = scoped
    scheduler = IngestionMaintenance(worker, max_attempts=1)

    def fail(**kwargs):
        raise RuntimeError("private connection and location")

    monkeypatch.setattr(worker, "retain", fail)
    result = scheduler.tick(now=NOW)
    assert result.status == "exhausted" and "private" not in repr(result)
    assert result.data_mode == "simulation"
    stop = Event()
    stop.set()
    scheduler.run(stop, max_ticks=2, clock=lambda: at(60))
    assert scheduler.last_tick == NOW


def test_same_and_multiple_scheduler_instances_serialize(scoped):
    worker, _, _, _ = scoped
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    scheduler = IngestionMaintenance(worker)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: scheduler.tick(now=at(86400)), range(4)))
    assert sorted(r.status for r in results) == ["completed", "idle", "idle", "idle"]
    assert sum(r.evidence for r in results) == 1
    others = [IngestionMaintenance(worker) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda s: s.tick(now=at(86401)), others))
    assert all(r.status == "completed" for r in results)
    assert snap(worker, 86401).tracking.service == "unknown"


def test_scope_migration_roundtrip_and_failed_ddl_rollback(postgres):
    engine, config = postgres
    command.downgrade(config, "0003_realtime_durable")

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("CREATE VIEW nammamove.ingestion_worker_scope"):
            raise RuntimeError("injected scope migration failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            with pytest.raises(RuntimeError, match="scope migration"):
                command.upgrade(config, "head")
    finally:
        event.remove(engine, "before_cursor_execute", fail)
        config.attributes.pop("connection", None)
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM nammamove.alembic_version"))
            == "0003_realtime_durable"
        )
        assert connection.scalar(text("SELECT to_regclass('nammamove.ingestion_workers')")) is None
    command.upgrade(config, "head")
