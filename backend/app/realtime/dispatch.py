"""Durable metadata dispatch of already committed synthetic generations only.

No raw-feed spool, fetcher, public delivery or API startup hook. SQL checkpoint
and acceptance evidence remain authoritative; jobs never contain observations.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from redis.exceptions import RedisError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.realtime.durable import DurableIngestion
from app.realtime.models import IngestionDispatch, IngestionSource
from app.realtime.redis_state import _aware, _digest


@dataclass(frozen=True)
class DispatchLease:
    source_id: str
    identity: str
    token: UUID
    attempt: int
    data_mode: Literal["simulation"] = "simulation"


@dataclass(frozen=True)
class DispatchResult:
    status: str
    lease: DispatchLease | None = None
    data_mode: Literal["simulation"] = "simulation"


class DurableDispatch:
    """Explicit per-source queue; capacity/retry/lease policy is owner-controlled.

    All mutations use the existing source advisory lock. A lease is committed
    before projection, so process death leaves reclaimable SQL work. Projection
    and acknowledgement hold that lock together; late lease tokens cannot ack.
    """

    def __init__(self, store: DurableIngestion) -> None:
        self.store = store

    def enqueue(self, *, now: datetime) -> DispatchResult:
        """Reference the current committed generation, without bytes or TTL renewal."""
        _aware(now)
        try:
            with Session(self.store.engine) as db, db.begin():
                source = self.store._source(db, now)
                self.store._checkpoint(source, now)
                if source.received_at is None:
                    return DispatchResult("empty")
                expires = source.received_at + timedelta(seconds=source.evidence_seconds)
                if now >= expires:
                    return DispatchResult("expired")
                identity = _digest("accepted|" + (source.fingerprint or ""))
                previous = db.get(IngestionDispatch, (source.id, identity))
                if previous is not None:
                    if not self._matches(previous, source):
                        raise ValueError("Dispatch reference mismatch")
                    return DispatchResult("duplicate")
                # Bound total retained rows, including terminal metadata. Worker
                # clock alone cannot authorize physical deletion or free slots.
                self._prune(db, now)
                count = (
                    db.scalar(
                        select(func.count())
                        .select_from(IngestionDispatch)
                        .where(IngestionDispatch.source_id == source.id)
                    )
                    or 0
                )
                if count >= source.dispatch_capacity:
                    return DispatchResult("backpressure")
                assert source.header_at is not None and source.guards_digest is not None
                db.add(
                    IngestionDispatch(
                        source_id=source.id,
                        identity=identity,
                        header_at=source.header_at,
                        received_at=source.received_at,
                        expires_at=expires,
                        binding_digest=source.binding_digest,
                        guards_digest=source.guards_digest,
                        due_at=now,
                    )
                )
            return DispatchResult("queued")
        except (SQLAlchemyError, ValueError, KeyError):
            return DispatchResult("unavailable")

    def _prune(self, db: Session, now: datetime) -> int:
        rows = db.scalars(
            delete(IngestionDispatch)
            .where(
                IngestionDispatch.source_id == self.store.adapter.source_id,
                IngestionDispatch.expires_at <= now,
                IngestionDispatch.expires_at <= func.statement_timestamp(),
            )
            .returning(IngestionDispatch.identity)
        ).all()
        return len(rows)

    def retain(self, *, now: datetime) -> int:
        """Explicit bounded metadata deletion; failure propagates to the operator."""
        _aware(now)
        with Session(self.store.engine) as db, db.begin():
            self.store._source(db, now)
            return self._prune(db, now)

    def claim(self, *, now: datetime) -> DispatchResult:
        """Commit one finite lease; crashes consume an attempt before recovery."""
        _aware(now)
        try:
            with Session(self.store.engine) as db, db.begin():
                source = self.store._source(db, now)
                job = db.scalar(
                    select(IngestionDispatch)
                    .where(
                        IngestionDispatch.source_id == source.id,
                        or_(
                            (IngestionDispatch.state == "pending")
                            & (IngestionDispatch.due_at <= now),
                            (IngestionDispatch.state == "leased")
                            & (IngestionDispatch.lease_until <= now),
                        ),
                    )
                    .order_by(IngestionDispatch.header_at, IngestionDispatch.identity)
                    .limit(1)
                )
                if job is None:
                    return DispatchResult("idle")
                if now >= job.expires_at:
                    self._finish(job, "expired")
                    return DispatchResult("expired")
                if job.attempts >= source.dispatch_attempts:
                    self._finish(job, "exhausted")
                    return DispatchResult("exhausted")
                job.state = "leased"
                job.attempts += 1
                job.due_at = now  # Also fences a regressing processing clock.
                job.token = uuid4()
                job.lease_until = min(
                    job.expires_at, now + timedelta(seconds=source.dispatch_lease_seconds)
                )
                lease = DispatchLease(source.id, job.identity, job.token, job.attempts)
            return DispatchResult("claimed", lease)
        except (SQLAlchemyError, ValueError, KeyError):
            return DispatchResult("unavailable")

    @staticmethod
    def _finish(job: IngestionDispatch, state: str) -> None:
        job.state, job.token, job.lease_until = state, None, None

    @staticmethod
    def _matches(job: IngestionDispatch, source: IngestionSource) -> bool:
        return (
            (
                job.identity == _digest("accepted|" + (source.fingerprint or ""))
                and job.header_at == source.header_at
                and job.received_at == source.received_at
                and job.expires_at
                == source.received_at + timedelta(seconds=source.evidence_seconds)
                and job.binding_digest == source.binding_digest
                and job.guards_digest == source.guards_digest
                and job.data_mode == "simulation"
            )
            if source.received_at is not None
            else False
        )

    def process(self, lease: DispatchLease, *, now: datetime) -> DispatchResult:
        """Project only the current trusted checkpoint, then commit acknowledgement."""
        _aware(now)
        if lease.source_id != self.store.adapter.source_id or lease.data_mode != "simulation":
            return DispatchResult("stale")
        try:
            with Session(self.store.engine) as db, db.begin():
                source = self.store._source(db, now)
                job = db.get(IngestionDispatch, (source.id, lease.identity))
                if job is None:
                    return DispatchResult("stale")
                if job.state == "completed":
                    if job.identity != _digest("accepted|" + (source.fingerprint or "")):
                        return DispatchResult("superseded")
                    if not self._matches(job, source):
                        return DispatchResult("invalid")
                    self.store._checkpoint(source, now)
                    return DispatchResult("duplicate")
                if (
                    job.state != "leased"
                    or job.token != lease.token
                    or job.attempts != lease.attempt
                    or job.lease_until is None
                    or now < job.due_at
                    or now >= job.lease_until
                ):
                    return DispatchResult("stale")
                if now >= job.expires_at:
                    status = "expired"
                elif job.identity != _digest("accepted|" + (source.fingerprint or "")):
                    status = "superseded"
                elif not self._matches(job, source):
                    status = "invalid"
                else:
                    # Integrity checks happen before Redis mutation. Never use a
                    # historical job's payload: only the locked current source.
                    self.store._checkpoint(source, now)
                    try:
                        success = self.store._project(source, now)
                    except RedisError:
                        success = False
                    if success:
                        status = "completed"
                    elif job.attempts >= source.dispatch_attempts:
                        status = "exhausted"
                    else:
                        status = "retry"
                        job.due_at = now + timedelta(seconds=2 ** (job.attempts - 1))
                self._finish(job, "pending" if status == "retry" else status)
            return DispatchResult(status)
        except (SQLAlchemyError, ValueError, KeyError):
            # The committed lease survives SQL/projection failure; reclaim only
            # after its deadline. No false ack on an ambiguous COMMIT response.
            return DispatchResult("unavailable")

    def run_one(self, *, now: datetime) -> DispatchResult:
        """One explicit claim/process tick, with no sleep or startup integration."""
        result = self.claim(now=now)
        return self.process(result.lease, now=now) if result.lease is not None else result
