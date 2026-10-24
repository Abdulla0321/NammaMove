from datetime import timedelta

from app.maintenance import retain
from app.models import AuditEvent, Disruption, JourneyRecord, Notification, utcnow
from conftest import auth, make_profile
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_retention_dry_run_then_apply_preserves_recent_records(secured):
    app, client, engine, token, keys, private, user = secured
    make_profile(client, token())
    with Session(engine) as db:
        old = utcnow() - timedelta(days=100)
        db.add_all(
            [
                JourneyRecord(
                    commuter_id=user,
                    origin="Synthetic A",
                    destination="Synthetic B",
                    itinerary={},
                    created_at=old,
                ),
                JourneyRecord(
                    commuter_id=user, origin="Synthetic C", destination="Synthetic D", itinerary={}
                ),
                Notification(commuter_id=user, message="old synthetic", created_at=old),
                AuditEvent(actor_id=user, action="synthetic", created_at=old),
                Disruption(reporter_id=user, kind="other", summary="old synthetic", created_at=old),
            ]
        )
        db.commit()
        counts = retain(db)
        assert counts == {"journeys": 1, "notifications": 1, "audit_events": 1, "disruptions": 1}
        assert db.scalar(select(func.count()).select_from(JourneyRecord)) == 2
        assert retain(db, apply=True) == counts
        db.commit()
        assert db.scalar(select(func.count()).select_from(JourneyRecord)) == 1
        assert db.scalar(select(func.count()).select_from(Disruption)) == 0


def test_local_deletion_anonymizes_report_and_audit(secured):
    app, client, engine, token, keys, private, user = secured
    make_profile(client, token())
    with Session(engine) as db:
        report = Disruption(reporter_id=user, kind="other", summary="Private reporter text")
        event = AuditEvent(actor_id=user, action="synthetic")
        db.add_all([report, event])
        db.commit()
        report_id, event_id = report.id, event.id
    assert client.delete("/v1/me", headers=auth(token())).status_code == 204
    with Session(engine) as db:
        saved = db.get(Disruption, report_id)
        assert saved.reporter_id is None
        assert saved.summary == "[removed on local profile deletion]"
        assert db.get(AuditEvent, event_id).actor_id is None


def test_database_failure_is_503_without_details(secured):
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError

    app, client, engine, token, *_ = secured

    def fail_query(*args):
        raise OperationalError("sensitive-statement", {}, RuntimeError("private-database-password"))

    event.listen(engine, "before_cursor_execute", fail_query)
    try:
        response = client.get("/v1/me", headers=auth(token()))
    finally:
        event.remove(engine, "before_cursor_execute", fail_query)
    assert response.status_code == 503
    assert "sensitive" not in response.text and "private" not in response.text
    assert client.get("/health").status_code == 200
    make_profile(client, token())


def test_retention_preserves_referenced_cancellation_evidence(secured):
    from app.models import DisruptionEvidence, Operator, Vehicle

    app, client, engine, token, keys, private, user = secured
    make_profile(client, token())
    old = utcnow() - timedelta(days=100)
    with Session(engine) as db:
        operator = Operator(name="Synthetic operator")
        report = Disruption(
            reporter_id=user,
            kind="other",
            summary="Synthetic cancellation authority",
            created_at=old,
            verification="verified",
            confidence=0.9,
            verified_at=old,
            expires_at=old + timedelta(days=1),
        )
        db.add_all([operator, report])
        db.flush()
        evidence = DisruptionEvidence(
            disruption_id=report.id,
            actor_id=user,
            source="synthetic operator reference",
            decision="verified",
        )
        db.add(evidence)
        db.flush()
        db.add(
            Vehicle(
                operator_id=operator.id,
                external_id="synthetic-vehicle",
                service_status="confirmed_cancelled",
                cancellation_evidence_id=evidence.id,
            )
        )
        db.commit()
        assert retain(db, apply=True)["disruptions"] == 0
        db.commit()
        assert db.get(DisruptionEvidence, evidence.id) is not None


def test_location_consent_requires_explicit_boolean(secured):
    app, client, engine, token, *_ = secured
    response = client.put(
        "/v1/me",
        headers=auth(token()),
        json={"display_name": "Synthetic", "location_consent": "yes"},
    )
    assert response.status_code == 422
