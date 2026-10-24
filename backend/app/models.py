"""Phase 01 catalog/security schema. No feed ingestion or live routing is implemented."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "nammamove"
FK = SCHEMA + "."


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(
        schema=SCHEMA,
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        },
    )


class Record:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class Commuter(Record, Base):
    __tablename__ = "commuters"
    display_name: Mapped[str] = mapped_column(String(80))
    locale: Mapped[str] = mapped_column(String(2), default="en")
    location_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("locale IN ('en','kn','hi')", name="commuter_locale"),)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    commuter_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "commuters.id", ondelete="CASCADE"), primary_key=True
    )
    step_free: Mapped[bool] = mapped_column(Boolean, default=False)
    max_walk_minutes: Mapped[int] = mapped_column(Integer, default=30)
    __table_args__ = (CheckConstraint("max_walk_minutes BETWEEN 0 AND 180", name="walk_limit"),)


class Operator(Record, Base):
    __tablename__ = "operators"
    name: Mapped[str] = mapped_column(String(120), unique=True)
    data_mode: Mapped[str] = mapped_column(String(10), default="simulation")
    __table_args__ = (CheckConstraint("data_mode IN ('simulation','live')", name="operator_mode"),)


class Stop(Record, Base):
    __tablename__ = "stops"
    operator_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "operators.id", ondelete="RESTRICT"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    # PostgreSQL migration adds stored generated geography(location) + GiST index.
    __table_args__ = (
        UniqueConstraint("operator_id", "external_id"),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name="stop_coordinates",
        ),
    )


class TransitRoute(Record, Base):
    __tablename__ = "transit_routes"
    operator_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "operators.id", ondelete="RESTRICT"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(160))
    mode: Mapped[str] = mapped_column(String(20))
    __table_args__ = (
        UniqueConstraint("operator_id", "external_id"),
        CheckConstraint("mode IN ('bus','metro','rail','walk')", name="route_mode"),
    )


class Trip(Record, Base):
    __tablename__ = "trips"
    route_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "transit_routes.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(100))
    service_id: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("route_id", "external_id"),)


class StopTime(Base):
    __tablename__ = "stop_times"
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "trips.id", ondelete="CASCADE"), primary_key=True
    )
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "stops.id", ondelete="RESTRICT"), index=True
    )
    arrival_seconds: Mapped[int] = mapped_column(Integer)
    departure_seconds: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint(
            "sequence >= 0 AND arrival_seconds >= 0 AND departure_seconds >= arrival_seconds",
            name="stop_time_order",
        ),
    )


class FeedSnapshot(Record, Base):
    __tablename__ = "feed_snapshots"
    operator_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "operators.id", ondelete="RESTRICT"), index=True
    )
    checksum: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(200))
    license: Mapped[str] = mapped_column(String(200))
    data_mode: Mapped[str] = mapped_column(String(10), default="simulation")
    __table_args__ = (
        UniqueConstraint("operator_id", "checksum"),
        CheckConstraint("data_mode IN ('simulation','live')", name="snapshot_mode"),
    )


class Disruption(Record, Base):
    __tablename__ = "disruptions"
    reporter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(FK + "commuters.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))
    summary: Mapped[str] = mapped_column(String(500))
    data_mode: Mapped[str] = mapped_column(String(10), default="simulation")
    verification: Mapped[str] = mapped_column(String(20), default="unverified")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    __table_args__ = (
        CheckConstraint("data_mode IN ('simulation','live')", name="disruption_mode"),
        CheckConstraint(
            "verification IN ('unverified','verified','rejected','resolved')",
            name="disruption_verification",
        ),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="disruption_confidence"),
        CheckConstraint(
            "verification != 'verified' OR (verified_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at > verified_at)",
            name="verification_lifetime",
        ),
    )


class DisruptionEvidence(Record, Base):
    __tablename__ = "disruption_evidence"
    disruption_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "disruptions.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(FK + "commuters.id", ondelete="SET NULL")
    )
    source: Mapped[str] = mapped_column(String(200))
    decision: Mapped[str] = mapped_column(String(20))
    __table_args__ = (
        CheckConstraint("decision IN ('verified','rejected')", name="evidence_decision"),
    )


class Vehicle(Record, Base):
    __tablename__ = "vehicles"
    operator_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "operators.id", ondelete="RESTRICT"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    feed_status: Mapped[str] = mapped_column(String(15), default="unavailable")
    service_status: Mapped[str] = mapped_column(String(25), default="uncertain")
    cancellation_evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(FK + "disruption_evidence.id", ondelete="RESTRICT")
    )
    __table_args__ = (
        UniqueConstraint("operator_id", "external_id"),
        CheckConstraint("capacity >= 0", name="vehicle_capacity"),
        CheckConstraint(
            "feed_status IN ('live','stale','unavailable','simulation')", name="vehicle_feed_status"
        ),
        CheckConstraint(
            "service_status IN ('scheduled','delayed','uncertain','confirmed_cancelled')",
            name="vehicle_service_status",
        ),
        CheckConstraint(
            "service_status != 'confirmed_cancelled' OR cancellation_evidence_id IS NOT NULL",
            name="cancellation_requires_evidence",
        ),
    )


class JourneyRecord(Record, Base):
    __tablename__ = "journeys"
    commuter_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "commuters.id", ondelete="CASCADE"), index=True
    )
    origin: Mapped[str] = mapped_column(String(160))
    destination: Mapped[str] = mapped_column(String(160))
    data_mode: Mapped[str] = mapped_column(String(10), default="simulation")
    itinerary: Mapped[dict[str, object]] = mapped_column(JSON)
    __table_args__ = (CheckConstraint("data_mode IN ('simulation','live')", name="journey_mode"),)


class Notification(Record, Base):
    __tablename__ = "notifications"
    commuter_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "commuters.id", ondelete="CASCADE"), index=True
    )
    message: Mapped[str] = mapped_column(String(500))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_mode: Mapped[str] = mapped_column(String(10), default="simulation")
    __table_args__ = (
        CheckConstraint("data_mode IN ('simulation','live')", name="notification_mode"),
    )


class AuditEvent(Record, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(FK + "commuters.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[UUID | None] = mapped_column(Uuid)
