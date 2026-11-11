"""Actual protobuf roundtrips using independently authored, sealed synthetic data."""

import json
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest
from app.realtime.gtfs_rt import FeedRejected, FixtureGtfsRtAdapter
from app.realtime.replay import FixtureReplay
from google.protobuf.json_format import ParseDict
from google.transit import gtfs_realtime_pb2 as gtfs

FIXTURES = Path(__file__).parent / "fixtures" / "realtime"
DAY = date(2026, 11, 4)


def source():
    return json.loads((FIXTURES / "synthetic.json").read_text(encoding="utf-8"))


def wire(data=None):
    message = gtfs.FeedMessage()
    ParseDict(source() if data is None else data, message)
    return message.SerializeToString()


NOW = datetime.fromtimestamp(int(source()["header"]["timestamp"]), timezone.utc)


def adapter(**limits):
    return FixtureGtfsRtAdapter("authored-fixture", frozenset({("A-D", DAY)}), **limits)


def state(replay, now=NOW):
    return replay.view("authored-fixture", "A-D", DAY, now=now)


def test_sealed_fixture_and_real_protobuf_roundtrip():
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    # Seal semantic JSON so Windows line endings cannot change provenance.
    canonical = json.dumps(source(), sort_keys=True, separators=(",", ":")).encode()
    assert sha256(canonical).hexdigest() == manifest["canonical_json_sha256"]
    batch = adapter().decode(wire(), now=NOW)
    assert batch.data_mode == "simulation" and batch.feed_age_seconds == 0
    assert [e.kind for e in batch.events] == ["vehicle", "trip_update", "alert"]
    replay = FixtureReplay(frozenset({"authored-fixture"}))
    for event in batch.events:
        assert replay.ingest(event, now=NOW) == "accepted"
    assert state(replay).service == "delayed"  # NO_SERVICE alert is advisory only.
    assert state(replay).eta_uncertain
    assert state(replay, NOW + timedelta(seconds=91)).service == "unknown"


def test_header_refresh_does_not_refresh_vehicle_or_trip_evidence():
    replay = FixtureReplay(frozenset({"authored-fixture"}))
    first = adapter().decode(wire(), now=NOW)
    for event in first.events:
        replay.ingest(event, now=NOW)
    data = source()
    data["header"]["timestamp"] = str(int(NOW.timestamp()) + 100)
    later = NOW + timedelta(seconds=100)
    second = adapter().decode(wire(data), now=later)
    assert second.events[:2] == first.events[:2]
    for event in second.events:
        replay.ingest(event, now=later)
    assert state(replay, later).vehicle.freshness == "stale"
    assert state(replay, later).service == "unknown"
    assert state(replay, later).alert.freshness == "fresh"


def test_reused_entity_id_allows_new_observation_and_explicit_independent_cancellation():
    data = source()
    data["entity"] = [data["entity"][1]]
    replay = FixtureReplay(frozenset({"authored-fixture"}))
    first = adapter().decode(wire(data), now=NOW).events[0]
    replay.ingest(first, now=NOW)
    data["header"]["timestamp"] = str(int(NOW.timestamp()) + 1)
    update = data["entity"][0]["trip_update"]
    update["timestamp"] = data["header"]["timestamp"]
    update["trip"]["schedule_relationship"] = "CANCELED"
    del update["delay"]
    later = NOW + timedelta(seconds=1)
    second = adapter().decode(wire(data), now=later).events[0]
    assert first.event_id != second.event_id
    assert replay.ingest(second, now=later) == "accepted"
    assert state(replay, later).service == "cancelled"


def test_empty_snapshot_and_blackout_never_cancel_or_recover():
    data = source()
    data["entity"] = []
    assert adapter().decode(wire(data), now=NOW).events == ()
    replay = FixtureReplay(frozenset({"authored-fixture"}))
    assert state(replay).service == "unknown"
    assert state(replay, NOW + timedelta(seconds=901)).service == "unknown"


@pytest.mark.parametrize(
    "payload",
    [b"", b"not protobuf", b"\x0a\xff", b"x" * 262145],
    ids=["empty", "invalid-wire", "truncated", "oversize"],
)
def test_malformed_and_oversized_bytes_fail_safely(payload):
    with pytest.raises(FeedRejected, match="^Synthetic GTFS-RT feed rejected$"):
        adapter().decode(payload, now=NOW)


@pytest.mark.parametrize(
    "change",
    [
        "differential",
        "version",
        "future_header",
        "old_header",
        "future_observation",
        "missing_observation",
        "missing_date",
        "unknown_trip",
        "bad_date",
        "deleted",
        "duplicate_id",
        "two_channels",
        "vehicle_cancel",
        "cancel_delay",
        "stop_prediction",
        "nan_position",
        "route_alert",
        "invalid_period",
        "unknown_wire",
    ],
)
def test_unsupported_or_unsafe_feed_is_rejected_atomically(change):
    data = deepcopy(source())
    vehicle = data["entity"][0]["vehicle"]
    update = data["entity"][1]["trip_update"]
    alert = data["entity"][2]["alert"]
    if change == "differential":
        data["header"]["incrementality"] = "DIFFERENTIAL"
    elif change == "version":
        data["header"]["gtfs_realtime_version"] = "1.0"
    elif change == "future_header":
        data["header"]["timestamp"] = str(int(NOW.timestamp()) + 1)
    elif change == "old_header":
        data["header"]["timestamp"] = str(int(NOW.timestamp()) - 900)
    elif change == "future_observation":
        vehicle["timestamp"] = str(int(NOW.timestamp()) + 1)
    elif change == "missing_observation":
        del vehicle["timestamp"]
    elif change == "missing_date":
        del vehicle["trip"]["start_date"]
    elif change == "unknown_trip":
        vehicle["trip"]["trip_id"] = "not-in-static-fixture"
    elif change == "bad_date":
        vehicle["trip"]["start_date"] = "20260230"
    elif change == "deleted":
        data["entity"][0]["is_deleted"] = True
    elif change == "duplicate_id":
        data["entity"].append(data["entity"][0])
    elif change == "two_channels":
        data["entity"][0]["trip_update"] = update
    elif change == "vehicle_cancel":
        vehicle["trip"]["schedule_relationship"] = "CANCELED"
    elif change == "cancel_delay":
        update["trip"]["schedule_relationship"] = "CANCELED"
    elif change == "stop_prediction":
        update["stop_time_update"] = [{"stop_sequence": 1, "arrival": {"delay": 2}}]
    elif change == "nan_position":
        vehicle["position"]["latitude"] = "NaN"
    elif change == "route_alert":
        alert["informed_entity"] = [{"route_id": "route"}]
    elif change == "invalid_period":
        alert["active_period"] = [{"start": "2", "end": "1"}]
    payload = wire(data)
    if change == "unknown_wire":
        payload += b"\xa0\x06\x01"
    with pytest.raises(FeedRejected):
        adapter().decode(payload, now=NOW)


@pytest.mark.parametrize("limits", [{"max_bytes": 10}, {"max_entities": 2}, {"max_events": 2}])
def test_configured_limits_bound_work_and_alert_fanout(limits):
    with pytest.raises(FeedRejected):
        adapter(**limits).decode(wire(), now=NOW)


def test_inactive_alerts_are_not_emitted_and_receipt_clock_must_be_aware():
    data = source()
    data["entity"][2]["alert"]["active_period"] = [{"end": str(int(NOW.timestamp()))}]
    assert len(adapter().decode(wire(data), now=NOW).events) == 2
    with pytest.raises(FeedRejected):
        adapter().decode(wire(), now=NOW.replace(tzinfo=None))


def test_adapter_replay_quarantines_jump_accepts_reassignment_and_rejects_reordering():
    data = source()
    data["entity"] = [data["entity"][0]]
    replay = FixtureReplay(frozenset({"authored-fixture"}))
    first = adapter().decode(wire(data), now=NOW).events[0]
    assert replay.ingest(first, now=NOW) == "accepted"
    assert replay.ingest(first, now=NOW) == "duplicate"
    vehicle = data["entity"][0]["vehicle"]
    vehicle["position"]["latitude"] = 20
    for seconds, identity, expected in [
        (1, "authored-bus", "quarantined"),
        (2, "other-bus", "accepted"),
    ]:
        later = NOW + timedelta(seconds=seconds)
        data["header"]["timestamp"] = str(int(later.timestamp()))
        vehicle["timestamp"] = data["header"]["timestamp"]
        vehicle["vehicle"]["id"] = identity
        event = adapter().decode(wire(data), now=later).events[0]
        assert replay.ingest(event, now=later) == expected
    # A changed old payload is not a duplicate and cannot replace newer evidence.
    data = source()
    data["entity"] = [data["entity"][0]]
    data["entity"][0]["vehicle"]["vehicle"]["id"] = "late-old-bus"
    old = adapter().decode(wire(data), now=later).events[0]
    assert replay.ingest(old, now=later) == "out_of_order"
    assert state(replay, later).service == "unknown"


def test_alert_fanout_is_bounded_before_any_events_can_be_applied():
    data = source()
    data["entity"] = [data["entity"][2]]
    selector = data["entity"][0]["alert"]["informed_entity"][0]
    data["entity"][0]["alert"]["informed_entity"] = [selector] * 3
    with pytest.raises(FeedRejected):
        adapter(max_events=2).decode(wire(data), now=NOW)
    data["entity"][0]["alert"]["informed_entity"] = [selector] * 17
    with pytest.raises(FeedRejected):
        adapter().decode(wire(data), now=NOW)
