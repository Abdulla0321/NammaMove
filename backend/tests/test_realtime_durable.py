"""Genuine PostgreSQL/PostGIS + Redis durability acceptance; no SQLite substitute."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from app.realtime.durable import DurableIngestion
from app.realtime.ingestion import FullDatasetWorker
from app.realtime.models import IngestionGeneration, IngestionSource
from app.realtime.redis_state import _digest
from app.transit.ingestion import ingest
from app.transit.models import GtfsTrip, TransitDataset
from redis.exceptions import ConnectionError
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_realtime_ingestion import DAY, NOW, at, feed, store, wire
from test_realtime_redis import redis_state
from test_transit import archive, manifest, tables

__all__ = ["redis_state"]
pytestmark = [pytest.mark.postgres, pytest.mark.redis]


def static_values():
    values = tables()
    values["trips.txt"] = (
        "route_id,service_id,trip_id,direction_id,shape_id\nR,C,A-D,0,H\nR,C,B-D,0,H\n"
    )
    values["stop_times.txt"] = (
        values["stop_times.txt"].replace("T,", "A-D,")
        + "B-D,26:00:00,26:00:00,S1,1\nB-D,26:10:00,26:10:00,S2,2\n"
    )
    return values


@pytest.fixture
def durable(postgres, redis_state):
    engine, config = postgres
    values = static_values()
    with Session(engine) as db, db.begin():
        dataset_id = ingest(db, archive(values), manifest()).id
    cache = store(redis_state)
    worker = DurableIngestion(engine, cache, dataset_id)
    worker.register()
    return worker, engine, config


def snap(worker, seconds=0):
    return worker.snapshot("A-D", DAY, now=at(seconds))


def clear_cache(worker):
    keys = list(worker.cache.client.scan_iter(match=worker.cache.prefix + "*"))
    if keys:
        worker.cache.client.delete(*keys)


def count(engine):
    with Session(engine) as db:
        return db.scalar(select(func.count()).select_from(IngestionGeneration))


def test_accept_duplicate_and_worker_reconstruction(durable):
    worker, engine, _ = durable
    payload = wire(feed())
    assert worker.ingest(payload, now=NOW) == "accepted"
    assert worker.ingest(payload, now=at(1)) == "duplicate"
    assert count(engine) == 1
    clear_cache(worker)
    restarted = DurableIngestion(engine, worker.cache, worker.dataset_id)
    assert restarted.recover(now=at(2))
    value = snap(restarted, 2)
    assert value.tracking.service == "delayed" and value.data_mode == "simulation"
    assert value.tracking.vehicle.received_at == NOW
    assert restarted.ingest(payload, now=at(2)) == "duplicate"


@pytest.mark.parametrize("channels", [(0,), (2,), ()])
def test_omission_and_restart_never_invent_cancellation(durable, channels):
    worker, _, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    assert worker.ingest(wire(feed(1, channels=channels)), now=at(1)) == "accepted"
    clear_cache(worker)
    assert snap(worker, 2).tracking.service == "unknown"


def test_rejected_metadata_idempotency_and_no_raw_feed(durable):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    assert worker.ingest(b"private raw synthetic invalid feed", now=at(1)) == "rejected"
    assert worker.ingest(b"private raw synthetic invalid feed", now=at(2)) == "rejected"
    assert count(engine) == 2
    with Session(engine) as db:
        rows = db.scalars(select(IngestionGeneration)).all()
        assert sorted(row.outcome for row in rows) == ["accepted", "rejected"]
        assert all("private" not in row.fingerprint for row in rows)
        rejected = next(r for r in rows if r.outcome == "rejected")
        assert rejected.received_at == at(1)
    assert snap(worker, 2).tracking.service == "delayed"


def test_durable_watermark_rejects_older_and_conflicting_generations(durable):
    worker, _, _ = durable
    assert worker.ingest(wire(feed(2, channels=())), now=at(2)) == "accepted"
    clear_cache(worker)
    assert worker.ingest(wire(feed()), now=at(3)) == "out_of_order"
    assert worker.ingest(wire(feed(2)), now=at(3)) == "conflict"
    assert snap(worker, 3).tracking.service == "unknown"


def test_fresh_independent_cancellation_expires_after_recovery(durable):
    worker, _, _ = durable
    data = feed(channels=(1,))
    update = data["entity"][0]["trip_update"]
    update["trip"]["schedule_relationship"] = "CANCELED"
    del update["delay"]
    assert worker.ingest(wire(data), now=NOW) == "accepted"
    clear_cache(worker)
    assert snap(worker, 90).tracking.service == "cancelled"
    assert snap(worker, 91).tracking.service == "unknown"
    assert snap(worker, 900).tracking.trip_update.freshness == "unavailable"


def test_recovery_preserves_alert_interval_and_observation_deadlines(durable):
    worker, _, _ = durable
    data = feed()
    data["entity"][2]["alert"]["active_period"] = [{"end": str(int(at(3).timestamp()))}]
    assert worker.ingest(wire(data), now=NOW) == "accepted"
    clear_cache(worker)
    assert snap(worker, 2).tracking.alert.freshness == "fresh"
    assert snap(worker, 3).tracking.alert.freshness == "unavailable"
    value = snap(worker, 91)
    assert value.tracking.vehicle.freshness == "stale" and value.tracking.service == "unknown"
    keys = list(worker.cache.client.scan_iter(match=worker.cache.prefix + "payload:*"))
    assert all(worker.cache.client.pttl(key) <= 809000 for key in keys)


def test_concurrent_generations_serialize_and_duplicate_once(durable):
    worker, engine, _ = durable
    barrier = Barrier(4)

    def write(_):
        barrier.wait(timeout=5)
        return DurableIngestion(engine, worker.cache, worker.dataset_id).ingest(
            wire(feed()), now=NOW
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(write, range(4)))
    assert outcomes.count("accepted") == 1 and outcomes.count("duplicate") == 3
    assert count(engine) == 1


def test_sql_failure_after_redis_write_never_exposes_uncommitted_generation(durable):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO nammamove.ingestion_generations"):
            raise ValueError("injected SQL failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        assert worker.ingest(wire(feed(1, channels=())), now=at(1)) == "unavailable"
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    # Redis was provisional; the public durability gate restores the SQL commit.
    assert snap(worker, 2).tracking.service == "delayed"
    assert count(engine) == 1
    assert worker.ingest(wire(feed(1, channels=())), now=at(2)) == "accepted"


def test_redis_outage_and_queue_retry_do_not_claim_durable_acceptance(durable, monkeypatch):
    worker, engine, _ = durable
    queue = FullDatasetWorker(worker)
    queue.submit(wire(feed()), now=NOW)

    def down(*args, **kwargs):
        raise ConnectionError("private connection details")

    with monkeypatch.context() as patch:
        patch.setattr(worker.cache.client, "pipeline", down)
        result = queue.run_one(now=NOW)
        assert result.outcome == "unavailable" and result.retry_scheduled
        assert snap(worker).tracking.service == "unknown"
    assert count(engine) == 0
    assert queue.run_one(now=at(1)).outcome == "accepted"
    assert count(engine) == 1


@pytest.mark.parametrize("corruption", ["checkpoint", "digest", "watermark", "dataset", "trip"])
def test_corrupt_or_mismatched_durable_records_fail_closed(durable, corruption):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    with Session(engine) as db, db.begin():
        source = db.get(IngestionSource, worker.adapter.source_id)
        if corruption == "checkpoint":
            source.checkpoint = source.checkpoint.replace('"simulation"', '"live"')
        elif corruption == "digest":
            source.checkpoint_digest = "0" * 64
        elif corruption == "watermark":
            source.fingerprint = "0" * 64
        elif corruption == "dataset":
            db.get(TransitDataset, worker.dataset_id).checksum = "0" * 64
        else:
            trip = db.scalar(
                select(GtfsTrip).where(
                    GtfsTrip.dataset_id == worker.dataset_id, GtfsTrip.external_id == "A-D"
                )
            )
            trip.direction_id = 1
    assert not worker.recover(now=at(1))
    assert snap(worker, 1).tracking.storage_status == "unavailable"
    assert snap(worker, 1).tracking.service == "unknown"
    assert worker.ingest(wire(feed(1)), now=at(1)) == "unavailable"


def test_content_corruption_with_recomputed_outer_digest_is_still_rejected(durable):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    with Session(engine) as db, db.begin():
        source = db.get(IngestionSource, worker.adapter.source_id)
        checkpoint = json.loads(source.checkpoint)
        key = next(iter(checkpoint["payloads"]))
        payload = json.loads(checkpoint["payloads"][key])
        payload["event"]["event_id"] = "tampered"
        checkpoint["payloads"][key] = json.dumps(payload)
        source.checkpoint = json.dumps(checkpoint)
        source.checkpoint_digest = _digest(source.checkpoint)
    assert not worker.recover(now=at(1))


def test_omitted_order_guard_corruption_cannot_authorize_jump_after_restart(durable):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    assert worker.ingest(wire(feed(1, channels=())), now=at(1)) == "accepted"
    with Session(engine) as db, db.begin():
        source = db.get(IngestionSource, worker.adapter.source_id)
        checkpoint = json.loads(source.checkpoint)
        manifest = json.loads(checkpoint["manifest"])
        manifest["guards"] = {}
        checkpoint["manifest"] = json.dumps(manifest)
        source.checkpoint = json.dumps(checkpoint)
        source.checkpoint_digest = _digest(source.checkpoint)
    clear_cache(worker)
    assert not worker.recover(now=at(2))
    jump = feed(2, channels=(0,))
    jump["entity"][0]["vehicle"]["position"]["latitude"] = 20
    assert worker.ingest(wire(jump), now=at(2)) == "unavailable"
    assert snap(worker, 2).tracking.observed_position is None


def test_sql_constraint_rejects_null_watermark_receipt(durable):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE nammamove.ingestion_sources SET received_at=NULL"))
    assert snap(worker, 1).tracking.service == "delayed"


def test_retention_removes_payloads_evidence_but_keeps_watermark(durable):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    assert worker.retain(now=at(86400)) == {"evidence": 1, "payloads": 3}
    assert count(engine) == 1
    worker.retain(now=at(86400), apply=True)
    assert count(engine) == 0
    with Session(engine) as db:
        source = db.get(IngestionSource, worker.adapter.source_id)
        assert source.header_at == NOW
        assert json.loads(source.checkpoint)["payloads"] == {}
    clear_cache(worker)
    assert snap(worker, 86400).tracking.service == "unknown"
    assert worker.ingest(wire(feed()), now=at(86400)) == "rejected"


def test_source_binding_cannot_be_reassigned_or_impersonated(durable):
    worker, engine, _ = durable
    other = DurableIngestion(engine, worker.cache, uuid4())
    assert other.ingest(wire(feed()), now=NOW) == "unavailable"
    assert not other.recover(now=NOW)
    with pytest.raises(ValueError):
        worker.register(max_generations=1)
    assert count(engine) == 0


@pytest.mark.parametrize("corruption", ["missing", "fingerprint", "expiry"])
def test_acceptance_evidence_is_checked_before_restart_recovery(durable, corruption):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    with Session(engine) as db, db.begin():
        evidence = db.scalar(select(IngestionGeneration))
        if corruption == "missing":
            db.delete(evidence)
        elif corruption == "fingerprint":
            evidence.fingerprint = "0" * 64
        else:
            evidence.expires_at += timedelta(seconds=1)
    clear_cache(worker)
    assert not worker.recover(now=at(1))
    assert snap(worker, 1).tracking.service == "unknown"
    assert worker.ingest(wire(feed(1)), now=at(1)) == "unavailable"


def test_bounded_evidence_capacity_and_explicit_retention(durable):
    worker, engine, _ = durable
    # Owner chooses a small policy before any evidence exists.
    with Session(engine) as db, db.begin():
        source = db.get(IngestionSource, worker.adapter.source_id)
        source.max_generations = 1
        source.evidence_seconds = 900
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    assert worker.ingest(wire(feed(1, channels=())), now=at(1)) == "capacity"
    assert snap(worker, 2).tracking.service == "delayed"
    assert count(engine) == 1
    assert worker.retain(now=at(900), apply=True)["evidence"] == 1
    assert worker.ingest(wire(feed(901, channels=())), now=at(901)) == "accepted"
    assert count(engine) == 1 and snap(worker, 901).tracking.service == "unknown"


def test_database_failure_gates_cached_reads_and_ingestion(durable, monkeypatch):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    from sqlalchemy.exc import OperationalError

    def down(*args, **kwargs):
        raise OperationalError("redacted", {}, Exception("private"))

    with monkeypatch.context() as patch:
        patch.setattr(engine, "connect", down)
        assert not worker.recover(now=at(1))
        result = snap(worker, 1)
        assert result.tracking.storage_status == "unavailable"
        assert result.tracking.service == "unknown" and result.tracking.observed_position is None
        assert worker.ingest(wire(feed(1)), now=at(1)) == "unavailable"
    assert snap(worker, 2).tracking.service == "delayed"


@pytest.mark.parametrize("field,value", [("route_id", "wrong-static-route"), ("direction_id", 1)])
def test_static_route_direction_mismatch_rejects_without_replacing_checkpoint(
    durable, field, value
):
    worker, _, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    data = feed(1)
    data["entity"][0]["vehicle"]["trip"][field] = value
    assert worker.ingest(wire(data), now=at(1)) == "rejected"
    assert snap(worker, 2).header_at == NOW


def test_lost_sql_commit_response_retries_as_durable_duplicate(durable, monkeypatch):
    from sqlalchemy.exc import OperationalError

    worker, engine, _ = durable
    queue = FullDatasetWorker(worker)
    queue.submit(wire(feed()), now=NOW)
    commit = engine.dialect.do_commit
    lost = []

    def committed_but_response_lost(connection):
        commit(connection)
        if not lost:
            lost.append(True)
            raise OperationalError("redacted", {}, Exception("response lost"))

    with monkeypatch.context() as patch:
        patch.setattr(engine.dialect, "do_commit", committed_but_response_lost)
        assert queue.run_one(now=NOW).outcome == "unavailable"
    assert count(engine) == 1
    assert queue.run_one(now=at(1)).outcome == "duplicate"
    assert snap(worker, 1).received_at == NOW


def test_concurrent_new_and_old_snapshots_cannot_rollback_watermark(durable):
    worker, engine, _ = durable
    barrier = Barrier(2)

    def write(seconds):
        barrier.wait(timeout=5)
        return worker.ingest(wire(feed(seconds, channels=() if seconds == 2 else (1,))), now=at(2))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, [1, 2]))
    assert set(results) <= {"accepted", "out_of_order"}
    clear_cache(worker)
    assert snap(worker, 2).header_at == at(2)
    assert snap(worker, 2).tracking.service == "unknown"


def test_rls_blocks_spoofed_app_identity_even_after_accidental_grants(durable):
    worker, engine, _ = durable
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    role = "nm_durable_rls_" + uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
            connection.execute(text(f"GRANT USAGE ON SCHEMA nammamove TO {role}"))
            connection.execute(
                text(
                    f"GRANT SELECT,INSERT,UPDATE,DELETE ON nammamove.ingestion_sources,nammamove.ingestion_generations TO {role}"
                )
            )
            connection.execute(text(f"SET LOCAL ROLE {role}"))
            connection.execute(
                text(
                    "SELECT set_config('nammamove.user_id',:uid,true), set_config('nammamove.role','admin',true)"
                ),
                {"uid": str(uuid4())},
            )
            assert connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_sources")) == 0
            assert (
                connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_generations")) == 0
            )
            assert connection.execute(text("DELETE FROM nammamove.ingestion_sources")).rowcount == 0
        finally:
            transaction.rollback()


def test_phase05d_failed_ddl_rolls_back_without_touching_prior_schema(postgres):
    engine, config = postgres
    command.downgrade(config, "0002_transit_data")

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("CREATE INDEX ix_ingestion_generations_expires_at"):
            raise RuntimeError("injected durability migration failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            with pytest.raises(RuntimeError, match="durability migration"):
                command.upgrade(config, "head")
    finally:
        event.remove(engine, "before_cursor_execute", fail)
        config.attributes.pop("connection", None)
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM nammamove.alembic_version"))
            == "0002_transit_data"
        )
        assert connection.scalar(text("SELECT to_regclass('nammamove.ingestion_sources')")) is None
        assert connection.scalar(text("SELECT to_regclass('nammamove.gtfs_stops')")) is not None
    command.upgrade(config, "head")


def test_runtime_grants_and_rls_deny_all_durable_data(postgres):
    engine, config = postgres
    role = "nm_durable_" + uuid4().hex
    script = Path("backend/sql/runtime_role.sql").read_text()
    script = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("--"))
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for statement in script.replace("nammamove_api", role).split(";"):
                if statement.strip():
                    connection.execute(text(statement))
            connection.execute(text(f"SET LOCAL ROLE {role}"))
            for table in (
                "ingestion_sources",
                "ingestion_generations",
                "ingestion_workers",
                "ingestion_dispatch",
            ):
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    assert not connection.scalar(
                        text("SELECT has_table_privilege(current_user,:table,:privilege)"),
                        {"table": "nammamove." + table, "privilege": privilege},
                    )
                with pytest.raises(DBAPIError), connection.begin_nested():
                    connection.execute(text(f"SELECT * FROM nammamove.{table}"))
        finally:
            transaction.rollback()
    command.downgrade(config, "0002_transit_data")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass('nammamove.ingestion_sources')")) is None
        assert (
            connection.scalar(text("SELECT to_regclass('nammamove.transit_datasets')")) is not None
        )
    command.upgrade(config, "head")
