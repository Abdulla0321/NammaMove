"""Portable tests use recorded actual OTP synthetic response; no real-provider pass claim."""

import copy
import json
from pathlib import Path

import httpx
import pytest
from app.routing.build import seal, verify_release
from app.routing.contracts import GraphManifest, PlanRequest
from app.routing.fixture import make_fixture
from app.routing.provider import OTPProvider
from conftest import auth
from fastapi import HTTPException

RECORDED = json.loads((Path(__file__).parent / "fixtures/otp/plan.json").read_text())


@pytest.fixture
def routing_manifest(tmp_path):
    raw = make_fixture(tmp_path / "inputs")
    raw["graph_sha256"] = "0" * 64
    return GraphManifest.model_validate(raw)


def query(**changes):
    values = {
        "origin": {"stop_id": "A"},
        "destination": {"stop_id": "D"},
        "when": "2026-10-26T07:55:00+05:30",
        "wheelchair": True,
        "transit_required": True,
        "max_walk_m": 500,
    }
    values.update(changes)
    return PlanRequest(**values)


def provider(manifest, response=None):
    return OTPProvider(
        "http://localhost:18081",
        manifest,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=RECORDED if response is None else response)
        ),
    )


def test_deterministic_authored_inputs_and_tamper_rejection(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert make_fixture(a) == make_fixture(b)
    # This checks byte integrity only; actual Java graph acceptance is in OTP tests.
    (a / "graph.obj").write_bytes(b"portable artifact placeholder")
    first = seal(a)
    assert verify_release(a) == first
    with pytest.raises(ValueError, match="already sealed"):
        seal(a)
    (a / "synthetic.gtfs.zip").write_bytes(b"bad feed")
    with pytest.raises(ValueError, match="checksum"):
        verify_release(a)
    assert json.loads((a / "manifest.json").read_text())["graph_sha256"] == first.graph_sha256


@pytest.mark.parametrize(
    "preference,expected",
    [("fastest", 30), ("cheapest", 30), ("fewest_transfers", 50), ("least_walking", 50)],
)
def test_preferences_and_physical_eta(routing_manifest, preference, expected):
    result = provider(routing_manifest).plan(query(preference=preference))
    assert result.itineraries[0].fare_inr == expected
    assert result.data_mode == "simulation" and result.service_status == "unknown"
    for itinerary in result.itineraries:
        assert itinerary.duration_seconds == (itinerary.end - itinerary.start).total_seconds()
        assert itinerary.fare_status == "known_synthetic_per_boarding"
        assert (
            itinerary.elapsed_from_requested_departure_seconds
            == itinerary.duration_seconds + itinerary.initial_wait_seconds
        )
    assert result.ranking_scope == "bounded_provider_candidates"


@pytest.mark.parametrize("changes", [{"max_walk_m": 0}, {"max_transfers": 0}, {"modes": ["BUS"]}])
def test_constraints_filter_infeasible_candidates(routing_manifest, changes):
    result = provider(routing_manifest).plan(query(**changes))
    assert len(result.itineraries) == 1 and result.itineraries[0].fare_inr == 50


def test_unknown_fare_is_not_free_and_accessibility_unknown_fails_closed(routing_manifest):
    manifest = routing_manifest.model_copy(update={"route_fares_inr": {}})
    result = provider(manifest).plan(query())
    assert all(i.fare_inr is None and i.fare_status == "unknown" for i in result.itineraries)
    raw = copy.deepcopy(RECORDED)
    for edge in raw["data"]["planConnection"]["edges"]:
        for leg in edge["node"]["legs"]:
            if leg["trip"]:
                leg["trip"]["wheelchairAccessible"] = "NO_INFORMATION"
    assert provider(manifest, raw).plan(query()).status == "no_route"


@pytest.mark.parametrize(
    "failure", ["json", "graphql", "http", "timeout", "oversized", "unknown_error"]
)
def test_provider_failure_sanitized(routing_manifest, failure):
    def transport(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private coordinates and token")
        if failure == "json":
            return httpx.Response(200, text="bad")
        if failure == "http":
            return httpx.Response(503, text="private")
        if failure == "oversized":
            return httpx.Response(200, content=b"x" * 2_000_001)
        if failure == "unknown_error":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "planConnection": {"edges": [], "routingErrors": [{"code": "SYSTEM_ERROR"}]}
                    }
                },
            )
        return httpx.Response(200, json={"errors": [{"message": "private"}]})

    p = OTPProvider("http://localhost", routing_manifest, transport=httpx.MockTransport(transport))
    with pytest.raises(HTTPException) as error:
        p.plan(query())
    assert error.value.status_code == 503 and "private" not in error.value.detail


@pytest.mark.parametrize("kind", ["overlap", "wrong_endpoint", "backwards", "transfer_slack"])
def test_invalid_provider_schedule_rejected(routing_manifest, kind):
    raw = copy.deepcopy(RECORDED)
    node = raw["data"]["planConnection"]["edges"][0]["node"]
    if kind == "overlap":
        node["legs"][1]["start"]["scheduledTime"] = "2026-10-26T08:04:00+05:30"
    if kind == "wrong_endpoint":
        node["legs"][0]["from"]["lat"] = 0
    if kind == "backwards":
        node["end"] = "2026-10-26T07:00:00+05:30"
    if kind == "transfer_slack":
        node["legs"][2]["start"]["scheduledTime"] = "2026-10-26T08:08:30+05:30"
    with pytest.raises(HTTPException) as error:
        provider(routing_manifest, raw).plan(query())
    assert error.value.status_code == 503


def test_graph_version_unknown_stop_and_capacity(routing_manifest):
    p = provider(routing_manifest)
    with pytest.raises(HTTPException) as e:
        p.plan(query(graph_id="f" * 64))
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:
        p.plan(query(origin={"stop_id": "UNKNOWN"}))
    assert e.value.status_code == 422
    for _ in range(4):
        assert p.slots.acquire(blocking=False)
    with pytest.raises(HTTPException) as e:
        p.plan(query())
    assert e.value.status_code == 503
    for _ in range(4):
        p.slots.release()
    assert p.plan(query()).status == "ok"
    assert p.plan(query(destination={"stop_id": "A"})).reason == "same_location"


@pytest.mark.parametrize(
    "changes",
    [
        {"when": "2026-10-26T08:00:00"},
        {"origin": {"latitude": 91, "longitude": 0}},
        {"max_walk_m": -1},
        {"operator_cancelled": True},
        {"modes": ["BUS", "BUS"]},
    ],
)
def test_request_contract_rejects_unsafe_or_invalid_input(changes):
    with pytest.raises(ValueError):
        query(**changes)


def test_protected_api_and_legacy_preservation(secured, routing_manifest):
    application, client, _, token, *_ = secured
    payload = query().model_dump(mode="json")
    assert client.post("/v1/routing/plan", json=payload).status_code == 401
    assert client.post("/v1/routing/plan", json=payload, headers=auth(token())).status_code == 503
    application.state.routing_provider = provider(routing_manifest)
    result = client.post("/v1/routing/plan", json=payload, headers=auth(token()))
    assert result.status_code == 200 and result.json()["confidence"] == "authored_fixture_only"
    assert client.get("/health").status_code == 200
    application.state.settings.simulation_enabled = False
    assert client.post("/v1/routing/plan", json=payload, headers=auth(token())).status_code == 503


def test_arrival_deadline_padding_never_returns_post_deadline(routing_manifest):
    p = provider(routing_manifest)
    result = p.plan(query(arrive_by=True, when="2026-10-26T08:18:00+05:30"))
    assert len(result.itineraries) == 1 and result.itineraries[0].fare_inr == 30
    assert result.itineraries[0].end <= query(arrive_by=True, when="2026-10-26T08:18:00+05:30").when


@pytest.mark.parametrize("field", ["stops", "route_fares_inr", "service_end"])
def test_sealed_metadata_must_match_verified_source(tmp_path, field):
    make_fixture(tmp_path / "release")
    folder = tmp_path / "release"
    (folder / "graph.obj").write_bytes(b"portable byte-integrity artifact")
    seal(folder)
    path = folder / "manifest.json"
    raw = json.loads(path.read_text())
    if field == "stops":
        raw[field]["A"]["latitude"] = 0
    elif field == "route_fares_inr":
        raw[field]["BUS"] = 0
    else:
        raw[field] = "2030-01-01"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="differs from source"):
        verify_release(folder)
