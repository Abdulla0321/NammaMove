"""Private synthetic ingestion metadata; latest checkpoint only, never GPS history."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models import FK, Base


class IngestionSource(Base):
    __tablename__ = "ingestion_sources"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    dataset_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(FK + "transit_datasets.id", ondelete="RESTRICT")
    )
    binding_digest: Mapped[str] = mapped_column(String(64))
    data_mode: Mapped[str] = mapped_column(String(10), default="simulation")
    evidence_seconds: Mapped[int] = mapped_column(Integer)
    max_generations: Mapped[int] = mapped_column(Integer)
    dispatch_capacity: Mapped[int] = mapped_column(Integer, default=8, server_default="8")
    dispatch_attempts: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    dispatch_lease_seconds: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    header_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkpoint: Mapped[str | None] = mapped_column(Text)
    checkpoint_digest: Mapped[str | None] = mapped_column(String(64))
    guards_digest: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = (
        CheckConstraint(
            "dispatch_capacity BETWEEN 1 AND 32 AND dispatch_attempts BETWEEN 1 AND 5 AND dispatch_lease_seconds BETWEEN 1 AND 60",
            name="ingestion_dispatch_bounds",
        ),
        CheckConstraint("data_mode = 'simulation'", name="ingestion_source_simulation"),
        CheckConstraint(
            "evidence_seconds BETWEEN 900 AND 86400 AND max_generations BETWEEN 1 AND 1000",
            name="ingestion_source_bounds",
        ),
        CheckConstraint(
            "(header_at IS NULL AND fingerprint IS NULL AND received_at IS NULL AND checkpoint IS NULL AND checkpoint_digest IS NULL AND guards_digest IS NULL) OR (header_at IS NOT NULL AND fingerprint IS NOT NULL AND received_at IS NOT NULL AND received_at >= header_at AND checkpoint IS NOT NULL AND checkpoint_digest IS NOT NULL AND guards_digest IS NOT NULL)",
            name="ingestion_watermark_complete",
        ),
        CheckConstraint("length(checkpoint) <= 4194304", name="ingestion_checkpoint_bound"),
    )


class IngestionDispatch(Base):
    """Bounded references only; the source checkpoint remains payload authority."""

    __tablename__ = "ingestion_dispatch"
    source_id: Mapped[str] = mapped_column(
        ForeignKey(FK + "ingestion_sources.id", ondelete="RESTRICT"), primary_key=True
    )
    identity: Mapped[str] = mapped_column(String(64), primary_key=True)
    header_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    binding_digest: Mapped[str] = mapped_column(String(64))
    guards_digest: Mapped[str] = mapped_column(String(64))
    data_mode: Mapped[str] = mapped_column(String(10), default="simulation")
    state: Mapped[str] = mapped_column(String(12), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    token: Mapped[UUID | None] = mapped_column(Uuid)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("data_mode = 'simulation'", name="dispatch_simulation"),
        CheckConstraint(
            "state IN ('pending','leased','completed','superseded','expired','exhausted','invalid') AND attempts BETWEEN 0 AND 5",
            name="dispatch_state",
        ),
        CheckConstraint(
            "received_at >= header_at AND expires_at > received_at AND expires_at <= received_at + interval '86400 seconds'",
            name="dispatch_expiry",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "(state = 'leased' AND token IS NOT NULL AND lease_until IS NOT NULL) OR (state <> 'leased' AND token IS NULL AND lease_until IS NULL)",
            name="dispatch_lease",
        ),
    )


class IngestionWorker(Base):
    """Owner-assigned actual database identities; never JWT or GUC authority."""

    __tablename__ = "ingestion_workers"
    worker_name: Mapped[str] = mapped_column(String(63), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey(FK + "ingestion_sources.id", ondelete="RESTRICT"), primary_key=True
    )


class IngestionGeneration(Base):
    __tablename__ = "ingestion_generations"
    source_id: Mapped[str] = mapped_column(
        ForeignKey(FK + "ingestion_sources.id", ondelete="RESTRICT"), primary_key=True
    )
    identity: Mapped[str] = mapped_column(String(64), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(20))
    header_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    data_mode: Mapped[str] = mapped_column(String(10), default="simulation")
    guards_digest: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = (
        CheckConstraint("data_mode = 'simulation'", name="ingestion_generation_simulation"),
        CheckConstraint("expires_at > received_at", name="ingestion_evidence_expiry"),
        CheckConstraint(
            "(outcome = 'accepted' AND guards_digest IS NOT NULL) OR (outcome <> 'accepted' AND guards_digest IS NULL)",
            name="ingestion_accepted_guards",
        ),
        CheckConstraint(
            "outcome IN ('accepted','rejected','out_of_order','conflict','quarantined','capacity')",
            name="ingestion_generation_outcome",
        ),
    )
