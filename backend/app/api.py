"""Persistent APIs. Nothing in this module modifies the simulator or a live graph."""

from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .auth import Identity, Principal, admin, current_principal, moderator
from .database import get_session
from .engine import route
from .models import (
    AuditEvent,
    Commuter,
    Disruption,
    DisruptionEvidence,
    JourneyRecord,
    Notification,
    Operator,
    Stop,
    UserPreference,
    utcnow,
)
from .schemas import (
    JourneyInput,
    JourneyOutput,
    NotificationOutput,
    OperatorInput,
    OperatorOutput,
    PreferenceInput,
    ProfileInput,
    ProfileOutput,
    ReportInput,
    ReportOutput,
    StopInput,
    StopOutput,
    VerificationInput,
)

router = APIRouter(prefix="/v1", dependencies=[Depends(current_principal)])
Db = Annotated[Session, Depends(get_session, scope="function")]
PageSize = Annotated[int, Query(ge=1, le=100)]


def profile_required(db: Session, principal: Principal) -> Commuter:
    profile = db.get(Commuter, principal.id)
    if not profile:
        raise HTTPException(409, "Create a commuter profile first")
    return profile


def audit(db: Session, principal: Principal, action: str, entity_id: UUID) -> None:
    profile_required(db, principal)
    db.add(AuditEvent(actor_id=principal.id, action=action, entity_id=entity_id))


@router.put("/me", response_model=ProfileOutput)
def update_profile(payload: ProfileInput, principal: Identity, db: Db) -> Commuter:
    profile = db.get(Commuter, principal.id)
    if profile is None:
        profile = Commuter(id=principal.id, **payload.model_dump())
        db.add(profile)
    else:
        for name, value in payload.model_dump().items():
            setattr(profile, name, value)
    db.flush()
    return profile


@router.get("/me", response_model=ProfileOutput)
def my_profile(principal: Identity, db: Db) -> Commuter:
    return profile_required(db, principal)


@router.delete("/me", status_code=204)
def delete_profile(principal: Identity, db: Db) -> Response:
    # Deletes local profile/history, not the external Supabase Auth identity.
    profile = profile_required(db, principal)
    # Keep operational records but remove the departed reporter's free-text content.
    db.execute(
        update(Disruption)
        .where(Disruption.reporter_id == principal.id)
        .values(summary="[removed on local profile deletion]")
    )
    db.delete(profile)
    db.flush()
    return Response(status_code=204)


@router.put("/me/preferences", response_model=PreferenceInput)
def preferences(payload: PreferenceInput, principal: Identity, db: Db) -> UserPreference:
    profile_required(db, principal)
    preference = db.get(UserPreference, principal.id)
    if preference is None:
        preference = UserPreference(commuter_id=principal.id, **payload.model_dump())
        db.add(preference)
    else:
        for name, value in payload.model_dump().items():
            setattr(preference, name, value)
    db.flush()
    return preference


@router.post("/operators", response_model=OperatorOutput, status_code=201)
def create_operator(
    payload: OperatorInput, principal: Annotated[Principal, Depends(admin)], db: Db
) -> Operator:
    profile_required(db, principal)
    operator = Operator(**payload.model_dump())
    db.add(operator)
    db.flush()
    audit(db, principal, "operator.created", operator.id)
    return operator


@router.post("/stops", response_model=StopOutput, status_code=201)
def create_stop(
    payload: StopInput, principal: Annotated[Principal, Depends(admin)], db: Db
) -> Stop:
    profile_required(db, principal)
    if db.get(Operator, payload.operator_id) is None:
        raise HTTPException(404, "Operator not found")
    stop = Stop(**payload.model_dump())
    db.add(stop)
    db.flush()
    audit(db, principal, "stop.created", stop.id)
    return stop


@router.get("/stops", response_model=list[StopOutput])
def list_stops(
    principal: Identity,
    db: Db,
    data_mode: Literal["simulation", "live"] = "simulation",
    limit: PageSize = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> list[Stop]:
    return list(
        db.scalars(
            select(Stop)
            .join(Operator)
            .where(Operator.data_mode == data_mode)
            .order_by(Stop.id)
            .limit(limit)
            .offset(offset)
        )
    )


@router.post("/journeys", response_model=JourneyOutput, status_code=201)
def save_journey(
    payload: JourneyInput, request: Request, principal: Identity, db: Db
) -> JourneyRecord:
    profile_required(db, principal)
    if not request.app.state.settings.allow_simulation:
        raise HTTPException(503, "Only simulation routing is available in Phase 01")
    itinerary = route(payload.origin, payload.destination)
    if itinerary is None:
        raise HTTPException(404, "No route found in the sample network")
    journey = JourneyRecord(
        commuter_id=principal.id,
        origin=payload.origin,
        destination=payload.destination,
        data_mode="simulation",
        itinerary=cast(dict[str, object], dict(itinerary)),
    )
    db.add(journey)
    db.flush()
    return journey


@router.get("/journeys", response_model=list[JourneyOutput])
def my_journeys(principal: Identity, db: Db, limit: PageSize = 50) -> list[JourneyRecord]:
    return list(
        db.scalars(
            select(JourneyRecord)
            .where(JourneyRecord.commuter_id == principal.id)
            .order_by(JourneyRecord.created_at.desc(), JourneyRecord.id)
            .limit(limit)
        )
    )


def owned_journey(db: Session, principal: Principal, journey_id: UUID) -> JourneyRecord:
    journey = db.scalar(
        select(JourneyRecord).where(
            JourneyRecord.id == journey_id, JourneyRecord.commuter_id == principal.id
        )
    )
    if journey is None:
        raise HTTPException(404, "Journey not found")
    return journey


@router.get("/journeys/{journey_id}", response_model=JourneyOutput)
def get_journey(journey_id: UUID, principal: Identity, db: Db) -> JourneyRecord:
    return owned_journey(db, principal, journey_id)


@router.delete("/journeys/{journey_id}", status_code=204)
def delete_journey(journey_id: UUID, principal: Identity, db: Db) -> Response:
    db.delete(owned_journey(db, principal, journey_id))
    db.flush()
    return Response(status_code=204)


@router.post("/disruptions", response_model=ReportOutput, status_code=201)
def report_disruption(payload: ReportInput, principal: Identity, db: Db) -> Disruption:
    profile_required(db, principal)
    report = Disruption(
        reporter_id=principal.id, **payload.model_dump(), verification="unverified", confidence=0
    )
    db.add(report)
    db.flush()
    return report


@router.get("/disruptions/{report_id}", response_model=ReportOutput)
def get_report(report_id: UUID, principal: Identity, db: Db) -> Disruption:
    query = select(Disruption).where(Disruption.id == report_id)
    if principal.role == "commuter":
        query = query.where(Disruption.reporter_id == principal.id)
    report = db.scalar(query)
    if report is None:
        raise HTTPException(404, "Disruption not found")
    return report


@router.post("/disruptions/{report_id}/verification", response_model=ReportOutput)
def verify_report(
    report_id: UUID,
    payload: VerificationInput,
    principal: Annotated[Principal, Depends(moderator)],
    db: Db,
) -> Disruption:
    profile_required(db, principal)
    report = db.scalar(select(Disruption).where(Disruption.id == report_id).with_for_update())
    if report is None:
        raise HTTPException(404, "Disruption not found")
    if report.reporter_id == principal.id:
        raise HTTPException(403, "Independent verification is required")
    report.verification = payload.decision
    report.confidence = payload.confidence
    report.verified_at = utcnow()
    report.expires_at = payload.expires_at
    db.add(
        DisruptionEvidence(
            disruption_id=report.id,
            actor_id=principal.id,
            source=payload.evidence_source,
            decision=payload.decision,
        )
    )
    audit(db, principal, "disruption." + payload.decision, report.id)
    db.flush()
    return report


@router.get("/notifications", response_model=list[NotificationOutput])
def my_notifications(principal: Identity, db: Db, limit: PageSize = 50) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.commuter_id == principal.id)
            .order_by(Notification.created_at.desc(), Notification.id)
            .limit(limit)
        )
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationOutput)
def read_notification(notification_id: UUID, principal: Identity, db: Db) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.commuter_id == principal.id
        )
    )
    if notification is None:
        raise HTTPException(404, "Notification not found")
    if notification.read_at is None:
        notification.read_at = utcnow()
    db.flush()
    return notification
