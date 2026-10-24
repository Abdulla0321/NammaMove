"""Explicit maintenance-owner CLI. Dry-run by default; never invoked on startup."""

import argparse
from datetime import timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from .config import Settings
from .database import Database
from .models import (
    AuditEvent,
    Disruption,
    DisruptionEvidence,
    JourneyRecord,
    Notification,
    Vehicle,
    utcnow,
)


def retain(db: Session, *, apply: bool = False) -> dict[str, int]:
    now = utcnow()
    # Operational evidence still referenced by a cancellation is not removed.
    referenced = select(DisruptionEvidence.disruption_id).join(
        Vehicle, Vehicle.cancellation_evidence_id == DisruptionEvidence.id
    )
    expired_reports = (
        ((Disruption.verification != "verified") | (Disruption.expires_at < now))
        & (Disruption.created_at < now - timedelta(days=90))
        & Disruption.id.not_in(referenced)
    )
    policies = [
        (JourneyRecord, JourneyRecord.created_at < now - timedelta(days=30)),
        (Notification, Notification.created_at < now - timedelta(days=30)),
        (AuditEvent, AuditEvent.created_at < now - timedelta(days=90)),
        (Disruption, expired_reports),
    ]
    counts: dict[str, int] = {}
    for model, condition in policies:
        counts[model.__tablename__] = (
            db.scalar(select(func.count()).select_from(model).where(condition)) or 0
        )
        if apply:
            db.execute(delete(model).where(condition))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retention: counts only unless --apply is passed. Requires maintenance-owner DATABASE_URL."
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    database = Database(Settings())
    if database.sessions is None:
        parser.error("DATABASE_URL is required")
    assert database.sessions is not None
    try:
        with database.sessions.begin() as db:
            allowed = db.scalar(
                text(
                    "SELECT current_user = pg_get_userbyid(nspowner) OR (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) FROM pg_namespace WHERE nspname='nammamove'"
                )
            )
            if not allowed:
                raise RuntimeError("Retention requires the maintenance schema owner")
            print({"applied": args.apply, "counts": retain(db, apply=args.apply)})
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
