"""Synthetic source-scoped durability gate around the existing whole-feed worker.

PostgreSQL is authoritative. Redis writes are provisional until SQL commits;
all durable reads re-project the committed checkpoint under the same source lock.
No network fetcher, application startup hook, raw feed archive or public API.
"""

import json
from datetime import date, datetime, timedelta
from math import ceil
from typing import cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from redis.exceptions import RedisError, WatchError
from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.realtime.gtfs_rt import FeedRejected
from app.realtime.ingestion import FeedOutcome, FeedSnapshot, RedisFullDataset, _Manifest
from app.realtime.models import IngestionGeneration, IngestionSource
from app.realtime.redis_state import TrackingSnapshot, _aware, _digest
from app.transit.models import GtfsCalendarDate, GtfsService, GtfsTrip, TransitDataset, TransitFeed


class _Checkpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    data_mode: str = Field(pattern="^simulation$")
    manifest: str = Field(max_length=1048576)
    payloads: dict[str, str] = Field(max_length=1000)


class DurableIngestion:
    """Bounded owner-registered fixture worker; preserve existing event/cache APIs.

    Use an exclusive Redis namespace for this durable source. Callers must not
    bypass this gate with standalone cache writers/readers. No SQL transaction
    is held after return, and no acceptance is reported before the SQL commit.
    """

    def __init__(self, engine: Engine, cache: RedisFullDataset, dataset_id: UUID) -> None:
        if engine.dialect.name != "postgresql":
            raise ValueError("Durable ingestion requires genuine PostgreSQL")
        self.engine = engine
        self.cache = cache
        self.adapter = cache.adapter
        self.dataset_id = dataset_id

    def _lock(self, db: Session) -> None:
        db.execute(text("SET LOCAL statement_timeout = '2000ms'"))
        db.execute(text("SET LOCAL lock_timeout = '1000ms'"))
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:source, 0))"),
            {"source": "ingestion:" + self.adapter.source_id},
        )

    def _owner(self, db: Session) -> None:
        owner = db.scalar(
            text(
                "SELECT current_user = pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='nammamove'"
            )
        )
        if owner is not True:
            raise ValueError("This slice requires an explicitly configured maintenance owner")

    def _binding(self, db: Session) -> str:
        dataset = db.get(TransitDataset, self.dataset_id, populate_existing=True)
        if dataset is None:
            raise ValueError("Missing static snapshot")
        feed = db.get(TransitFeed, dataset.feed_id, populate_existing=True)
        if (
            feed is None
            or feed.provider != "synthetic"
            or feed.data_mode != "simulation"
            or dataset.state != "validated"
            or dataset.authorization != "simulation"
            or dataset.authority != "synthetic"
            or self.cache.version is not None
            and self.cache.version != dataset.version
        ):
            raise ValueError("Mismatched synthetic static snapshot")
        catalog: list[object] = []
        for trip_id, day in sorted(self.adapter.fixture_trips):
            trip = db.scalar(
                select(GtfsTrip).where(
                    GtfsTrip.dataset_id == self.dataset_id, GtfsTrip.external_id == trip_id
                )
            )
            if trip is None:
                raise ValueError("Trip outside bound static snapshot")
            service = db.scalar(
                select(GtfsService).where(
                    GtfsService.dataset_id == self.dataset_id,
                    GtfsService.external_id == trip.service_id,
                )
            )
            exception = db.scalar(
                select(GtfsCalendarDate.exception_type).where(
                    GtfsCalendarDate.dataset_id == self.dataset_id,
                    GtfsCalendarDate.service_id == trip.service_id,
                    GtfsCalendarDate.date == day,
                )
            )
            active = (
                service is not None
                and service.start_date <= day <= service.end_date
                and bool(service.weekdays & (1 << day.weekday()))
            )
            if exception is not None:
                active = exception == 1
            if not active:
                raise ValueError("Inactive bound static service date")
            assert service is not None
            catalog.append(
                [
                    trip_id,
                    str(day),
                    trip.route_id,
                    trip.service_id,
                    trip.shape_id,
                    trip.direction_id,
                    service.weekdays,
                    str(service.start_date),
                    str(service.end_date),
                    exception,
                ]
            )
        return _digest(
            json.dumps(
                [
                    str(dataset.id),
                    dataset.checksum,
                    dataset.manifest_digest,
                    dataset.version,
                    dataset.feed_id,
                    self.cache.policy,
                    self.cache.prefix,
                    catalog,
                ]
            )
        )

    def register(self, *, evidence_seconds: int = 86400, max_generations: int = 1000) -> None:
        """Explicit owner registration; never rebind an existing source in place."""
        if not 900 <= evidence_seconds <= 86400 or not 1 <= max_generations <= 1000:
            raise ValueError("Invalid bounded evidence policy")
        with Session(self.engine) as db, db.begin():
            self._lock(db)
            self._owner(db)
            digest = self._binding(db)
            previous = db.get(IngestionSource, self.adapter.source_id)
            if previous is not None:
                if (
                    previous.dataset_id,
                    previous.binding_digest,
                    previous.evidence_seconds,
                    previous.max_generations,
                ) != (self.dataset_id, digest, evidence_seconds, max_generations):
                    raise ValueError("Source registration is immutable")
                return
            db.add(
                IngestionSource(
                    id=self.adapter.source_id,
                    dataset_id=self.dataset_id,
                    binding_digest=digest,
                    evidence_seconds=evidence_seconds,
                    max_generations=max_generations,
                )
            )

    def _source(self, db: Session, now: datetime) -> IngestionSource:
        self._lock(db)
        source = db.get(IngestionSource, self.adapter.source_id, populate_existing=True)
        if (
            source is None
            or source.data_mode != "simulation"
            or source.dataset_id != self.dataset_id
            or source.binding_digest != self._binding(db)
        ):
            raise ValueError("Source/static snapshot binding mismatch")
        if source.received_at is not None and now < source.received_at:
            raise ValueError("Receipt clock regression")
        if source.received_at is not None:
            identity = _digest("accepted|" + (source.fingerprint or ""))
            evidence = db.get(IngestionGeneration, (source.id, identity))
            expires = source.received_at + timedelta(seconds=source.evidence_seconds)
            if evidence is None:
                if now < expires:
                    raise ValueError("Missing unexpired acceptance evidence")
            elif (
                evidence.outcome != "accepted"
                or evidence.data_mode != "simulation"
                or evidence.fingerprint != source.fingerprint
                or evidence.header_at != source.header_at
                or evidence.received_at != source.received_at
                or evidence.expires_at != expires
                or evidence.guards_digest != source.guards_digest
            ):
                raise ValueError("Acceptance evidence/watermark mismatch")
        return source

    def _checkpoint(
        self, source: IngestionSource, now: datetime
    ) -> tuple[_Manifest | None, dict[str, str]]:
        if source.checkpoint is None:
            if source.header_at is not None or source.fingerprint is not None:
                raise ValueError("Missing durable checkpoint")
            return None, {}
        if (
            len(source.checkpoint.encode()) > 4194304
            or _digest(source.checkpoint) != source.checkpoint_digest
        ):
            raise ValueError("Corrupt durable checkpoint")
        checkpoint = _Checkpoint.model_validate_json(source.checkpoint)
        manifest = self.cache._manifest(checkpoint.manifest, now)
        if manifest is None or (manifest.header_at, manifest.fingerprint, manifest.received_at) != (
            source.header_at,
            source.fingerprint,
            source.received_at,
        ):
            raise ValueError("Durable watermark mismatch")
        if _digest(manifest.model_dump_json(include={"guards"})) != source.guards_digest:
            raise ValueError("Retained ordering guard integrity mismatch")
        if set(checkpoint.payloads) - {r.key for r in manifest.records}:
            raise ValueError("Unreferenced recovery payload")
        for record in manifest.records:
            raw = checkpoint.payloads.get(record.key)
            self.cache._validate_observation(
                record, raw.encode() if raw is not None else None, manifest, now
            )
        return manifest, checkpoint.payloads

    def _project(self, source: IngestionSource, now: datetime) -> bool:
        manifest, payloads = self._checkpoint(source, now)
        for _ in range(self.cache.state.max_attempts):
            try:
                with self.cache.client.pipeline() as tx:
                    tx.watch(self.cache.key)  # type: ignore[no-untyped-call]
                    previous = self.cache._manifest(cast(bytes | None, tx.get(self.cache.key)), now)
                    old_keys = [] if previous is None else [r.key for r in previous.records]
                    tx.multi()
                    if old_keys:
                        tx.delete(*old_keys)
                    if manifest is None:
                        tx.delete(self.cache.key)
                    else:
                        for record in manifest.records:
                            remaining = (record.expires_at - now).total_seconds()
                            if remaining > 0:
                                tx.set(
                                    record.key,
                                    payloads[record.key],
                                    px=max(1, ceil(remaining * 1000)),
                                )
                        # Only hashed ordering metadata survives original observation expiry.
                        tx.set(
                            self.cache.key,
                            manifest.model_dump_json(),
                            ex=self.cache.state.retention_seconds,
                        )
                    tx.execute()
                    return True
            except WatchError:
                continue
        return False

    def _capture(self, source: IngestionSource, now: datetime) -> None:
        raw = cast(bytes | None, self.cache.client.get(self.cache.key))
        manifest = self.cache._manifest(raw, now)
        if manifest is None:
            raise ValueError("No accepted generation")
        keys = [r.key for r in manifest.records]
        values = cast(list[bytes | None], self.cache.client.mget(keys)) if keys else []
        payloads = {
            key: value.decode()
            for key, value in zip(keys, values, strict=True)
            if value is not None
        }
        checkpoint = _Checkpoint(
            data_mode="simulation", manifest=manifest.model_dump_json(), payloads=payloads
        ).model_dump_json()
        source.header_at, source.fingerprint, source.received_at = (
            manifest.header_at,
            manifest.fingerprint,
            manifest.received_at,
        )
        source.checkpoint, source.checkpoint_digest = checkpoint, _digest(checkpoint)
        source.guards_digest = _digest(manifest.model_dump_json(include={"guards"}))
        self._checkpoint(source, now)

    def ingest(self, payload: bytes, *, now: datetime) -> FeedOutcome:
        """Persist accepted/rejected metadata idempotently; unavailable is retryable."""
        _aware(now)
        if not isinstance(payload, bytes) or len(payload) > self.adapter.max_bytes:
            return "rejected"  # No unbounded hashing/archive for oversized input.
        try:
            with Session(self.engine) as db, db.begin():
                source = self._source(db, now)
                try:
                    batch = self.adapter.decode(payload, now=now)
                    fingerprint, header = batch.fingerprint, batch.header_at
                    valid = batch.feed_version == self.cache.version
                    for reference in batch.trip_references:
                        trip = db.scalar(
                            select(GtfsTrip).where(
                                GtfsTrip.dataset_id == self.dataset_id,
                                GtfsTrip.external_id == reference.trip_id,
                            )
                        )
                        if (
                            trip is None
                            or (
                                reference.route_id is not None
                                and reference.route_id != trip.route_id
                            )
                            or (
                                reference.direction_id is not None
                                and reference.direction_id != trip.direction_id
                            )
                        ):
                            valid = False
                except FeedRejected:
                    fingerprint, header, valid = _digest(payload.hex()), None, False
                # Outcome identities do not rewrite or renew existing evidence retention.
                if not valid:
                    outcome: FeedOutcome = "rejected"
                else:
                    if not self._project(source, now):
                        return "contended"
                    outcome = self.cache.ingest(payload, now=now)
                    if outcome == "accepted":
                        self._capture(source, now)
                    if outcome in {"unavailable", "contended"}:
                        return outcome
                if outcome == "duplicate":
                    return outcome
                identity = _digest(outcome + "|" + fingerprint)
                if db.get(IngestionGeneration, (self.adapter.source_id, identity)) is None:
                    count = (
                        db.scalar(
                            select(func.count())
                            .select_from(IngestionGeneration)
                            .where(IngestionGeneration.source_id == source.id)
                        )
                        or 0
                    )
                    if count >= source.max_generations:
                        # Roll back provisional cache/source changes and require retention.
                        raise _Capacity()
                    db.add(
                        IngestionGeneration(
                            source_id=source.id,
                            identity=identity,
                            fingerprint=fingerprint,
                            outcome=outcome,
                            header_at=header,
                            received_at=now,
                            expires_at=now + timedelta(seconds=source.evidence_seconds),
                            guards_digest=source.guards_digest if outcome == "accepted" else None,
                        )
                    )
            return outcome  # Outside transaction: acceptance requires successful COMMIT.
        except _Capacity:
            return "capacity"
        except (SQLAlchemyError, RedisError, ValueError, KeyError):
            return "unavailable"

    def recover(self, *, now: datetime) -> bool:
        """Rebuild only a trusted, matching, still-valid committed checkpoint."""
        _aware(now)
        try:
            with Session(self.engine) as db, db.begin():
                return self._project(self._source(db, now), now)
        except (SQLAlchemyError, RedisError, ValueError, KeyError):
            return False

    def snapshot(self, trip_id: str, day: date, *, now: datetime) -> FeedSnapshot:
        """Durability-gated read; never expose provisional or mismatched Redis state."""
        _aware(now)
        try:
            with Session(self.engine) as db, db.begin():
                if self._project(self._source(db, now), now):
                    return self.cache.snapshot(trip_id, day, now=now)
        except (SQLAlchemyError, RedisError, ValueError, KeyError):
            pass
        return FeedSnapshot(tracking=TrackingSnapshot(storage_status="unavailable"))

    def retain(self, *, now: datetime, apply: bool = False) -> dict[str, int]:
        """Source-scoped bounded retention, dry-run by default; preserve watermarks."""
        _aware(now)
        with Session(self.engine) as db, db.begin():
            source = self._source(db, now)
            manifest, payloads = self._checkpoint(source, now)
            condition = (IngestionGeneration.source_id == source.id) & (
                IngestionGeneration.expires_at <= now
            )
            evidence = (
                db.scalar(select(func.count()).select_from(IngestionGeneration).where(condition))
                or 0
            )
            kept = (
                {}
                if manifest is None
                else {
                    r.key: payloads[r.key]
                    for r in manifest.records
                    if now < r.expires_at and r.key in payloads
                }
            )
            counts = {"evidence": evidence, "payloads": len(payloads) - len(kept)}
            if apply:
                db.execute(delete(IngestionGeneration).where(condition))
                if manifest is not None:
                    source.checkpoint = _Checkpoint(
                        data_mode="simulation", manifest=manifest.model_dump_json(), payloads=kept
                    ).model_dump_json()
                    source.checkpoint_digest = _digest(source.checkpoint)
            return counts


class _Capacity(Exception):
    """Internal rollback signal, without retaining provider data."""
