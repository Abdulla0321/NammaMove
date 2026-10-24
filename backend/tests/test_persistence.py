from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models import (
    AuditEvent,
    Commuter,
    DisruptionEvidence,
    JourneyRecord,
    Notification,
    Stop,
    UserPreference,
    utcnow,
)
from conftest import auth, make_profile
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_profile_journey_ownership_and_delete(secured):
    app, client, engine, token, *_ = secured
    mine, other = token(), token(subject=uuid4())
    profile = make_profile(client, mine)
    make_profile(client, other)
    assert (
        client.put(
            "/v1/me/preferences",
            headers=auth(mine),
            json={"step_free": True, "max_walk_minutes": 15},
        ).status_code
        == 200
    )
    result = client.post(
        "/v1/journeys",
        headers=auth(mine),
        json={"origin": "Electronic City", "destination": "MG Road"},
    )
    assert result.status_code == 201
    saved = result.json()
    assert saved["data_mode"] == "simulation"
    assert saved["itinerary"]["estimatedMinutes"] == 76
    assert client.get("/v1/journeys", headers=auth(other)).json() == []
    assert client.get("/v1/journeys/" + saved["id"], headers=auth(other)).status_code == 404
    assert client.delete("/v1/journeys/" + saved["id"], headers=auth(other)).status_code == 404
    assert client.get("/v1/journeys/" + saved["id"], headers=auth(mine)).status_code == 200
    assert client.delete("/v1/me", headers=auth(mine)).status_code == 204
    with Session(engine) as db:
        from uuid import UUID

        assert db.get(Commuter, UUID(profile["id"])) is None
        assert db.scalar(select(func.count()).select_from(JourneyRecord)) == 0
        assert db.scalar(select(func.count()).select_from(UserPreference)) == 0


def test_catalog_validation_mode_separation_and_duplicate_rollback(secured):
    app, client, engine, token, *_ = secured
    admin = token(role="admin")
    make_profile(client, admin)
    operator = client.post(
        "/v1/operators", headers=auth(admin), json={"name": "Synthetic", "data_mode": "simulation"}
    ).json()
    stop = {
        "operator_id": operator["id"],
        "external_id": "test-stop",
        "name": "Synthetic Stop",
        "latitude": 12.97,
        "longitude": 77.59,
    }
    assert (
        client.post("/v1/stops", headers=auth(admin), json={**stop, "latitude": 91}).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/stops", headers=auth(admin), json={**stop, "operator_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert client.post("/v1/stops", headers=auth(admin), json=stop).status_code == 201
    assert client.post("/v1/stops", headers=auth(admin), json=stop).status_code == 409
    assert client.get("/v1/stops?data_mode=live", headers=auth(admin)).json() == []
    assert len(client.get("/v1/stops", headers=auth(admin)).json()) == 1
    assert client.get("/v1/stops?limit=10000", headers=auth(admin)).status_code == 422
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Stop)) == 1
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 2


def test_untrusted_reports_and_independent_moderator_evidence(secured):
    app, client, engine, token, *_ = secured
    user = token()
    mod = token(subject=uuid4(), role="moderator")
    make_profile(client, user)
    make_profile(client, mod)
    report = {
        "kind": "road_closure",
        "summary": "Synthetic closure report",
        "data_mode": "simulation",
    }
    assert (
        client.post(
            "/v1/disruptions", headers=auth(user), json={**report, "verified": True}
        ).status_code
        == 422
    )
    result = client.post("/v1/disruptions", headers=auth(user), json=report)
    assert result.status_code == 201
    saved = result.json()
    assert saved["verification"] == "unverified" and saved["confidence"] == 0
    evidence = {
        "decision": "verified",
        "evidence_source": "synthetic operator confirmation",
        "confidence": 0.95,
        "expires_at": (utcnow() + timedelta(hours=1)).isoformat(),
    }
    url = "/v1/disruptions/" + saved["id"] + "/verification"
    assert client.post(url, headers=auth(user), json=evidence).status_code == 403
    assert client.post(url, headers=auth(token(role="moderator")), json=evidence).status_code == 403
    assert (
        client.post(
            url,
            headers=auth(mod),
            json={**evidence, "expires_at": (utcnow() - timedelta(hours=1)).isoformat()},
        ).status_code
        == 422
    )
    assert (
        client.post(url, headers=auth(mod), json={**evidence, "confidence": 1.1}).status_code == 422
    )
    assert client.post(url, headers=auth(mod), json=evidence).json()["verification"] == "verified"
    other = token(subject=uuid4())
    assert client.get("/v1/disruptions/" + saved["id"], headers=auth(other)).status_code == 404
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DisruptionEvidence)) == 1
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 1
    # Persistent verification cannot silently change the Phase 00 sample graph.
    assert (
        client.post(
            "/journeys/plan", json={"origin": "Electronic City", "destination": "MG Road"}
        ).json()["estimatedMinutes"]
        == 76
    )


def test_notification_ownership_and_idempotent_read(secured):
    app, client, engine, token, keys, private, user = secured
    make_profile(client, token())
    with Session(engine) as db:
        notification = Notification(commuter_id=user, message="Synthetic test alert")
        db.add(notification)
        db.commit()
        notification_id = notification.id
    url = "/v1/notifications/" + str(notification_id) + "/read"
    assert client.get("/v1/notifications", headers=auth(token(subject=uuid4()))).json() == []
    assert client.post(url, headers=auth(token(subject=uuid4()))).status_code == 404
    first = client.post(url, headers=auth(token()))
    assert first.status_code == 200
    second = client.post(url, headers=auth(token()))
    assert datetime.fromisoformat(second.json()["read_at"]).replace(
        tzinfo=timezone.utc
    ) == datetime.fromisoformat(first.json()["read_at"]).replace(tzinfo=timezone.utc)


def test_failure_is_sanitized_and_transaction_rolled_back(secured):
    app, client, engine, token, *_ = secured
    from sqlalchemy import event

    def fail_commit(session):
        raise RuntimeError("password-should-never-be-returned")

    event.listen(Session, "before_commit", fail_commit)
    try:
        result = client.put("/v1/me", headers=auth(token()), json={"display_name": "Private Name"})
    finally:
        event.remove(Session, "before_commit", fail_commit)
    assert result.status_code == 500
    assert "password" not in result.text
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Commuter)) == 0


def test_private_input_does_not_leak_in_errors_or_logs(secured, capsys):
    app, client, engine, token, *_ = secured
    secret = "PRIVATE_LOCATION_DO_NOT_LOG"
    result = client.put(
        "/v1/me?secret=" + secret,
        headers=auth(token()),
        json={"display_name": "", "unexpected": secret},
    )
    assert result.status_code == 422
    assert secret not in result.text
    assert len(result.headers["x-request-id"]) == 36
    assert result.headers["cache-control"] == "no-store"
    assert secret not in capsys.readouterr().err
    assert client.put("/v1/me", headers=auth(token()), content="x" * 65537).status_code == 413
