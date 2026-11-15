"""Whole-feed behavior against genuine Redis, using authored protobuf fixtures."""

import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier

import pytest
from app.realtime.gtfs_rt import FixtureGtfsRtAdapter
from app.realtime.ingestion import FullDatasetWorker, RedisFullDataset
from redis.client import Pipeline
from redis.exceptions import ConnectionError, WatchError
from test_realtime_gtfs_rt import DAY, NOW, source
from test_realtime_gtfs_rt import wire as old_wire
from test_realtime_redis import redis_state, worker

__all__ = ["redis_state"]
pytestmark = pytest.mark.redis


def wire(data):
    # Independent official wire encoding: field 4, length-delimited UTF-8 string.
    # The old installed binding cannot encode this standard header field itself.
    from google.transit import gtfs_realtime_pb2 as gtfs

    data = deepcopy(data)
    version = data["header"].pop("feed_version", None)
    if version is None:
        return old_wire(data)
    message = gtfs.FeedMessage.FromString(old_wire(data))

    def varint(value):
        result = bytearray()
        while value > 127:
            result.append((value & 127) | 128)
            value >>= 7
        result.append(value)
        return bytes(result)

    encoded = version.encode()
    header = message.header.SerializeToString() + b"\x22" + varint(len(encoded)) + encoded
    message.ClearField("header")
    # Required header is supplied manually; serialize entities without initialization check.
    return b"\x0a" + varint(len(header)) + header + message.SerializePartialToString()


def at(seconds=0):
    return NOW + timedelta(seconds=seconds)


def feed(seconds=0, *, channels=(0, 1, 2), version=None, observe=True):
    data = source()
    data["header"]["timestamp"] = str(int(at(seconds).timestamp()))
    if version is not None:
        data["header"]["feed_version"] = version
    data["entity"] = [data["entity"][i] for i in channels]
    if observe:
        for entity in data["entity"]:
            for kind in ("vehicle", "trip_update"):
                if kind in entity:
                    entity[kind]["timestamp"] = data["header"]["timestamp"]
    return data


def store(redis_state, **options):
    client, _, namespace = redis_state
    state = worker(client, namespace, **options)
    adapter = FixtureGtfsRtAdapter(
        "fixture", state.fixture_trips, retention_seconds=state.retention_seconds
    )
    return RedisFullDataset(adapter, state)


def view(target, seconds=0):
    return target.snapshot("A-D", DAY, now=at(seconds))


def test_full_replacement_withdraws_omissions_without_cancellation_or_recovery(redis_state):
    target = store(redis_state)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"
    first = view(target)
    assert first.data_mode == "simulation" and first.tracking.service == "delayed"
    assert first.tracking.vehicle.freshness == "fresh"
    assert target.ingest(wire(feed(1, channels=(0,))), now=at(1)) == "accepted"
    result = view(target, 1)
    assert result.tracking.service == "unknown" and result.tracking.predicted is None
    assert result.tracking.alert.freshness == "unavailable"
    assert target.ingest(wire(feed(2, channels=())), now=at(2)) == "accepted"
    result = view(target, 2)
    assert result.tracking.observed_position is None and result.tracking.service == "unknown"


@pytest.mark.parametrize("channels", [(0,), (1,), (2,), ()])
def test_empty_and_partial_snapshots_do_not_invent_service(redis_state, channels):
    target = store(redis_state)
    data = feed(channels=channels)
    if 1 in channels:
        update = data["entity"][0]["trip_update"]
        update["trip"]["schedule_relationship"] = "CANCELED"
        del update["delay"]
    assert target.ingest(wire(data), now=NOW) == "accepted"
    assert view(target).tracking.service == ("cancelled" if 1 in channels else "unknown")
    assert view(target, 91).tracking.service == "unknown"
    assert view(target, 900).tracking.service == "unknown"


def test_duplicate_reordering_and_conflict_do_not_refresh_ttl(redis_state):
    client, _, _ = redis_state
    target = store(redis_state)
    data = feed()
    assert target.ingest(wire(data), now=NOW) == "accepted"
    before = {key: client.pttl(key) for key in client.scan_iter(match=target.prefix + "*")}
    data["entity"].reverse()
    assert target.ingest(wire(data), now=at(60)) == "duplicate"
    for key, ttl in before.items():
        assert client.pttl(key) <= ttl
    data["entity"] = []
    assert target.ingest(wire(data), now=at(60)) == "conflict"
    assert view(target, 60).received_at == NOW
    assert view(target, 91).tracking.service == "unknown"


def test_header_ordering_survives_empty_feed_and_worker_reconstruction(redis_state):
    target = store(redis_state)
    assert target.ingest(wire(feed(10, channels=())), now=at(10)) == "accepted"
    restarted = store(redis_state)
    assert restarted.ingest(wire(feed()), now=at(10)) == "out_of_order"
    assert view(restarted, 10).tracking.service == "unknown"


def test_opaque_static_version_is_pinned_not_lexically_ordered(redis_state):
    base = store(redis_state)
    target = RedisFullDataset(base.adapter, base.state, expected_feed_version="static-fixture-9")
    assert target.ingest(wire(feed(version="static-fixture-9")), now=NOW) == "accepted"
    for version in (None, "static-fixture-10", "old"):
        assert target.ingest(wire(feed(1, version=version)), now=at(1)) == "rejected"
    assert view(target, 1).tracking.service == "delayed"
    assert base.ingest(wire(feed(1)), now=at(1)) == "unavailable"


def test_refreshed_header_cannot_refresh_observation_or_receipt(redis_state):
    target = store(redis_state)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"
    assert target.ingest(wire(feed(100, observe=False)), now=at(100)) == "accepted"
    result = view(target, 100)
    assert result.feed_freshness == "fresh"
    assert result.tracking.vehicle.freshness == "stale"
    assert result.tracking.vehicle.received_at == NOW
    assert result.tracking.service == "unknown"


def test_omitted_channel_guards_reject_old_or_equal_conflicting_reintroduction(redis_state):
    target = store(redis_state)
    assert target.ingest(wire(feed(10)), now=at(10)) == "accepted"
    assert target.ingest(wire(feed(11, channels=())), now=at(11)) == "accepted"
    old = feed(12)
    old["entity"][0]["vehicle"]["timestamp"] = str(int(NOW.timestamp()))
    assert target.ingest(wire(old), now=at(12)) == "out_of_order"
    equal = feed(12)
    equal["entity"][0]["vehicle"]["timestamp"] = str(int(at(10).timestamp()))
    equal["entity"][0]["vehicle"]["vehicle"]["id"] = "changed"
    assert target.ingest(wire(equal), now=at(12)) == "conflict"
    assert view(target, 12).tracking.vehicle.freshness == "unavailable"


@pytest.mark.parametrize(
    "failure", ["malformed", "differential", "unknown_trip", "expired", "future", "ambiguous"]
)
def test_failed_feed_preserves_all_previous_channels(redis_state, failure):
    target = store(redis_state)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"
    data = feed(1)
    if failure == "differential":
        data["header"]["incrementality"] = "DIFFERENTIAL"
    elif failure == "unknown_trip":
        data["entity"][-1]["alert"]["informed_entity"][0]["trip"]["trip_id"] = "unknown"
    elif failure == "expired":
        data["entity"][0]["vehicle"]["timestamp"] = str(int(at(-900).timestamp()))
    elif failure == "future":
        data["header"]["timestamp"] = str(int(at(2).timestamp()))
    elif failure == "ambiguous":
        other = deepcopy(data["entity"][0])
        other["id"] = "other-id-same-trip-channel"
        data["entity"].append(other)
    assert (
        target.ingest(b"broken" if failure == "malformed" else wire(data), now=at(1)) == "rejected"
    )
    result = view(target, 1)
    assert result.header_at == NOW and result.tracking.service == "delayed"
    assert result.tracking.alert.freshness == "fresh"


def test_alert_intervals_expire_activate_and_gap_without_new_feed(redis_state):
    target = store(redis_state)
    data = feed(channels=(2,))
    data["entity"][0]["alert"]["active_period"] = [
        {"start": str(int(at(2).timestamp())), "end": str(int(at(4).timestamp()))},
        {"start": str(int(at(6).timestamp())), "end": str(int(at(8).timestamp()))},
    ]
    assert target.ingest(wire(data), now=NOW) == "accepted"
    for seconds, expected in [
        (0, "unavailable"),
        (2, "fresh"),
        (3.99, "fresh"),
        (4, "unavailable"),
        (6, "fresh"),
        (8, "unavailable"),
    ]:
        result = view(target, seconds)
        assert result.tracking.alert.freshness == expected
        assert result.tracking.service == "unknown"


@pytest.mark.parametrize("periods", [[], [{"start": "0"}], [{"end": "9999999999"}]])
def test_alert_open_bounds_are_supported(redis_state, periods):
    target = store(redis_state)
    data = feed(channels=(2,))
    data["entity"][0]["alert"]["active_period"] = periods
    assert target.ingest(wire(data), now=NOW) == "accepted"
    assert view(target).tracking.alert.freshness == "fresh"
    assert view(target, 900).tracking.alert.freshness == "unavailable"


def test_multiple_alerts_same_trip_expire_independently(redis_state):
    target = store(redis_state)
    data = feed(channels=(2,))
    other = deepcopy(data["entity"][0])
    other["id"] = "second-alert"
    data["entity"][0]["alert"]["active_period"] = [{"end": str(int(at(1).timestamp()))}]
    other["alert"]["active_period"] = [{"end": str(int(at(3).timestamp()))}]
    data["entity"].append(other)
    assert target.ingest(wire(data), now=NOW) == "accepted"
    assert view(target, 1).tracking.alert.freshness == "fresh"
    assert view(target, 3).tracking.alert.freshness == "unavailable"


def test_natural_redis_alert_ttl_and_no_duplicate_extension(redis_state):
    client, _, _ = redis_state
    target = store(redis_state)
    data = feed(channels=(2,))
    data["entity"][0]["alert"]["active_period"] = [{"end": str(int(at(1).timestamp()))}]
    payload = wire(data)
    assert target.ingest(payload, now=NOW) == "accepted"
    keys = list(client.scan_iter(match=target.prefix + "payload:*"))
    assert len(keys) == 1 and 0 < client.pttl(keys[0]) <= 1000
    assert target.ingest(payload, now=NOW) == "duplicate"
    deadline = time.monotonic() + 2
    while client.exists(keys[0]) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert client.get(keys[0]) is None and client.exists(target.key)


def test_inactive_alert_fanout_is_bounded_too(redis_state):
    target = store(redis_state)
    data = feed(channels=(2,))
    alert = data["entity"][0]["alert"]
    alert["active_period"] = [{"start": str(int(at(100).timestamp()))}]
    alert["informed_entity"] *= 3
    target.adapter.max_events = 2
    assert target.ingest(wire(data), now=NOW) == "rejected"


def test_snapshot_capacity_and_guard_capacity_preserve_previous_generation(redis_state):
    target = store(redis_state, max_records=1)
    assert target.ingest(wire(feed(channels=(0,))), now=NOW) == "accepted"
    assert target.ingest(wire(feed(1)), now=at(1)) == "capacity"
    assert target.ingest(wire(feed(1, channels=(1,))), now=at(1)) == "capacity"
    assert view(target, 1).tracking.vehicle.freshness == "fresh"


def test_impossible_gps_jump_rejects_entire_feed_but_reassignment_is_allowed(redis_state):
    target = store(redis_state)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"
    data = feed(1, channels=(0,))
    data["entity"][0]["vehicle"]["position"]["latitude"] = 20
    assert target.ingest(wire(data), now=at(1)) == "quarantined"
    assert view(target, 1).tracking.service == "delayed"
    data["entity"][0]["vehicle"]["vehicle"]["id"] = "reassigned"
    assert target.ingest(wire(data), now=at(1)) == "accepted"
    assert view(target, 1).tracking.service == "unknown"


def test_concurrent_identical_whole_feeds_commit_once(redis_state):
    target = store(redis_state, max_attempts=16)
    barrier = Barrier(6)

    def write(_):
        barrier.wait()
        return target.ingest(wire(feed()), now=NOW)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(write, range(6)))
    assert results.count("accepted") == 1 and results.count("duplicate") == 5


def test_concurrent_snapshots_and_readers_never_mix_generations(redis_state):
    target = store(redis_state, max_attempts=16)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"
    barrier = Barrier(3)

    def write(offset):
        barrier.wait()
        return target.ingest(wire(feed(offset, channels=(0,) if offset == 1 else (1,))), now=at(2))

    def read():
        barrier.wait()
        return [view(target, 2) for _ in range(20)]

    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = [pool.submit(write, 1), pool.submit(write, 2), pool.submit(read)]
        assert {tasks[0].result(), tasks[1].result()} <= {"accepted", "out_of_order"}
        results = tasks[2].result()
    for result in results:
        if result.tracking.storage_status == "unavailable":
            assert result.tracking.service == "unknown"
            continue
        stamp = int((result.header_at - NOW).total_seconds())
        assert (result.tracking.vehicle.freshness == "fresh") == (stamp in (0, 1))
        assert (result.tracking.trip_update.freshness == "fresh") == (stamp in (0, 2))
    assert view(target, 2).header_at == at(2)


def test_watch_conflict_and_lost_exec_retry_are_idempotent(redis_state, monkeypatch):
    client, _, _ = redis_state
    target = store(redis_state)
    execute = Pipeline.execute
    raced = []

    def conflict(tx, *args, **kwargs):
        if not raced:
            raced.append(True)
            client.set(target.key, "invalid")
            client.delete(target.key)
        return execute(tx, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Pipeline, "execute", conflict)
        assert target.ingest(wire(feed()), now=NOW) == "accepted"

    def lost(tx, *args, **kwargs):
        execute(tx, *args, **kwargs)
        raise ConnectionError("private URL must not escape")

    with monkeypatch.context() as patch:
        patch.setattr(Pipeline, "execute", lost)
        assert target.ingest(wire(feed(1, channels=())), now=at(1)) == "unavailable"
    assert target.ingest(wire(feed(1, channels=())), now=at(1)) == "duplicate"
    assert view(target, 1).tracking.service == "unknown"


def test_contention_exhaustion_leaves_previous_feed_intact(redis_state, monkeypatch):
    target = store(redis_state, max_attempts=2)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"

    def conflict(*args, **kwargs):
        raise WatchError()

    with monkeypatch.context() as patch:
        patch.setattr(Pipeline, "execute", conflict)
        assert target.ingest(wire(feed(1, channels=())), now=at(1)) == "contended"
    assert view(target, 1).tracking.service == "delayed"


def test_outage_corruption_and_receipt_clock_fail_closed(redis_state, monkeypatch):
    client, _, _ = redis_state
    target = store(redis_state)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"

    def down(*args, **kwargs):
        raise ConnectionError("private")

    with monkeypatch.context() as patch:
        patch.setattr(client, "pipeline", down)
        assert view(target).tracking.storage_status == "unavailable"
        assert target.ingest(wire(feed()), now=NOW) == "unavailable"
    assert view(target, -1).tracking.storage_status == "unavailable"
    client.set(target.key, "corrupt")
    assert view(target).tracking.service == "unknown"
    assert target.ingest(wire(feed(1, channels=())), now=at(1)) == "unavailable"
    assert client.get(target.key) == b"corrupt"


def test_source_date_isolation_and_cold_cache_after_state_loss(redis_state):
    client, _, namespace = redis_state
    target = store(redis_state)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"
    assert target.snapshot("B-D", DAY, now=NOW).tracking.service == "unknown"
    # Independently configured namespace, not mutable source authorization.
    isolated = RedisFullDataset(target.adapter, worker(client, namespace + "_other"))
    assert view(isolated).tracking.service == "unknown"
    keys = list(client.scan_iter(match=target.prefix + "*"))
    client.delete(*keys)
    restarted = store(redis_state)
    assert view(restarted).tracking.service == "unknown"
    assert restarted.ingest(wire(feed()), now=at(900)) == "rejected"
    assert restarted.ingest(wire(feed(901)), now=at(901)) == "accepted"


def test_queue_backpressure_byte_budget_and_oversize_admission(redis_state):
    target = store(redis_state)
    payload = wire(feed())
    queue = FullDatasetWorker(target, max_jobs=2, max_bytes=len(payload))
    assert queue.submit(payload, now=NOW) == "queued"
    assert queue.submit(payload, now=NOW) == "backpressure"
    assert queue.submit(b"x" * (target.adapter.max_bytes + 1), now=NOW) == "rejected"
    assert queue.pending == 1
    assert queue.run_one(now=NOW).outcome == "accepted"
    assert queue.pending == 0
    assert queue.submit(payload, now=NOW) == "queued"
    assert queue.run_one(now=NOW).outcome == "duplicate"


def test_worker_deterministic_retries_hold_capacity_then_exhaust(redis_state, monkeypatch):
    target = store(redis_state)
    queue = FullDatasetWorker(target, max_jobs=1)
    queue.submit(wire(feed()), now=NOW)

    def down(*args, **kwargs):
        raise ConnectionError("private")

    with monkeypatch.context() as patch:
        patch.setattr(target.client, "pipeline", down)
        first = queue.run_one(now=NOW)
        assert first.outcome == "unavailable" and first.retry_scheduled
        assert queue.run_one(now=at(0.99)) is None
        assert queue.submit(wire(feed()), now=NOW) == "backpressure"
        assert queue.run_one(now=at(1)).attempts == 2
        assert queue.run_one(now=at(2.99)) is None
        last = queue.run_one(now=at(3))
        assert last.attempts == 3 and not last.retry_scheduled
    assert queue.pending == 0 and queue.metrics["retry_exhausted"] == 1


def test_worker_lost_commit_retries_to_duplicate_and_restart_resubmission(redis_state, monkeypatch):
    target = store(redis_state)
    queue = FullDatasetWorker(target)
    payload = wire(feed())
    queue.submit(payload, now=NOW)
    execute = Pipeline.execute

    def lost(tx, *args, **kwargs):
        execute(tx, *args, **kwargs)
        raise ConnectionError("lost")

    with monkeypatch.context() as patch:
        patch.setattr(Pipeline, "execute", lost)
        assert queue.run_one(now=NOW).retry_scheduled
    assert queue.run_one(now=at(1)).outcome == "duplicate"
    restarted = FullDatasetWorker(store(redis_state))
    assert restarted.pending == 0
    restarted.submit(payload, now=at(2))
    assert restarted.run_one(now=at(2)).outcome == "duplicate"


def test_old_queued_snapshot_cannot_rollback_newer_or_expired_state(redis_state):
    target = store(redis_state)
    queue = FullDatasetWorker(target)
    queue.submit(wire(feed(2, channels=())), now=at(2))
    queue.submit(wire(feed()), now=at(2))
    assert queue.run_one(now=at(2)).outcome == "accepted"
    assert queue.run_one(now=at(2)).outcome == "out_of_order"
    queue.submit(wire(feed()), now=at(2))
    assert queue.run_one(now=at(900)).outcome == "rejected"
    assert view(target, 900).tracking.service == "unknown"


def test_concurrent_producers_respect_queue_capacity(redis_state):
    queue = FullDatasetWorker(store(redis_state), max_jobs=3)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: queue.submit(wire(feed()), now=NOW), range(20)))
    assert results.count("queued") == 3 and results.count("backpressure") == 17
    assert queue.pending == 3


def test_feed_namespace_does_not_modify_legacy_event_state(redis_state):
    _, legacy, _ = redis_state
    from test_realtime_redis import event

    assert legacy.ingest(event(kind="trip_update", service="cancelled"), now=NOW) == "accepted"
    target = store(redis_state)
    assert target.ingest(wire(feed(channels=())), now=NOW) == "accepted"
    assert legacy.snapshot("A-D", DAY, now=NOW).service == "cancelled"
    assert view(target).tracking.service == "unknown"


def test_omission_cannot_bypass_same_vehicle_jump_quarantine(redis_state):
    target = store(redis_state)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"
    assert target.ingest(wire(feed(1, channels=())), now=at(1)) == "accepted"
    data = feed(2, channels=(0,))
    data["entity"][0]["vehicle"]["position"]["latitude"] = 20
    assert target.ingest(wire(data), now=at(2)) == "quarantined"
    assert view(target, 2).tracking.observed_position is None
    data["entity"][0]["vehicle"]["vehicle"]["id"] = "new-assigned-vehicle"
    assert target.ingest(wire(data), now=at(2)) == "accepted"


def test_identical_omitted_observation_preserves_original_receipt_and_age(redis_state):
    target = store(redis_state)
    assert target.ingest(wire(feed()), now=NOW) == "accepted"
    assert target.ingest(wire(feed(1, channels=())), now=at(1)) == "accepted"
    assert target.ingest(wire(feed(2, observe=False)), now=at(2)) == "accepted"
    result = view(target, 2)
    assert result.tracking.vehicle.received_at == NOW
    assert result.tracking.trip_update.received_at == NOW
    assert result.tracking.vehicle.observed_age_seconds == 2


@pytest.mark.parametrize("corruption", ["missing", "invalid"])
def test_duplicate_cannot_acknowledge_incomplete_or_corrupt_generation(redis_state, corruption):
    client, _, _ = redis_state
    target = store(redis_state)
    queue = FullDatasetWorker(target, max_attempts=1)
    payload = wire(feed())
    assert target.ingest(payload, now=NOW) == "accepted"
    key = next(client.scan_iter(match=target.prefix + "payload:*"))
    if corruption == "missing":
        client.delete(key)
    else:
        client.set(key, "invalid")
    assert target.ingest(payload, now=at(1)) == "unavailable"
    assert queue.submit(payload, now=at(1)) == "queued"
    assert queue.run_one(now=at(1)).outcome == "unavailable"
    assert view(target, 1).tracking.storage_status == "unavailable"
    # Even an unrelated trip cannot expose a partially committed generation.
    assert target.snapshot("B-D", DAY, now=at(1)).tracking.storage_status == "unavailable"


def test_queue_inflight_reserves_capacity_and_second_consumer_does_not_duplicate(
    redis_state, monkeypatch
):
    from threading import Event

    target = store(redis_state)
    queue = FullDatasetWorker(target, max_jobs=1)
    queue.submit(wire(feed()), now=NOW)
    entered, release = Event(), Event()
    ingest = target.ingest

    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        return ingest(*args, **kwargs)

    monkeypatch.setattr(target, "ingest", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(queue.run_one, now=NOW)
        try:
            assert entered.wait(timeout=5)
            assert queue.pending == 1
            assert queue.submit(wire(feed()), now=NOW) == "backpressure"
            assert queue.run_one(now=NOW) is None
        finally:
            release.set()
        assert running.result().outcome == "accepted"
    assert queue.pending == 0


@pytest.mark.parametrize(
    "options",
    [
        {"max_jobs": 0},
        {"max_jobs": 65},
        {"max_bytes": 0},
        {"max_bytes": 8388609},
        {"max_attempts": 6},
    ],
)
def test_invalid_queue_bounds_fail_before_admission(redis_state, options):
    with pytest.raises(ValueError, match="bounded"):
        FullDatasetWorker(store(redis_state), **options)


def test_expired_and_future_alert_ranges_do_not_overflow_wire_clock(redis_state):
    target = store(redis_state)
    data = feed(channels=(2,))
    data["entity"][0]["alert"]["active_period"] = [{"end": str(2**64 - 1)}]
    assert target.ingest(wire(data), now=NOW) == "accepted"
    assert view(target).tracking.alert.freshness == "fresh"


def test_new_schema_fields_remain_rejected_with_feed_version_support(redis_state):
    target = store(redis_state)
    payload = wire(feed()) + b"\xa0\x06\x01"
    assert target.ingest(payload, now=NOW) == "rejected"


@pytest.mark.parametrize(
    "change",
    ["service", "position", "trip", "identity", "receipt", "expired_clock", "future_clock"],
)
def test_valid_json_payload_corruption_cannot_be_read_or_acknowledged(redis_state, change):
    import json

    client, _, _ = redis_state
    target = store(redis_state)
    payload = wire(feed())
    assert target.ingest(payload, now=NOW) == "accepted"
    for key in client.scan_iter(match=target.prefix + "payload:*"):
        value = json.loads(client.get(key))
        event = value["event"]
        if change == "service" and event["kind"] == "trip_update":
            event["service"] = "cancelled"
            event["delay_seconds"] = None
        elif change == "position" and event["kind"] == "vehicle":
            event["position"]["latitude"] += 0.001
        elif change == "trip":
            event["trip_id"] = "B-D"  # Another valid fixture trip is still the wrong payload.
        elif change == "identity":
            event["event_id"] = "changed"
        elif change == "receipt":
            value["received_at"] = at(10).isoformat()
        elif change == "expired_clock":
            event["observed_at"] = at(-900).isoformat()
        elif change == "future_clock":
            event["observed_at"] = at(100).isoformat()
        else:
            continue
        client.set(key, json.dumps(value))
        break
    for trip in ("A-D", "B-D"):
        result = target.snapshot(trip, DAY, now=at(1))
        assert result.tracking.storage_status == "unavailable"
        assert result.tracking.service == "unknown"
        assert result.tracking.observed_position is None
    assert target.ingest(payload, now=at(1)) == "unavailable"
    assert target.ingest(wire(feed(2, channels=())), now=at(2)) == "unavailable"


@pytest.mark.parametrize("change", ["duplicate", "unknown_scope", "expiry", "channel_key"])
def test_semantic_manifest_corruption_fails_closed(redis_state, change):
    import json

    client, _, _ = redis_state
    target = store(redis_state)
    payload = wire(feed())
    assert target.ingest(payload, now=NOW) == "accepted"
    manifest = json.loads(client.get(target.key))
    record = manifest["records"][0]
    if change == "duplicate":
        manifest["records"].append(record)
    elif change == "unknown_scope":
        record["trip_id"] = "not-configured"
    elif change == "expiry":
        record["expires_at"] = at(100).isoformat()
    else:
        record["channel_key"] = "0" * 64
    client.set(target.key, json.dumps(manifest))
    assert view(target, 1).tracking.storage_status == "unavailable"
    assert target.ingest(payload, now=at(1)) == "unavailable"


def test_unexpected_processing_error_retries_then_releases_capacity(redis_state, monkeypatch):
    target = store(redis_state)
    queue = FullDatasetWorker(target, max_jobs=1, max_attempts=2)
    payload = wire(feed())
    queue.submit(payload, now=NOW)

    def failed(*args, **kwargs):
        raise RuntimeError("private worker details must not escape")

    with monkeypatch.context() as patch:
        patch.setattr(target, "ingest", failed)
        first = queue.run_one(now=NOW)
        assert first.outcome == "unavailable" and first.retry_scheduled
        assert queue.pending == 1
        assert queue.submit(payload, now=NOW) == "backpressure"
        last = queue.run_one(now=at(1))
        assert last.outcome == "unavailable" and not last.retry_scheduled
        assert "private" not in last.model_dump_json()
    assert queue.pending == 0 and queue.metrics["worker_error"] == 2
    assert queue.metrics["retry_exhausted"] == 1
    assert queue.submit(payload, now=at(2)) == "queued"
    assert queue.run_one(now=at(2)).outcome == "accepted"


def test_unexpected_error_after_commit_recovers_as_duplicate(redis_state, monkeypatch):
    target = store(redis_state)
    queue = FullDatasetWorker(target, max_jobs=1)
    queue.submit(wire(feed()), now=NOW)
    ingest = target.ingest

    def interrupted_after_commit(*args, **kwargs):
        assert ingest(*args, **kwargs) == "accepted"
        raise RuntimeError("post-commit interruption")

    with monkeypatch.context() as patch:
        patch.setattr(target, "ingest", interrupted_after_commit)
        assert queue.run_one(now=NOW).retry_scheduled
    assert queue.run_one(now=at(1)).outcome == "duplicate"
    assert queue.pending == 0 and view(target, 1).received_at == NOW
