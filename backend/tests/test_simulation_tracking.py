from pathlib import Path

import httpx
import pytest
from app.simulation.api import create_demo
from app.simulation.mapbox import Mapbox
from app.simulation.tracking import SimulationStore
from fastapi.testclient import TestClient

KEY = {"X-Demo-Key": "test-console"}
API = "/demo/v1"


def test_concurrent_simulations_and_restart_replay(tmp_path: Path) -> None:
    path = tmp_path / "simulations.sqlite3"
    store = SimulationStore(path)
    store.initialize()
    now = 100.0

    def wall_clock() -> float:
        return now

    def directions(request: httpx.Request) -> httpx.Response:
        assert request.url.params["annotations"] == "duration"
        return httpx.Response(
            200,
            json={
                "code": "Ok",
                "routes": [
                    {
                        "duration": 10,
                        "distance": 1000,
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[77.6, 13], [77.61, 13], [77.61, 13.01]],
                        },
                        "legs": [{"annotation": {"duration": [8, 2]}}],
                    }
                ],
            },
        )

    transport = httpx.MockTransport(directions)
    mapbox = Mapbox(
        "map-token", httpx.Client(transport=transport, base_url="https://api.mapbox.com")
    )
    app = create_demo("test-console", mapbox=mapbox, store=store, wall_clock=wall_clock)
    with TestClient(app) as client:
        plan = client.post(
            f"{API}/map/routes",
            headers=KEY,
            json={"origin": "Whitefield", "destination": "KSR Bengaluru"},
        ).json()
        payload = {"plan_id": plan["plan_id"], "route_id": "cab-direct", "speed": 1}
        first = client.post(f"{API}/simulations", headers=KEY, json=payload)
        second = client.post(f"{API}/simulations", headers=KEY, json={**payload, "speed": 2})
        assert first.status_code == second.status_code == 201
        first_id, second_id = first.json()["id"], second.json()["id"]
        assert first_id != second_id
        assert client.get(f"{API}/simulations/{first_id}/position").status_code == 401
        now += 4
        current = client.get(f"{API}/simulations/{first_id}/position", headers=KEY).json()
        quicker = client.get(f"{API}/simulations/{second_id}/position", headers=KEY).json()
        assert current["id"] == f"{first_id}:4"
        assert current["position"] == pytest.approx([77.605, 13])
        assert quicker["position"] == [77.61, 13]
        assert quicker["tick"] == 8

    now += 50
    restarted = create_demo("test-console", store=SimulationStore(path), wall_clock=wall_clock)
    with TestClient(restarted) as client:
        assert set(client.get(f"{API}/simulations", headers=KEY).json()) == {first_id, second_id}
        uri = f"{API}/simulations/{first_id}/positions"
        initial = client.get(uri, headers=KEY, params={"limit": 5}).json()
        page = client.get(uri, headers=KEY, params={"after": initial["next_after"]}).json()
        samples = initial["samples"] + page["samples"]
        assert [sample["tick"] for sample in samples] == list(range(11))
        assert samples[4] == current
        assert samples[-1]["phase"] == "complete"
        assert samples[-1]["position"] == [77.61, 13.01]
        assert client.get(uri, headers=KEY, params={"after": 10}).json() == {
            "samples": [],
            "next_after": 10,
        }
