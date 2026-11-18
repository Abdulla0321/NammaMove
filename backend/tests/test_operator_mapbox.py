from collections.abc import Callable

import httpx
from app.operator_demo import create_demo
from app.simulation.mapbox import Mapbox, Track
from fastapi.testclient import TestClient

KEY = {"X-Demo-Key": "test-console"}
API = "/demo/v1"


def test_mapbox_routes_follow_real_geometry_contract_and_simulated_clock():
    now = 500.0
    requests: list[str] = []

    def provider(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        params = request.url.params
        assert params["access_token"] == "test-token"
        if request.url.path == "/search/geocode/v6/forward":
            assert params["country"] == "IN"
            assert "bbox" in params
            return httpx.Response(
                200,
                json={"features": [{"geometry": {"type": "Point", "coordinates": [77.8, 12.99]}}]},
            )
        assert params["geometries"] == "geojson"
        left, right = request.url.path.rsplit("/", 1)[1].split(";")
        start, end = [float(x) for x in left.split(",")], [float(x) for x in right.split(",")]
        corner = [start[0], end[1]]
        return httpx.Response(
            200,
            json={
                "code": "Ok",
                "routes": [
                    {
                        "duration": 90,
                        "distance": 10000,
                        "geometry": {"type": "LineString", "coordinates": [start, corner, end]},
                    }
                ],
            },
        )

    def clock() -> float:
        return now

    with map_api(provider, clock) as client:
        response = client.post(
            f"{API}/map/routes",
            headers=KEY,
            json={"origin": "Test Lane", "destination": "KSR Bengaluru"},
        )
        assert response.status_code == 200
        options = response.json()
        assert {route["id"] for route in options["routes"]} == {
            "cab-direct",
            "cab-metro",
            "walk-metro",
            "bus",
        }
        assert any("walking" in path for path in requests)
        assert any("driving-traffic" in path for path in requests)
        assert (
            client.post(f"{API}/journeys", headers=KEY, json={"route_id": "cab-direct"}).status_code
            == 409
        )
        booked = client.post(
            f"{API}/journeys",
            headers=KEY,
            json={"route_id": "cab-direct", "plan_id": options["plan_id"]},
        )
        assert booked.status_code == 201
        journey = booked.json()
        path = journey["route"]["legs"][0]["path"]
        assert len(path) == 3
        progress = {"journey_id": journey["id"], "leg_index": 0}
        fleet = f"{API}/fleet/cab-01"
        scanner = client.get(f"{fleet}/credential", headers=KEY).json()
        credentials = {"X-Demo-Key": scanner["scanner_key"]}
        assert client.get(f"{API}/map/progress", headers=KEY).json()["phase"] == "waiting"
        assert client.post(f"{fleet}/accept", headers=credentials, json=progress).status_code == 200
        ticket = client.get(f"{API}/state", headers=KEY).json()["journey"]["ticket"]
        payload = {**progress, "ticket": ticket}
        assert (
            client.post(
                f"{fleet}/scan", headers=credentials, json={**payload, "action": "board"}
            ).status_code
            == 200
        )
        now += 1.5
        motion = client.get(f"{API}/map/progress", headers=KEY).json()
        assert motion["phase"] == "moving"
        assert motion["progress"] == 0.5
        assert motion["position"] == list(
            Track.build([tuple(point) for point in path]).position(0.5)
        )
        assert (
            client.post(
                f"{fleet}/scan", headers=credentials, json={**payload, "action": "exit"}
            ).status_code
            == 409
        )
        assert client.get(f"{API}/state", headers=KEY).json()["balance_inr"] == 750
        now += 1.5
        motion = client.get(f"{API}/map/progress", headers=KEY).json()
        assert motion["position"] == path[-1]
        assert motion["phase"] == "arrived"
        assert (
            client.post(
                f"{fleet}/scan", headers=credentials, json={**payload, "action": "exit"}
            ).status_code
            == 200
        )
        assert client.get(f"{API}/state", headers=KEY).json()["balance_inr"] == 590


def test_mapbox_token_rejection_does_not_echo_token_or_use_fixture_routes():
    def denied(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="test-token")

    with map_api(denied, lambda: 0) as client:
        response = client.post(
            f"{API}/map/routes",
            headers=KEY,
            json={"origin": "Whitefield", "destination": "KSR Bengaluru"},
        )
        assert response.status_code == 503
        assert "test-token" not in response.text


def map_api(
    provider: Callable[[httpx.Request], httpx.Response], clock: Callable[[], float]
) -> TestClient:
    http = httpx.Client(transport=httpx.MockTransport(provider), base_url="https://api.mapbox.com")
    return TestClient(create_demo("test-console", mapbox=Mapbox("test-token", http), clock=clock))
