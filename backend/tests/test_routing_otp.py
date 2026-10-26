"""Actual OTP only: opt-in configured service with a sealed authored fixture graph."""

import os
from pathlib import Path

import pytest
from app.routing.build import verify_release
from app.routing.provider import OTPProvider
from test_routing import query


@pytest.fixture(scope="session")
def real_otp():
    folder = os.environ.get("NAMMAMOVE_TEST_OTP_DIR")
    url = os.environ.get("NAMMAMOVE_TEST_OTP_URL")
    if not folder or not url:
        pytest.skip(
            "Set NAMMAMOVE_TEST_OTP_DIR and NAMMAMOVE_TEST_OTP_URL for actual OTP acceptance"
        )
    import time

    from fastapi import HTTPException

    provider = OTPProvider(url, verify_release(Path(folder)))
    for _ in range(10):
        try:
            assert provider.plan(query()).status == "ok"
            return provider
        except HTTPException:
            time.sleep(1)
    pytest.fail("Configured real OTP service did not become ready; no mock substitution")


@pytest.mark.otp
def test_real_multimodal_transfer_fares_and_preferences(real_otp):
    fastest = real_otp.plan(query())
    first = fastest.itineraries[0]
    assert [leg.mode for leg in first.legs] == ["BUS", "WALK", "SUBWAY"]
    assert first.fare_inr == 30 and first.transfers == 1 and first.duration_seconds == 17 * 60
    utc = real_otp.plan(query(when="2026-10-26T02:25:00Z"))
    assert utc.itineraries[0].end == first.end
    for preference in ("cheapest", "fewest_transfers", "least_walking"):
        result = real_otp.plan(query(preference=preference))
        assert result.itineraries[0].fare_inr == (30 if preference == "cheapest" else 50)


@pytest.mark.otp
@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"when": "2026-10-27T07:55:00+05:30"}, "no_route"),
        ({"when": "2026-10-26T08:40:00+05:30"}, "no_route"),
        ({"destination": {"latitude": 0, "longitude": 0}}, "no_route"),
        ({"when": "2026-10-27T00:00:00+05:30", "destination": {"stop_id": "B"}}, "ok"),
        ({"when": "2026-10-28T00:00:00+05:30", "destination": {"stop_id": "B"}}, "no_route"),
        ({"arrive_by": True, "when": "2026-10-26T08:18:00+05:30"}, "ok"),
        ({"arrive_by": True, "when": "2026-10-26T08:10:00+05:30"}, "no_route"),
        (
            {
                "origin": {"stop_id": "D"},
                "destination": {"stop_id": "A"},
                "when": "2026-10-26T08:15:00+05:30",
            },
            "ok",
        ),
        ({"modes": ["SUBWAY", "WALK"]}, "no_route"),
    ],
)
def test_real_calendar_direction_missed_connection_and_arrive_by(real_otp, changes, expected):
    result = real_otp.plan(query(**changes))
    assert result.status == expected
    for itinerary in result.itineraries:
        if changes.get("arrive_by"):
            assert itinerary.end <= query(**changes).when
        if changes.get("origin") == {"stop_id": "D"}:
            assert all(leg.direction_id == "1" for leg in itinerary.legs if leg.mode != "WALK")


@pytest.mark.otp
def test_real_walking_bounds_and_inaccessible_vehicle(real_otp):
    unrestricted = real_otp.plan(query(wheelchair=False))
    assert unrestricted.itineraries[0].fare_inr is None
    assert unrestricted.itineraries[0].legs[0].trip_id.endswith(":STAIR_OUT")
    accessible = real_otp.plan(query(max_walk_m=0))
    assert accessible.itineraries[0].fare_inr == 50 and accessible.itineraries[0].walking_m == 0
    walking = real_otp.plan(query(modes=["WALK"], transit_required=False, max_walk_m=10000))
    assert walking.itineraries[0].fare_status == "free_walking"
    assert walking.itineraries[0].walking_m > 3000


@pytest.mark.otp
def test_real_bounded_four_concurrent_load(real_otp):
    import math
    import time
    from concurrent.futures import ThreadPoolExecutor

    # Two warmups exclude graph loading/JIT from this steady-state target.
    real_otp.plan(query())
    real_otp.plan(query())

    def run(_):
        started = time.perf_counter()
        result = real_otp.plan(query())
        assert result.status == "ok"
        return time.perf_counter() - started

    with ThreadPoolExecutor(max_workers=4) as pool:
        durations = list(pool.map(run, range(40)))
    assert sorted(durations)[math.ceil(0.95 * len(durations)) - 1] < 2
