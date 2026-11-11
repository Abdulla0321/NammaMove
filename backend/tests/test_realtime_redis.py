"""Real Redis transactions/TTLs; no fake server is accepted as integration evidence."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from app.realtime.redis_state import RedisTrackingState, tracking_client
from app.realtime.replay import Position, ReplayEvent
from redis import Redis
from redis.client import Pipeline
from redis.exceptions import ConnectionError, WatchError

NOW = datetime(2026, 11, 4, 8, tzinfo=timezone.utc)
DAY = date(2026, 11, 4)


def event(identity="1", seconds=0, kind="vehicle", **fields):
    return ReplayEvent(
        source_id="fixture",
        event_id=identity,
        trip_id="A-D",
        service_date=DAY,
        kind=kind,
        observed_at=NOW + timedelta(seconds=seconds),
        **fields,
    )


def worker(client, namespace, **options):
    return RedisTrackingState(
        client,
        namespace=namespace,
        source_id="fixture",
        fixture_trips=frozenset({("A-D", DAY), ("B-D", DAY)}),
        **options,
    )


@pytest.fixture
def redis_state():
    url = os.environ.get("NAMMAMOVE_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set NAMMAMOVE_TEST_REDIS_URL to a dedicated disposable Redis")
    from urllib.parse import urlsplit

    assert urlsplit(url).hostname in {"127.0.0.1", "localhost"}
    client = tracking_client(url)
    assert client.ping()
    namespace = "nammamove:simulation:test_" + uuid4().hex
    state = worker(client, namespace)
    yield client, state, namespace
    # Only this test's namespace, never FLUSHDB/FLUSHALL or another service's keys.
    keys = list(client.scan_iter(match=namespace + ":*"))
    if keys:
        client.delete(*keys)
    client.close()


def snapshot(state, seconds=0):
    return state.snapshot("A-D", DAY, now=NOW + timedelta(seconds=seconds))


@pytest.mark.redis
def test_fresh_stale_unavailable_boundaries_and_independent_service(redis_state):
    client, state, _ = redis_state
    gps = event(vehicle_id="v", position=Position(latitude=12.97, longitude=77.59))
    assert state.ingest(gps, now=NOW) == "accepted"
    assert snapshot(state, 90).vehicle.freshness == "fresh"
    assert snapshot(state, 90).service == "unknown"
    stale = snapshot(state, 90.001)
    assert stale.vehicle.freshness == "stale" and stale.observed_position is None
    expired = snapshot(state, 900)
    assert expired.vehicle.freshness == "unavailable" and expired.service == "unknown"
    assert 0 < client.pttl(state._key("A-D", DAY, "vehicle")) <= 900000


@pytest.mark.redis
def test_service_and_predictions_have_separate_provenance(redis_state):
    _, state, _ = redis_state
    assert (
        state.ingest(event(kind="trip_update", service="delayed", delay_seconds=120), now=NOW)
        == "accepted"
    )
    value = snapshot(state)
    assert value.data_mode == "simulation" and value.scheduled_information == "not_loaded"
    assert value.vehicle.freshness == "unavailable"
    assert value.predicted.delay_seconds == 120 and value.predicted.eta_uncertain
    assert value.trip_update.observed_at == NOW and value.trip_update.received_at == NOW
    assert snapshot(state, 91).predicted is None
    assert snapshot(state, 91).service == "unknown"


@pytest.mark.redis
def test_only_fresh_independent_trip_update_can_cancel(redis_state):
    _, state, _ = redis_state
    state.ingest(event(kind="trip_update", service="cancelled"), now=NOW)
    state.ingest(event("gps", seconds=100), now=NOW + timedelta(seconds=100))
    state.ingest(event("alert", kind="alert", seconds=100), now=NOW + timedelta(seconds=100))
    assert snapshot(state, 100).service == "unknown"
    assert snapshot(state, 100).vehicle.freshness == "fresh"
    assert snapshot(state, 100).alert.freshness == "fresh"


@pytest.mark.redis
def test_duplicate_conflict_and_late_events_never_refresh_snapshot_or_ttl(redis_state):
    client, state, _ = redis_state
    original = event(kind="trip_update", service="scheduled")
    assert state.ingest(original, now=NOW) == "accepted"
    ttl = client.pttl(state._key("A-D", DAY, "trip_update"))
    assert state.ingest(original, now=NOW + timedelta(seconds=60)) == "duplicate"
    assert state.ingest(event(kind="trip_update", service="cancelled"), now=NOW) == "conflicting_id"
    assert (
        state.ingest(event("late", seconds=-1, kind="trip_update", service="cancelled"), now=NOW)
        == "out_of_order"
    )
    assert client.pttl(state._key("A-D", DAY, "trip_update")) <= ttl
    assert snapshot(state, 91).service == "unknown"


@pytest.mark.redis
def test_delayed_receipt_ttl_uses_observation_time(redis_state):
    client, state, _ = redis_state
    assert state.ingest(event(seconds=-890), now=NOW) == "accepted"
    assert 0 < client.pttl(state._key("A-D", DAY, "vehicle")) <= 10000
    assert snapshot(state).vehicle.freshness == "stale"
    assert snapshot(state, 10).vehicle.freshness == "unavailable"
    assert state.ingest(event("expired", seconds=-900), now=NOW) == "quarantined"


@pytest.mark.redis
def test_simultaneous_same_event_commits_exactly_once(redis_state):
    client, _, namespace = redis_state
    barrier = Barrier(8)

    def write(_):
        state = worker(client, namespace, max_attempts=16)
        barrier.wait()
        return state.ingest(event(), now=NOW)

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(write, range(8)))
    assert outcomes.count("accepted") == 1
    assert outcomes.count("duplicate") == 7


@pytest.mark.redis
def test_concurrent_ordering_and_channel_updates_are_not_lost(redis_state):
    client, state, namespace = redis_state
    barrier = Barrier(4)
    events = [
        event("old", seconds=-2),
        event("new", seconds=-1),
        event("service", kind="trip_update", service="cancelled"),
        event("alert", kind="alert"),
    ]

    def write(item):
        barrier.wait()
        return worker(client, namespace, max_attempts=16).ingest(item, now=NOW)

    with ThreadPoolExecutor(max_workers=4) as executor:
        outcomes = list(executor.map(write, events))
    assert set(outcomes) <= {"accepted", "out_of_order"}
    result = snapshot(state)
    assert result.vehicle.observed_at == NOW - timedelta(seconds=1)
    assert result.service == "cancelled" and result.alert.freshness == "fresh"


@pytest.mark.redis
def test_watch_conflict_retries_and_retry_exhaustion_is_bounded(redis_state, monkeypatch):
    client, state, _ = redis_state
    execute = Pipeline.execute
    conflicts = []

    def race(pipeline, *args, **kwargs):
        if not conflicts:
            conflicts.append(True)
            client.set(state.metadata_key, client.get(state.metadata_key) or "{}")
            # Remove injected invalid initial data; two changes still trigger WATCH.
            client.delete(state.metadata_key)
        return execute(pipeline, *args, **kwargs)

    monkeypatch.setattr(Pipeline, "execute", race)
    assert state.ingest(event(), now=NOW) == "accepted"
    assert len(conflicts) == 1

    def exhausted(*args, **kwargs):
        raise WatchError()

    monkeypatch.setattr(Pipeline, "execute", exhausted)
    assert state.ingest(event("new", seconds=1), now=NOW + timedelta(seconds=1)) == "contended"


@pytest.mark.redis
def test_lost_commit_response_is_safe_to_retry(redis_state, monkeypatch):
    _, state, _ = redis_state
    execute = Pipeline.execute

    def lost_response(pipeline, *args, **kwargs):
        execute(pipeline, *args, **kwargs)
        raise ConnectionError("injected lost response")

    with monkeypatch.context() as patch:
        patch.setattr(Pipeline, "execute", lost_response)
        assert state.ingest(event(), now=NOW) == "unavailable"
    assert state.ingest(event(), now=NOW) == "duplicate"
    assert snapshot(state).vehicle.freshness == "fresh"


@pytest.mark.redis
def test_redis_outage_fails_closed_then_recovers(redis_state, monkeypatch):
    _, state, _ = redis_state
    state.ingest(event(kind="trip_update", service="cancelled"), now=NOW)

    def down(*args, **kwargs):
        raise ConnectionError("private connection details must not escape")

    with monkeypatch.context() as patch:
        patch.setattr(state.client, "pipeline", down)
        result = snapshot(state)
        assert result.storage_status == "unavailable" and result.service == "unknown"
        assert result.predicted is None and result.observed_position is None
        assert state.ingest(event("new"), now=NOW) == "unavailable"
    assert snapshot(state).service == "cancelled"
    assert snapshot(state, 91).service == "unknown"


@pytest.mark.redis
def test_gps_jump_quarantine_reassignment_and_scope_isolation(redis_state):
    client, state, namespace = redis_state
    state.ingest(event(vehicle_id="one", position=Position(latitude=12, longitude=77)), now=NOW)
    jump = event("jump", seconds=1, vehicle_id="one", position=Position(latitude=20, longitude=80))
    assert state.ingest(jump, now=NOW + timedelta(seconds=1)) == "quarantined"
    reassigned = jump.model_copy(update={"event_id": "new", "vehicle_id": "two"})
    assert state.ingest(reassigned, now=NOW + timedelta(seconds=1)) == "accepted"
    assert snapshot(state, 1).observed_position == jump.position
    other = RedisTrackingState(
        client, namespace=namespace, source_id="other", fixture_trips=frozenset({("A-D", DAY)})
    )
    assert snapshot(other, 1).vehicle.freshness == "unavailable"
    assert state.snapshot("B-D", DAY, now=NOW + timedelta(seconds=1)).service == "unknown"


@pytest.mark.redis
def test_capacity_expiry_and_policy_mismatch_fail_closed(redis_state):
    client, _, namespace = redis_state
    state = worker(client, namespace, max_records=1)
    assert state.ingest(event(), now=NOW) == "accepted"
    assert state.ingest(event("new", seconds=1), now=NOW + timedelta(seconds=1)) == "capacity"
    assert worker(client, namespace).ingest(event(), now=NOW) == "unavailable"
    assert state.ingest(event("after", seconds=900), now=NOW + timedelta(seconds=900)) == "accepted"


@pytest.mark.redis
def test_corrupt_metadata_and_snapshot_fail_closed_without_overwrite(redis_state):
    client, state, _ = redis_state
    client.set(state.metadata_key, '{"private":"invalid"}')
    assert snapshot(state).storage_status == "unavailable"
    assert state.ingest(event(), now=NOW) == "unavailable"
    assert client.get(state.metadata_key) == b'{"private":"invalid"}'
    client.delete(state.metadata_key)
    state.ingest(event(), now=NOW)
    client.set(state._key("A-D", DAY, "vehicle"), "invalid")
    assert snapshot(state).service == "unknown"
    assert snapshot(state).storage_status == "unavailable"


@pytest.mark.redis
def test_expired_payload_does_not_remove_ordering_protection(redis_state):
    client, state, _ = redis_state
    state.ingest(event(), now=NOW)
    client.pexpire(state._key("A-D", DAY, "vehicle"), 0)
    assert snapshot(state).vehicle.freshness == "unavailable"
    assert state.ingest(event("older", seconds=-1), now=NOW) == "out_of_order"
    assert snapshot(state).service == "unknown"


def test_real_connection_refusal_returns_unavailable():
    client = tracking_client("redis://127.0.0.1:1/0")
    state = worker(client, "nammamove:simulation:refused")
    assert snapshot(state).storage_status == "unavailable"
    assert state.ingest(event(), now=NOW) == "unavailable"
    client.close()


@pytest.mark.parametrize(
    "options",
    [
        {"fresh_seconds": 900},
        {"retention_seconds": 0},
        {"max_records": 1001},
        {"max_attempts": 0},
        {"max_speed_mps": float("nan")},
    ],
)
def test_invalid_worker_policy_rejected(options):
    with pytest.raises(ValueError):
        worker(Redis(), "nammamove:simulation:invalid", **options)


@pytest.mark.redis
def test_missing_metadata_fails_closed_instead_of_losing_ordering(redis_state):
    client, state, _ = redis_state
    state.ingest(event(), now=NOW)
    client.delete(state.metadata_key)
    assert snapshot(state).storage_status == "unavailable"
    assert state.ingest(event("older", seconds=-1), now=NOW) == "unavailable"


@pytest.mark.redis
def test_clock_regression_and_unknown_scope_cannot_change_state(redis_state):
    _, state, _ = redis_state
    assert state.ingest(event(), now=NOW) == "accepted"
    assert (
        state.ingest(event("old-clock", seconds=-1), now=NOW - timedelta(seconds=1))
        == "unavailable"
    )
    assert snapshot(state, -1).storage_status == "unavailable"
    assert state.ingest(event("future", seconds=1), now=NOW) == "quarantined"
    assert state.ingest(event().model_copy(update={"source_id": "other"}), now=NOW) == "quarantined"
    with pytest.raises(ValueError, match="aware"):
        state.ingest(event(), now=NOW.replace(tzinfo=None))


@pytest.mark.redis
def test_sealed_protobuf_replay_into_redis_and_feed_blackout(redis_state):
    from app.realtime.gtfs_rt import FixtureGtfsRtAdapter
    from test_realtime_gtfs_rt import wire

    _, state, _ = redis_state
    adapter = FixtureGtfsRtAdapter("fixture", frozenset({("A-D", DAY)}))
    batch = adapter.decode(wire(), now=NOW)
    for item in batch.events:
        assert state.ingest(item, now=NOW) == "accepted"
    for item in batch.events:
        assert state.ingest(item, now=NOW + timedelta(seconds=60)) == "duplicate"
    assert snapshot(state).service == "delayed"
    assert snapshot(state, 91).service == "unknown"
    assert snapshot(state, 900).observed_position is None
    assert snapshot(state, 900).trip_update.freshness == "unavailable"


@pytest.mark.redis
def test_state_loss_returns_unknown_and_stale_replay_cannot_resurrect(redis_state):
    client, state, _ = redis_state
    item = event(kind="trip_update", service="cancelled")
    state.ingest(item, now=NOW)
    keys = list(client.scan_iter(match=state.prefix + "*"))
    client.delete(*keys)
    assert snapshot(state).service == "unknown"
    assert state.ingest(item, now=NOW + timedelta(seconds=900)) == "quarantined"
    assert state.ingest(event("new", seconds=901), now=NOW + timedelta(seconds=901)) == "accepted"
    assert snapshot(state, 901).service == "unknown"


def test_unbounded_connections_rejected_before_io():
    with pytest.raises(ValueError, match="bounded timeouts"):
        worker(Redis(), "nammamove:simulation:unbounded")


@pytest.mark.redis
def test_redis_naturally_deletes_expired_payload_but_keeps_dedup_guard(redis_state):
    client, state, _ = redis_state
    item = event(seconds=-899.98)
    assert state.ingest(item, now=NOW) == "accepted"
    key = state._key("A-D", DAY, "vehicle")
    deadline = time.monotonic() + 2
    while client.exists(key) and time.monotonic() < deadline:
        time.sleep(0.005)
    assert client.get(key) is None
    assert client.exists(state.metadata_key)
    assert state.ingest(item, now=NOW) == "duplicate"
    assert snapshot(state).service == "unknown"


@pytest.mark.redis
def test_cancellation_cannot_be_presented_as_a_delay_prediction(redis_state):
    _, state, _ = redis_state
    state.ingest(event(kind="trip_update", service="cancelled", delay_seconds=120), now=NOW)
    value = snapshot(state)
    assert value.service == "cancelled" and value.predicted is None


@pytest.mark.redis
def test_configured_freshness_and_retention_have_exact_boundaries(redis_state):
    client, _, namespace = redis_state
    state = worker(client, namespace, fresh_seconds=2, retention_seconds=5)
    state.ingest(event(kind="trip_update", service="cancelled"), now=NOW)
    assert snapshot(state, 2).service == "cancelled"
    assert snapshot(state, 2.001).trip_update.freshness == "stale"
    assert snapshot(state, 2.001).service == "unknown"
    assert snapshot(state, 5).trip_update.freshness == "unavailable"
    assert 0 < client.pttl(state._key("A-D", DAY, "trip_update")) <= 5000
