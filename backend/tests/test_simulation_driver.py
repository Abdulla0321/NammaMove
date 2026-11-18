from app.simulation.api import create_demo
from fastapi.testclient import TestClient

CONSOLE = {"X-Demo-Key": "console-test"}
PARTNER = {"X-Demo-Key": "partner-test"}
API = "/demo/v1"


def test_assigned_staff_validates_board_and_exit_without_console_key():
    now = 100.0

    def clock() -> float:
        return now

    app = create_demo(
        "console-test",
        clock=clock,
        driver_passwords={"bus-01": "bus-test"},
        integration_key="partner-test",
    )
    with TestClient(app) as client:
        assert client.get("/driver").status_code == 200
        itinerary = {"origin": "Whitefield", "destination": "KSR Bengaluru"}
        assert client.post(f"{API}/routes", headers=PARTNER, json=itinerary).status_code == 200
        assert client.get(f"{API}/state", headers=PARTNER).status_code == 401
        assert client.get(f"{API}/fleet/bus-01/credential", headers=PARTNER).status_code == 401
        assert (
            client.post(
                f"{API}/staff/login", json={"username": "bmtc-driver", "password": "incorrect"}
            ).status_code
            == 401
        )
        login = client.post(
            f"{API}/staff/login", json={"username": "bmtc-driver", "password": "bus-test"}
        )
        assert login.status_code == 200
        assert login.headers["Cache-Control"] == "no-store"
        staff = {"X-Staff-Token": login.json()["session"]}
        assert client.get(f"{API}/fleet/cab-01/assignment", headers=staff).status_code == 401
        booking = client.post(f"{API}/journeys", headers=CONSOLE, json={"route_id": "bus"})
        assert booking.status_code == 201
        active = client.get(f"{API}/fleet/bus-01/assignment", headers=staff).json()["assignment"]
        assert "ticket" not in active
        payload = {"journey_id": active["journey_id"], "leg_index": active["leg_index"]}
        assert (
            client.post(f"{API}/fleet/bus-01/accept", headers=staff, json=payload).status_code
            == 200
        )
        state = client.get(f"{API}/state", headers=CONSOLE).json()
        payload["ticket"] = state["journey"]["ticket"]
        endpoint = f"{API}/fleet/bus-01/scan"
        assert (
            client.post(endpoint, headers=staff, json={**payload, "action": "board"}).status_code
            == 200
        )
        assert client.get(f"{API}/state", headers=CONSOLE).json()["balance_inr"] == 750
        assert (
            client.post(endpoint, headers=staff, json={**payload, "action": "exit"}).status_code
            == 200
        )
        assert (
            client.post(endpoint, headers=staff, json={**payload, "action": "exit"}).status_code
            == 409
        )
        assert client.get(f"{API}/state", headers=CONSOLE).json()["balance_inr"] == 720
        now += 1800
        assert client.get(f"{API}/fleet/bus-01/assignment", headers=staff).status_code == 401
