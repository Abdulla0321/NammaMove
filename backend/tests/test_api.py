from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_and_simulated_network():
    assert client.get("/health").json() == {"status": "ok", "mode": "simulation"}
    network = client.get("/network").json()
    assert network["mode"] == "simulation"
    assert len(network["edges"]) == 7
    assert "Electronic City" in network["stops"]


def test_plan_and_verified_disruption():
    request = {"origin": "Electronic City", "destination": "MG Road"}
    baseline = client.post("/journeys/plan", json=request)
    assert baseline.status_code == 200
    assert baseline.json()["estimatedMinutes"] == 76
    assert baseline.json()["fare"] == 70
    assert "simulated" in baseline.json()["dataNotice"]
    request["incidents"] = [
        {"id": "closure", "affected_edges": ["bus-2"], "verified": True, "blocked": True}
    ]
    diverted = client.post("/journeys/plan", json=request)
    assert diverted.status_code == 200
    assert [leg["id"] for leg in diverted.json()["legs"]] == ["bus-3", "bus-4"]
    request["incidents"][0]["verified"] = False
    assert client.post("/journeys/plan", json=request).json()["estimatedMinutes"] == 76


def test_invalid_and_unreachable_requests():
    assert (
        client.post("/journeys/plan", json={"origin": "", "destination": "MG Road"}).status_code
        == 422
    )
    assert (
        client.post(
            "/journeys/plan", json={"origin": "MG Road", "destination": "Electronic City"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/journeys/plan",
            json={
                "origin": "A",
                "destination": "B",
                "incidents": [{"id": "bad", "affected_edges": [], "delay_minutes": -1}],
            },
        ).status_code
        == 422
    )


def test_status_evidence_and_freshness_boundary():
    assert client.get("/services/status").json()["serviceStatus"] == "uncertain"
    assert client.get("/services/status?last_seen_seconds=300").json()["feedStatus"] == "live"
    assert client.get("/services/status?last_seen_seconds=301").json()["feedStatus"] == "stale"
    assert (
        client.get("/services/status?operator_cancelled=true").json()["serviceStatus"]
        == "confirmed_cancelled"
    )
    assert client.get("/services/status?last_seen_seconds=-1").status_code == 422
