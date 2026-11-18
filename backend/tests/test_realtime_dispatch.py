"""Genuine PostGIS/Redis dispatch, crash and source-isolation acceptance."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from alembic import command
from app.realtime.dispatch import DurableDispatch
from app.realtime.models import IngestionDispatch, IngestionSource
from redis.exceptions import ConnectionError
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session
from test_realtime_durable import clear_cache, durable, snap
from test_realtime_ingestion import NOW, at, feed, wire
from test_realtime_redis import redis_state
from test_realtime_worker import scoped

__all__ = ["durable", "redis_state", "scoped"]
pytestmark = [pytest.mark.postgres, pytest.mark.redis]


@pytest.fixture
def dispatch(scoped):
    worker, owner, engine, role = scoped
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    queue = DurableDispatch(worker)
    return queue, worker, engine, role


def rows(engine):
    with Session(engine) as db:
        return db.scalars(select(IngestionDispatch)).all()


def test_committed_generation_dispatch_and_duplicate_ack(dispatch):
    queue, worker, engine, _ = dispatch
    assert queue.enqueue(now=NOW).status == "queued"
    assert queue.enqueue(now=at(1)).status == "duplicate"
    clear_cache(worker)
    claim = queue.claim(now=at(2))
    assert claim.status == "claimed" and claim.lease.data_mode == "simulation"
    assert queue.process(claim.lease, now=at(2)).status == "completed"
    assert queue.process(claim.lease, now=at(3)).status == "duplicate"
    assert queue.enqueue(now=at(3)).status == "duplicate"
    assert queue.run_one(now=at(3)).status == "idle"
    assert len(rows(engine)) == 1
    assert snap(worker, 3).received_at == NOW
    assert snap(worker, 3).data_mode == "simulation"


def test_acceptance_to_enqueue_crash_gap_reconciles_latest_watermark(dispatch):
    _, worker, engine, _ = dispatch
    # Producer died after the durable ingestion commit, before enqueue.
    restarted = DurableDispatch(worker)
    clear_cache(worker)
    assert restarted.enqueue(now=at(2)).status == "queued"
    assert restarted.run_one(now=at(2)).status == "completed"
    assert rows(engine)[0].received_at == NOW
    assert snap(worker, 2).received_at == NOW


def test_completed_ack_validates_current_reference_and_checkpoint(dispatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    lease = queue.claim(now=NOW).lease
    assert queue.process(lease, now=at(1)).status == "completed"
    with Session(engine) as db, db.begin():
        db.scalar(select(IngestionDispatch)).guards_digest = "0" * 64
    assert queue.process(lease, now=at(2)).status == "invalid"
    assert queue.enqueue(now=at(2)).status == "unavailable"


def test_unaccepted_or_expired_sources_cannot_enqueue(scoped):
    worker, _, _, _ = scoped
    queue = DurableDispatch(worker)
    assert queue.enqueue(now=NOW).status == "empty"
    assert worker.ingest(b"invalid synthetic", now=NOW) == "rejected"
    assert queue.enqueue(now=NOW).status == "empty"
    assert worker.ingest(wire(feed()), now=NOW) == "accepted"
    assert queue.enqueue(now=at(86400)).status == "expired"


def test_capacity_includes_leases_and_terminal_rows_and_owner_policy(dispatch):
    queue, worker, engine, _ = dispatch
    with engine.begin() as connection:
        connection.execute(text("UPDATE nammamove.ingestion_sources SET dispatch_capacity=1"))
    assert queue.enqueue(now=NOW).status == "queued"
    assert queue.run_one(now=NOW).status == "completed"
    assert worker.ingest(wire(feed(1, channels=())), now=at(1)) == "accepted"
    assert queue.enqueue(now=at(1)).status == "backpressure"
    assert len(rows(engine)) == 1
    assert queue.retain(now=at(86400)) == 1
    assert queue.enqueue(now=at(86400)).status == "queued"
    assert len(rows(engine)) == 1


def test_concurrent_enqueue_and_claim_are_single_winner(dispatch):
    queue, worker, engine, _ = dispatch
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: DurableDispatch(worker).enqueue(now=NOW).status, range(4))
        )
    assert results.count("queued") == 1 and results.count("duplicate") == 3
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims = list(pool.map(lambda _: DurableDispatch(worker).claim(now=at(1)), range(4)))
    leases = [r.lease for r in claims if r.lease is not None]
    assert len(leases) == 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: queue.process(leases[0], now=at(2)).status, range(4)))
    assert outcomes.count("completed") == 1 and outcomes.count("duplicate") == 3
    assert rows(engine)[0].attempts == 1


def test_process_death_reclaims_lease_and_fences_old_ack(dispatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    abandoned = queue.claim(now=NOW).lease
    restarted = DurableDispatch(worker)
    assert restarted.claim(now=at(9)).status == "idle"
    replacement = restarted.claim(now=at(10)).lease
    assert replacement.token != abandoned.token and replacement.attempt == 2
    clear_cache(worker)
    assert queue.process(abandoned, now=at(10)).status == "stale"
    assert restarted.process(replacement, now=at(10)).status == "completed"
    assert rows(engine)[0].attempts == 2
    assert snap(worker, 10).received_at == NOW


def test_actual_child_exit_after_committed_claim_is_recoverable(dispatch, redis_state):
    queue, worker, engine, role = dispatch
    queue.enqueue(now=NOW)
    script = """
import os
from datetime import date, datetime
from uuid import UUID
from sqlalchemy import create_engine, event
from app.realtime.dispatch import DurableDispatch
from app.realtime.durable import DurableIngestion
from app.realtime.gtfs_rt import FixtureGtfsRtAdapter
from app.realtime.ingestion import RedisFullDataset
from app.realtime.redis_state import RedisTrackingState, tracking_client
engine = create_engine(os.environ['NAMMAMOVE_TEST_DATABASE_URL'], hide_parameters=True)
@event.listens_for(engine, 'checkout')
def identity(connection, record, proxy):
    with connection.cursor() as cursor:
        cursor.execute('SET ROLE ' + os.environ['NM_CRASH_ROLE'])
    connection.commit()
day = date.fromisoformat(os.environ['NM_CRASH_DAY'])
trips = frozenset({('A-D', day), ('B-D', day)})
client = tracking_client(os.environ['NAMMAMOVE_TEST_REDIS_URL'])
state = RedisTrackingState(client, namespace=os.environ['NM_CRASH_NAMESPACE'], source_id='fixture', fixture_trips=trips)
store = DurableIngestion(engine, RedisFullDataset(FixtureGtfsRtAdapter('fixture', trips), state), UUID(os.environ['NM_CRASH_DATASET']))
assert DurableDispatch(store).claim(now=datetime.fromisoformat(os.environ['NM_CRASH_NOW'])).status == 'claimed'
os._exit(23)
"""
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": "backend",
            "NM_CRASH_ROLE": role,
            "NM_CRASH_DAY": NOW.date().isoformat(),
            "NM_CRASH_NOW": NOW.isoformat(),
            "NM_CRASH_NAMESPACE": redis_state[2],
            "NM_CRASH_DATASET": str(worker.dataset_id),
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, timeout=30
    )
    # Do not echo a child's environment/exception output into assertion reports.
    assert result.returncode == 23
    assert rows(engine)[0].state == "leased"
    assert DurableDispatch(worker).run_one(now=at(10)).status == "completed"
    assert rows(engine)[0].attempts == 2


def test_repeated_crashes_exhaust_persisted_attempt_budget(dispatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    for seconds in (0, 10, 20):
        assert DurableDispatch(worker).claim(now=at(seconds)).status == "claimed"
    assert DurableDispatch(worker).claim(now=at(30)).status == "exhausted"
    assert queue.claim(now=at(40)).status == "idle"
    assert rows(engine)[0].attempts == 3


def test_redis_outage_bounded_retry_and_original_ttl(dispatch, monkeypatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    clear_cache(worker)

    def down(*args, **kwargs):
        raise ConnectionError("private connection")

    with monkeypatch.context() as patch:
        patch.setattr(worker.cache.client, "pipeline", down)
        assert queue.run_one(now=at(1)).status == "retry"
        assert queue.run_one(now=at(1)).status == "idle"
        assert queue.run_one(now=at(2)).status == "retry"
        assert queue.run_one(now=at(4)).status == "exhausted"
    assert rows(engine)[0].attempts == 3
    assert snap(worker, 91).tracking.service == "unknown"
    assert snap(worker, 900).tracking.vehicle.freshness == "unavailable"


def test_redis_recovery_retry_is_idempotent_and_not_freshened(dispatch, monkeypatch):
    queue, worker, _, _ = dispatch
    queue.enqueue(now=NOW)

    def down(*args, **kwargs):
        raise ConnectionError("private connection")

    with monkeypatch.context() as patch:
        patch.setattr(worker.cache.client, "pipeline", down)
        assert queue.run_one(now=at(90)).status == "retry"
    assert DurableDispatch(worker).run_one(now=at(91)).status == "completed"
    assert snap(worker, 91).tracking.service == "unknown"
    assert snap(worker, 91).received_at == NOW


def test_new_watermark_supersedes_old_job_without_projection(dispatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    old = queue.claim(now=NOW).lease
    assert worker.ingest(wire(feed(1, channels=())), now=at(1)) == "accepted"
    assert queue.enqueue(now=at(1)).status == "queued"
    clear_cache(worker)
    assert queue.process(old, now=at(2)).status == "superseded"
    assert worker.cache.client.get(worker.cache.key) is None
    assert queue.run_one(now=at(2)).status == "completed"
    assert snap(worker, 2).tracking.service == "unknown"
    assert snap(worker, 2).header_at == at(1)
    assert sorted(r.state for r in rows(engine)) == ["completed", "superseded"]


@pytest.mark.parametrize("column", ["binding_digest", "guards_digest", "received_at", "identity"])
def test_corrupt_job_never_projects(dispatch, column):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    with Session(engine) as db, db.begin():
        job = db.scalar(select(IngestionDispatch))
        setattr(job, column, at(1) if column == "received_at" else "0" * 64)
    clear_cache(worker)
    assert queue.run_one(now=at(2)).status in {"invalid", "superseded"}
    assert worker.cache.client.get(worker.cache.key) is None


@pytest.mark.parametrize("column", ["checkpoint_digest", "binding_digest", "guards_digest"])
def test_corrupt_source_fails_closed(dispatch, column):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    with Session(engine) as db, db.begin():
        source = db.get(IngestionSource, worker.adapter.source_id)
        setattr(source, column, "0" * 64)
    clear_cache(worker)
    assert queue.run_one(now=at(1)).status == "unavailable"
    assert worker.cache.client.get(worker.cache.key) is None
    assert queue.enqueue(now=at(1)).status == "unavailable"


def test_expired_job_cannot_resurrect_observations(dispatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    clear_cache(worker)
    assert queue.claim(now=at(86400)).status == "expired"
    assert rows(engine)[0].state == "expired"
    assert worker.cache.client.get(worker.cache.key) is None


def test_wrong_source_token_and_simulated_lease_denied(dispatch):
    queue, _, _, _ = dispatch
    queue.enqueue(now=NOW)
    lease = queue.claim(now=NOW).lease
    assert queue.process(replace(lease, source_id="unauthorized"), now=at(1)).status == "stale"
    assert queue.process(replace(lease, token=uuid4()), now=at(1)).status == "stale"
    assert queue.process(replace(lease, attempt=5), now=at(1)).status == "stale"
    assert queue.process(lease, now=at(1)).status == "completed"


def test_processing_clock_cannot_regress_before_claim(dispatch):
    queue, _, _, _ = dispatch
    queue.enqueue(now=NOW)
    lease = queue.claim(now=at(2)).lease
    assert queue.process(lease, now=at(1)).status == "stale"
    assert queue.process(lease, now=at(2)).status == "completed"


def test_projection_then_sql_ack_failure_is_reclaimable(dispatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    lease = queue.claim(now=NOW).lease

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE nammamove.ingestion_dispatch"):
            raise OperationalError("redacted", {}, Exception("private"))

    event.listen(worker.engine, "before_cursor_execute", fail)
    try:
        assert queue.process(lease, now=at(1)).status == "unavailable"
    finally:
        event.remove(worker.engine, "before_cursor_execute", fail)
    assert rows(engine)[0].state == "leased"
    assert DurableDispatch(worker).run_one(now=at(10)).status == "completed"
    assert snap(worker, 10).received_at == NOW


@pytest.mark.parametrize("operation", ["enqueue", "claim", "ack"])
def test_lost_sql_commit_response_is_retry_safe(dispatch, monkeypatch, operation):
    queue, worker, engine, _ = dispatch
    if operation != "enqueue":
        queue.enqueue(now=NOW)
    lease = queue.claim(now=NOW).lease if operation == "ack" else None
    commit = worker.engine.dialect.do_commit
    lost = []

    def ambiguous(connection):
        commit(connection)
        if not lost:
            lost.append(True)
            raise OperationalError("redacted", {}, Exception("private"))

    with monkeypatch.context() as patch:
        patch.setattr(worker.engine.dialect, "do_commit", ambiguous)
        result = (
            queue.process(lease, now=at(1))
            if operation == "ack"
            else getattr(queue, operation)(now=NOW)
        )
        assert result.status == "unavailable"
    assert len(rows(engine)) == 1
    if operation == "enqueue":
        assert queue.enqueue(now=at(1)).status == "duplicate"
    elif operation == "claim":
        assert queue.claim(now=at(1)).status == "idle"
        assert queue.run_one(now=at(10)).status == "completed"
    else:
        assert queue.process(lease, now=at(2)).status == "duplicate"


def test_database_outage_does_not_ack_or_project(dispatch, monkeypatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    lease = queue.claim(now=NOW).lease
    clear_cache(worker)

    def down(*args, **kwargs):
        raise OperationalError("redacted", {}, Exception("private"))

    with monkeypatch.context() as patch:
        patch.setattr(worker.engine, "connect", down)
        assert queue.enqueue(now=at(1)).status == "unavailable"
        assert queue.claim(now=at(1)).status == "unavailable"
        assert queue.process(lease, now=at(1)).status == "unavailable"
    assert rows(engine)[0].state == "leased"
    assert worker.cache.client.get(worker.cache.key) is None
    assert queue.run_one(now=at(10)).status == "completed"


def test_dispatch_permission_and_spoofed_guc_source_denial(dispatch):
    queue, worker, engine, role = dispatch
    queue.enqueue(now=NOW)
    with Session(engine) as db, db.begin():
        source = db.get(IngestionSource, worker.adapter.source_id)
        db.add(
            IngestionSource(
                id="other",
                dataset_id=source.dataset_id,
                binding_digest=source.binding_digest,
                evidence_seconds=900,
                max_generations=10,
            )
        )
        db.flush()
        db.add(
            IngestionDispatch(
                source_id="other",
                identity="a" * 64,
                header_at=NOW,
                received_at=NOW,
                expires_at=at(900),
                binding_digest=source.binding_digest,
                guards_digest="b" * 64,
                due_at=NOW,
            )
        )
    with engine.begin() as connection:
        connection.execute(
            text(f"GRANT SELECT,UPDATE,DELETE ON nammamove.ingestion_dispatch TO {role}")
        )
    with worker.engine.begin() as connection:
        connection.execute(
            text(
                "SELECT set_config('nammamove.user_id','spoof',true),set_config('nammamove.role','admin',true),set_config('nammamove.source_id','other',true)"
            )
        )
        assert connection.scalar(text("SELECT count(*) FROM nammamove.ingestion_dispatch")) == 1
        assert (
            connection.execute(
                text(
                    "UPDATE nammamove.ingestion_dispatch SET state='invalid' WHERE source_id='other'"
                )
            ).rowcount
            == 0
        )
        assert (
            connection.execute(
                text("DELETE FROM nammamove.ingestion_dispatch WHERE source_id='other'")
            ).rowcount
            == 0
        )
    # Remove accidental broad UPDATE before testing column-limited provisioning.
    with engine.begin() as connection:
        connection.execute(
            text(f"REVOKE SELECT,UPDATE,DELETE ON nammamove.ingestion_dispatch FROM {role}")
        )
    with worker.engine.begin() as connection:
        for sql in (
            "UPDATE nammamove.ingestion_sources SET dispatch_capacity=32",
            "UPDATE nammamove.ingestion_dispatch SET binding_digest=repeat('0',64)",
        ):
            with pytest.raises(DBAPIError), connection.begin_nested():
                connection.execute(text(sql))
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO nammamove.ingestion_dispatch SELECT 'other',repeat('c',64),header_at,received_at,expires_at,binding_digest,guards_digest,data_mode,state,attempts,due_at,token,lease_until FROM nammamove.ingestion_dispatch LIMIT 1"
                )
            )


def test_future_expiry_dispatch_rows_cannot_be_deleted(dispatch):
    queue, worker, engine, _ = dispatch
    queue.enqueue(now=NOW)
    future = datetime.now(UTC) + timedelta(days=1)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE nammamove.ingestion_dispatch SET header_at=:now,received_at=:now,expires_at=:future"
            ),
            {"now": datetime.now(UTC), "future": future},
        )
    with worker.engine.begin() as connection:
        assert connection.execute(text("DELETE FROM nammamove.ingestion_dispatch")).rowcount == 0
    assert queue.retain(now=at(2000000)) == 0


def test_dispatch_failed_ddl_rolls_back_and_preserves_0004(postgres):
    engine, config = postgres
    command.downgrade(config, "0004_ingestion_scope")

    def fail(connection, cursor, statement, parameters, context, executemany):
        if "CREATE TABLE nammamove.ingestion_dispatch" in statement:
            raise RuntimeError("injected dispatch migration failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            with pytest.raises(RuntimeError, match="dispatch migration"):
                command.upgrade(config, "head")
    finally:
        event.remove(engine, "before_cursor_execute", fail)
        config.attributes.pop("connection", None)
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM nammamove.alembic_version"))
            == "0004_ingestion_scope"
        )
        assert connection.scalar(text("SELECT to_regclass('nammamove.ingestion_dispatch')")) is None
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_schema='nammamove' AND table_name='ingestion_sources' AND column_name LIKE 'dispatch_%'"
                )
            )
            == 0
        )
    command.upgrade(config, "head")
