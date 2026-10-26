"""Owner-only atomic imports. Callers own the outer transaction."""

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import insert, select, text
from sqlalchemy.orm import Session

from . import models as m
from .contracts import Manifest
from .validation import FeedRejected, validate_feed

TABLES = {
    "agencies": m.GtfsAgency,
    "stops": m.GtfsStop,
    "routes": m.GtfsRoute,
    "services": m.GtfsService,
    "calendar_dates": m.GtfsCalendarDate,
    "shapes": m.GtfsShape,
    "shape_points": m.GtfsShapePoint,
    "trips": m.GtfsTrip,
    "stop_times": m.GtfsStopTime,
    "transfers": m.GtfsTransfer,
    "frequencies": m.GtfsFrequency,
}


def lock_feed(session: Session, feed_id: str) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:feed, 0))"), {"feed": feed_id}
        )


def activate(session: Session, feed_id: str, dataset_id: UUID) -> m.TransitDataset:
    lock_feed(session, feed_id)
    feed = session.get(m.TransitFeed, feed_id, populate_existing=True)
    dataset = session.get(m.TransitDataset, dataset_id)
    if (
        feed is None
        or dataset is None
        or dataset.feed_id != feed_id
        or dataset.state != "validated"
    ):
        raise ValueError("Only a validated version belonging to this feed may be activated")
    feed.active_dataset_id = dataset.id
    session.flush()
    return dataset


def ingest(
    session: Session, payload: bytes, manifest: Manifest, *, promote: bool = True
) -> m.TransitDataset:
    lock_feed(session, manifest.feed_id)
    feed = session.get(m.TransitFeed, manifest.feed_id, populate_existing=True)
    if feed is None:
        feed = m.TransitFeed(
            id=manifest.feed_id, provider=manifest.provider, data_mode=manifest.data_mode
        )
        session.add(feed)
        session.flush()
    feed.last_attempt_at = datetime.now(timezone.utc)
    checksum = hashlib.sha256(payload).hexdigest()
    metadata = manifest.model_dump(mode="json", exclude={"retrieved_at"})
    digest = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
    existing = session.scalar(
        select(m.TransitDataset).where(
            m.TransitDataset.feed_id == feed.id,
            m.TransitDataset.checksum == checksum,
            m.TransitDataset.manifest_digest == digest,
        )
    )
    if existing is not None:
        if existing.state == "validated":
            feed.last_success_at = datetime.now(timezone.utc)
            feed.last_error_code = None
        else:
            feed.last_error_code = "quarantined_feed"
        if promote and existing.state == "validated":
            activate(session, feed.id, existing.id)
        return existing
    values = manifest.model_dump(exclude={"provider", "data_mode"})
    dataset = m.TransitDataset(
        feed_id=feed.id,
        checksum=checksum,
        manifest_digest=digest,
        state="quarantined",
        report={},
        **values,
    )
    session.add(dataset)
    try:
        validated = validate_feed(payload)
        allowed = {"bmtc": {3}, "bmrcl": {1}, "synthetic": {0, 1, 2, 3}}[manifest.provider]
        if any(row["route_type"] not in allowed for row in validated.tables["routes"]):
            raise FeedRejected("provider_route_type_mismatch", "routes.txt")
    except FeedRejected as error:
        dataset.report = error.report()
        feed.last_error_code = error.code
        session.flush()
        return dataset
    dataset.state = "validated"
    dataset.report = validated.report
    dataset.service_start, dataset.service_end = validated.service_start, validated.service_end
    session.flush()
    for name, model in TABLES.items():
        rows = validated.tables[name]
        for offset in range(0, len(rows), 1000):
            session.execute(
                insert(model),
                [{"dataset_id": dataset.id, **row} for row in rows[offset : offset + 1000]],
            )
    feed.last_success_at = datetime.now(timezone.utc)
    feed.last_error_code = None
    if promote:
        activate(session, feed.id, dataset.id)
    session.flush()
    return dataset
