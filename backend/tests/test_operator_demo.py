from importlib.util import find_spec

from app.operator_demo import create_demo
from fastapi.testclient import TestClient

KEY = {"X-Demo-Key": "console-test"}
PREFIX = "/demo/v1"


def test_demo_corridor_and_credentials():
    with TestClient(create_demo("console-test")) as client:
        assert "NammaMove Operator Console" in client.get("/").text
        assert client.get(f"{PREFIX}/state").status_code == 401
        assert client.get(f"{PREFIX}/fleet/cab-01/credential").status_code == 401
        response = client.post(
            f"{PREFIX}/routes",
            headers=KEY,
            json={"origin": " whitefield ", "destination": "KSR Bengaluru"},
        )
        assert response.status_code == 200
        assert {route["id"] for route in response.json()} == {"bus", "cab-metro", "walk-metro"}
        assert (
            client.post(
                f"{PREFIX}/routes",
                headers=KEY,
                json={"origin": "Other", "destination": "KSR Bengaluru"},
            ).status_code
            == 404
        )


def test_multileg_reconciliation_rejects_wrong_vehicle_forgery_and_replay():
    with TestClient(create_demo("console-test")) as client:
        booked = client.post(f"{PREFIX}/journeys", headers=KEY, json={"route_id": "cab-metro"})
        assert booked.status_code == 201
        journey = booked.json()
        assert client.get(f"{PREFIX}/state", headers=KEY).json()["held_inr"] == 90

        def scanner(vehicle):
            credential = client.get(f"{PREFIX}/fleet/{vehicle}/credential", headers=KEY).json()
            return {"X-Demo-Key": credential["scanner_key"]}

        for index, vehicle in enumerate(("cab-01", "metro-01")):
            leg = {"journey_id": journey["id"], "leg_index": index}
            path = f"{PREFIX}/fleet/{vehicle}"
            credentials = scanner(vehicle)
            assert (
                client.post(f"{path}/accept", headers=scanner("bus-01"), json=leg).status_code
                == 401
            )
            assert (
                client.post(
                    f"{PREFIX}/fleet/bus-01/accept", headers=scanner("bus-01"), json=leg
                ).status_code
                == 409
            )
            accepted = client.post(f"{path}/accept", headers=credentials, json=leg)
            assert accepted.status_code == 200
            assert "ticket" not in accepted.json()
            ticket = client.get(f"{PREFIX}/state", headers=KEY).json()["journey"]["ticket"]
            qr = client.post(f"{PREFIX}/ticket/qr", headers=KEY, json=leg)
            if find_spec("qrcode") is None:
                assert qr.status_code == 503
            else:
                assert qr.status_code == 200
                assert qr.headers["content-type"] == "image/svg+xml"
                assert qr.headers["cache-control"] == "no-store"
                assert "<svg" in qr.text
            assert (
                client.post(
                    f"{path}/scan",
                    headers=credentials,
                    json={**leg, "ticket": "forged", "action": "board"},
                ).status_code
                == 409
            )
            scan = {**leg, "ticket": ticket, "action": "exit"}
            assert client.post(f"{path}/scan", headers=credentials, json=scan).status_code == 409
            before = client.get(f"{PREFIX}/state", headers=KEY).json()
            assert (
                client.post(
                    f"{path}/scan", headers=credentials, json={**scan, "action": "board"}
                ).status_code
                == 200
            )
            assert (
                client.get(f"{PREFIX}/state", headers=KEY).json()["balance_inr"]
                == before["balance_inr"]
            )
            assert client.post(f"{path}/scan", headers=credentials, json=scan).status_code == 200
            assert client.post(f"{path}/scan", headers=credentials, json=scan).status_code == 409

        finish = client.post(
            f"{PREFIX}/walk", headers=KEY, json={"journey_id": journey["id"], "leg_index": 2}
        )
        assert finish.json()["stage"] == "complete"
        state = client.get(f"{PREFIX}/state", headers=KEY).json()
        assert state["balance_inr"] == 660
        assert state["held_inr"] == 0
        assert state["operator_credits_inr"] == {"cab-01": 30, "metro-01": 60, "bus-01": 0}
        assert len(state["ledger"]) == 2
