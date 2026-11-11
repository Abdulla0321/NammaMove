"""Authored synthetic replay acceptance; no licensed feeds or device locations."""

from datetime import date, datetime, timedelta, timezone

import pytest
from app.realtime.replay import FixtureReplay, Position, ReplayEvent
from pydantic import ValidationError

NOW = datetime(2026, 11, 3, 8, tzinfo=timezone.utc)
DAY = date(2026, 11, 3)


def event(identity="1", kind="vehicle", seconds=0, **fields):
    return ReplayEvent(
        source_id="fixture",
        event_id=identity,
        trip_id="A-D",
        service_date=DAY,
        kind=kind,
        observed_at=NOW + timedelta(seconds=seconds),
        **fields,
    )


def harness(**kwargs):
    return FixtureReplay(frozenset({"fixture"}), **kwargs)


def view(replay, seconds=0, source="fixture", day=DAY):
    return replay.view(source, "A-D", day, now=NOW + timedelta(seconds=seconds))


def test_blackout_never_cancels_and_expiry_removes_position():
    replay = harness()
    assert view(replay).service == "unknown"
    replay.ingest(event(position=Position(latitude=12, longitude=77), vehicle_id="v"), now=NOW)
    assert view(replay).vehicle.freshness == "fresh"
    assert view(replay, 91).vehicle.freshness == "stale"
    assert view(replay, 91).position is None
    assert view(replay, 91).service == "unknown"
    assert view(replay, 900).vehicle.freshness == "unavailable"
    assert view(replay, 900).service == "unknown"


def test_cancellation_requires_independent_fresh_trip_update():
    replay = harness()
    replay.ingest(event(kind="trip_update", service="cancelled"), now=NOW)
    replay.ingest(event("vehicle", seconds=1), now=NOW + timedelta(seconds=1))
    assert view(replay, 1).service == "cancelled"
    assert view(replay, 1).vehicle.freshness == "fresh"
    assert view(replay, 91).service == "unknown"


def test_alert_freshness_does_not_refresh_trip_or_gps():
    replay = harness()
    replay.ingest(event(kind="trip_update", service="delayed", delay_seconds=120), now=NOW)
    replay.ingest(event("alert", kind="alert", seconds=100), now=NOW + timedelta(seconds=100))
    result = view(replay, 100)
    assert result.alert.freshness == "fresh"
    assert result.trip_update.freshness == "stale"
    assert result.vehicle.freshness == "unavailable"
    assert result.service == "unknown"
    assert result.delay_seconds is None
    assert result.eta_uncertain and result.data_mode == "simulation"


def test_duplicate_and_conflicting_id_do_not_refresh_observed_age():
    replay = harness()
    original = event(kind="trip_update", service="scheduled")
    assert replay.ingest(original, now=NOW) == "accepted"
    assert replay.ingest(original, now=NOW + timedelta(seconds=60)) == "duplicate"
    assert (
        replay.ingest(
            event(kind="trip_update", service="cancelled"), now=NOW + timedelta(seconds=60)
        )
        == "conflicting_id"
    )
    assert view(replay, 91).trip_update.freshness == "stale"
    assert replay.metrics["duplicate"] == 1


def test_old_equal_future_and_unknown_source_events_cannot_replace_state():
    replay = harness()
    replay.ingest(event(kind="trip_update", service="scheduled"), now=NOW)
    assert (
        replay.ingest(event("equal", kind="trip_update", service="cancelled"), now=NOW)
        == "out_of_order"
    )
    assert (
        replay.ingest(event("old", kind="trip_update", seconds=-1, service="cancelled"), now=NOW)
        == "out_of_order"
    )
    assert replay.ingest(event("future", seconds=1), now=NOW) == "quarantined"
    unknown = event().model_copy(update={"source_id": "unapproved"})
    assert replay.ingest(unknown, now=NOW) == "quarantined"
    assert view(replay).service == "scheduled"


def test_gps_jump_quarantined_but_vehicle_reassignment_does_not_compare_vehicles():
    replay = harness()
    replay.ingest(event(position=Position(latitude=12, longitude=77), vehicle_id="v1"), now=NOW)
    jump = event("jump", seconds=1, position=Position(latitude=20, longitude=80), vehicle_id="v1")
    assert replay.ingest(jump, now=NOW + timedelta(seconds=1)) == "quarantined"
    reassigned = event("new", seconds=2, position=jump.position, vehicle_id="v2")
    assert replay.ingest(reassigned, now=NOW + timedelta(seconds=2)) == "accepted"
    assert view(replay, 2).position == jump.position


def test_source_and_service_date_isolate_state():
    replay = FixtureReplay(frozenset({"fixture", "other"}))
    replay.ingest(event(kind="trip_update", service="cancelled"), now=NOW)
    assert view(replay, source="other").service == "unknown"
    assert view(replay, day=DAY + timedelta(days=1)).service == "unknown"


def test_capacity_fails_closed_then_retention_frees_records():
    replay = harness(max_records=1)
    replay.ingest(event(), now=NOW)
    assert replay.ingest(event("2", seconds=1), now=NOW + timedelta(seconds=1)) == "capacity"
    assert replay.ingest(event("3", seconds=900), now=NOW + timedelta(seconds=900)) == "accepted"
    assert view(replay, 900).vehicle.observed_age_seconds == 0


def test_stale_replay_after_retention_cannot_resurrect_and_clock_cannot_reverse():
    replay = harness()
    assert replay.ingest(event(), now=NOW + timedelta(seconds=900)) == "quarantined"
    with pytest.raises(ValueError, match="backwards"):
        view(replay)
    with pytest.raises(ValueError, match="aware"):
        replay.view("fixture", "A-D", DAY, now=datetime(2026, 11, 3))


@pytest.mark.parametrize(
    "fields",
    [
        {"data_mode": "live"},
        {"kind": "vehicle", "service": "cancelled"},
        {"kind": "alert", "delay_seconds": 2},
        {"position": {"latitude": float("nan"), "longitude": 77}},
        {"position": {"latitude": 91, "longitude": 77}},
        {"position": {"latitude": 12, "longitude": 77}},
        {"observed_at": datetime(2026, 11, 3)},
        {"kind": "trip_update"},
        {"verified": True},
    ],
)
def test_invalid_or_client_trust_payload_rejected(fields):
    base = event().model_dump()
    with pytest.raises(ValidationError):
        ReplayEvent.model_validate({**base, **fields})
