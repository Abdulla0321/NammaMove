"""Authenticated, version-consistent static catalog searches."""

from datetime import date, datetime, timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select, text
from sqlalchemy.orm import Session

from ..auth import current_principal
from ..database import get_session
from .models import (
    GtfsCalendarDate,
    GtfsFrequency,
    GtfsRoute,
    GtfsService,
    GtfsStop,
    GtfsStopTime,
    GtfsTransfer,
    GtfsTrip,
    TransitDataset,
    TransitFeed,
)

router = APIRouter(prefix="/v1/transit", dependencies=[Depends(current_principal)])
Db = Annotated[Session, Depends(get_session, scope="function")]
Provider = Literal["bmtc", "bmrcl", "synthetic"]
Mode = Literal["scheduled", "simulation"]


def snapshot(db: Session, provider: Provider, mode: Mode) -> TransitDataset:
    dataset = db.scalar(
        select(TransitDataset)
        .join(TransitFeed, TransitFeed.active_dataset_id == TransitDataset.id)
        .where(TransitFeed.provider == provider, TransitFeed.data_mode == mode)
    )
    if dataset is None:
        raise HTTPException(503, "No validated active dataset is available")
    return dataset


def metadata(dataset: TransitDataset, mode: str) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    retrieved = (
        dataset.retrieved_at.replace(tzinfo=timezone.utc)
        if dataset.retrieved_at.tzinfo is None
        else dataset.retrieved_at
    )
    day = now.astimezone(ZoneInfo("Asia/Kolkata")).date()
    coverage = (
        dataset.service_start is not None
        and dataset.service_end is not None
        and dataset.service_start <= day <= dataset.service_end
    )
    stale = (now - retrieved).total_seconds() > 7 * 86400 or not coverage
    return {
        "dataset_id": str(dataset.id),
        "version": dataset.version,
        "data_mode": mode,
        "freshness": "simulation" if mode == "simulation" else "stale" if stale else "scheduled",
        "realtime_status": "unavailable",
        "service_status": "unknown",
        "retrieved_at": retrieved.isoformat(),
        "published_at": dataset.published_at.isoformat() if dataset.published_at else None,
        "service_start": str(dataset.service_start),
        "service_end": str(dataset.service_end),
        "timezone": dataset.timezone,
        "source_url": dataset.source_url,
        "checksum": dataset.checksum,
        "publisher": dataset.publisher,
        "authority": dataset.authority,
        "license_id": dataset.license_id,
        "license_url": dataset.license_url,
        "attribution": dataset.attribution,
        "quality": dataset.report,
        "quality_notes": dataset.quality_notes,
        "agency_schedule_accuracy_verified": False,
    }


def pattern(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@router.get("/feeds")
def feeds(db: Db) -> dict[str, object]:
    result = []
    for feed in db.scalars(select(TransitFeed).order_by(TransitFeed.id)):
        dataset = db.get(TransitDataset, feed.active_dataset_id) if feed.active_dataset_id else None
        result.append(
            {
                "provider": feed.provider,
                "data_mode": feed.data_mode,
                "status": metadata(dataset, feed.data_mode)["freshness"]
                if dataset
                else "unavailable",
                "last_error_code": feed.last_error_code,
                "last_attempt_at": feed.last_attempt_at,
                "last_success_at": feed.last_success_at,
                "active": metadata(dataset, feed.data_mode) if dataset else None,
            }
        )
    return {"feeds": result, "realtime_status": "unavailable", "service_status": "unknown"}


@router.get("/stops")
def stops(
    db: Db,
    provider: Provider,
    mode: Mode = "scheduled",
    q: Annotated[str, Query(max_length=100)] = "",
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_m: Annotated[int, Query(ge=1, le=10000)] = 1000,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> dict[str, object]:
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Latitude and longitude must be supplied together")
    dataset = snapshot(db, provider, mode)
    if latitude is not None:
        if db.get_bind().dialect.name != "postgresql":
            raise HTTPException(503, "Spatial search requires PostGIS")
        rows = db.execute(
            text("""SELECT external_id, name, latitude, longitude, location_type, parent_station,
            public.ST_Distance(location, public.ST_SetSRID(public.ST_MakePoint(:lon,:lat),4326)::public.geography) AS distance_m
            FROM nammamove.gtfs_stops WHERE dataset_id=:dataset AND name ILIKE :q ESCAPE '\\'
            AND public.ST_DWithin(location, public.ST_SetSRID(public.ST_MakePoint(:lon,:lat),4326)::public.geography,:radius)
            ORDER BY distance_m, external_id LIMIT :limit OFFSET :offset"""),
            {
                "dataset": dataset.id,
                "q": pattern(q),
                "lat": latitude,
                "lon": longitude,
                "radius": radius_m,
                "limit": limit,
                "offset": offset,
            },
        ).mappings()
        items = [dict(row) for row in rows]
    else:
        statement = (
            select(GtfsStop)
            .where(GtfsStop.dataset_id == dataset.id, GtfsStop.name.ilike(pattern(q), escape="\\"))
            .order_by(GtfsStop.name, GtfsStop.external_id)
            .limit(limit)
            .offset(offset)
        )
        items = [
            {
                "external_id": row.external_id,
                "name": row.name,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "location_type": row.location_type,
                "parent_station": row.parent_station,
            }
            for row in db.scalars(statement)
        ]
    return {"dataset": metadata(dataset, mode), "stops": items}


@router.get("/routes")
def routes(
    db: Db,
    provider: Provider,
    mode: Mode = "scheduled",
    q: Annotated[str, Query(max_length=100)] = "",
    stop_id: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> dict[str, object]:
    dataset = snapshot(db, provider, mode)
    statement = select(GtfsRoute).where(
        GtfsRoute.dataset_id == dataset.id,
        (
            GtfsRoute.short_name.ilike(pattern(q), escape="\\")
            | GtfsRoute.long_name.ilike(pattern(q), escape="\\")
        ),
    )
    if stop_id is not None:
        statement = statement.where(
            GtfsRoute.external_id.in_(
                select(GtfsTrip.route_id)
                .join(
                    GtfsStopTime,
                    (GtfsStopTime.dataset_id == GtfsTrip.dataset_id)
                    & (GtfsStopTime.trip_id == GtfsTrip.external_id),
                )
                .where(GtfsTrip.dataset_id == dataset.id, GtfsStopTime.stop_id == stop_id)
            )
        )
    items = [
        {
            "external_id": r.external_id,
            "short_name": r.short_name,
            "long_name": r.long_name,
            "route_type": r.route_type,
        }
        for r in db.scalars(statement.order_by(GtfsRoute.external_id).limit(limit).offset(offset))
    ]
    return {"dataset": metadata(dataset, mode), "routes": items}


@router.get("/network")
def network(db: Db, provider: Provider, mode: Mode = "scheduled") -> dict[str, object]:
    dataset = snapshot(db, provider, mode)
    return {
        "dataset": metadata(dataset, mode),
        "network": dataset.report.get("network"),
        "journey_planning_available": False,
    }


@router.get("/patterns")
def patterns(
    db: Db,
    provider: Provider,
    route_id: Annotated[str, Query(min_length=1, max_length=200)],
    mode: Mode = "scheduled",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    service_date: date | None = None,
) -> dict[str, object]:
    dataset = snapshot(db, provider, mode)
    statement = select(GtfsTrip).where(
        GtfsTrip.dataset_id == dataset.id, GtfsTrip.route_id == route_id
    )
    if service_date is not None:
        added = select(GtfsCalendarDate.service_id).where(
            GtfsCalendarDate.dataset_id == dataset.id,
            GtfsCalendarDate.date == service_date,
            GtfsCalendarDate.exception_type == 1,
        )
        removed = select(GtfsCalendarDate.service_id).where(
            GtfsCalendarDate.dataset_id == dataset.id,
            GtfsCalendarDate.date == service_date,
            GtfsCalendarDate.exception_type == 2,
        )
        regular = select(GtfsService.external_id).where(
            GtfsService.dataset_id == dataset.id,
            GtfsService.start_date <= service_date,
            GtfsService.end_date >= service_date,
            GtfsService.weekdays.op("&")(1 << service_date.weekday()) != 0,
        )
        statement = statement.where(
            or_(
                GtfsTrip.service_id.in_(added),
                and_(GtfsTrip.service_id.in_(regular), GtfsTrip.service_id.not_in(removed)),
            )
        )
    trips = list(db.scalars(statement.order_by(GtfsTrip.external_id).limit(limit)))
    items = []
    for trip in trips:
        times = db.scalars(
            select(GtfsStopTime)
            .where(GtfsStopTime.dataset_id == dataset.id, GtfsStopTime.trip_id == trip.external_id)
            .order_by(GtfsStopTime.sequence)
        )
        items.append(
            {
                "trip_id": trip.external_id,
                "direction_id": trip.direction_id,
                "service_id": trip.service_id,
                "frequencies": [
                    {
                        "start_seconds": f.start_seconds,
                        "end_seconds": f.end_seconds,
                        "headway_seconds": f.headway_seconds,
                        "exact_times": f.exact_times,
                    }
                    for f in db.scalars(
                        select(GtfsFrequency)
                        .where(
                            GtfsFrequency.dataset_id == dataset.id,
                            GtfsFrequency.trip_id == trip.external_id,
                        )
                        .order_by(GtfsFrequency.start_seconds)
                    )
                ],
                "stops": [
                    {
                        "stop_id": t.stop_id,
                        "sequence": t.sequence,
                        "arrival_seconds": t.arrival_seconds,
                        "timepoint": t.timepoint,
                        "timing_precision": "approximate"
                        if t.timepoint == 0
                        else "source_timepoint",
                        "departure_seconds": t.departure_seconds,
                    }
                    for t in times
                ],
            }
        )
    return {
        "dataset": metadata(dataset, mode),
        "patterns": items,
        "service_date_filter_applied": service_date is not None,
        "service_date": service_date,
        "time_basis": "seconds since Asia/Kolkata service-day midnight; values may exceed 86400",
    }


@router.get("/transfers")
def transfers(
    db: Db,
    provider: Provider,
    mode: Mode = "scheduled",
    stop_id: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> dict[str, object]:
    dataset = snapshot(db, provider, mode)
    statement = select(GtfsTransfer).where(GtfsTransfer.dataset_id == dataset.id)
    if stop_id is not None:
        statement = statement.where(
            (GtfsTransfer.from_stop_id == stop_id) | (GtfsTransfer.to_stop_id == stop_id)
        )
    rows = db.scalars(
        statement.order_by(GtfsTransfer.from_stop_id, GtfsTransfer.to_stop_id, GtfsTransfer.id)
        .limit(limit)
        .offset(offset)
    )
    return {
        "dataset": metadata(dataset, mode),
        "transfers": [
            {
                "from_stop_id": t.from_stop_id,
                "to_stop_id": t.to_stop_id,
                "transfer_type": t.transfer_type,
                "min_transfer_seconds": t.min_transfer_seconds,
                "from_route_id": t.from_route_id,
                "to_route_id": t.to_route_id,
                "from_trip_id": t.from_trip_id,
                "to_trip_id": t.to_trip_id,
            }
            for t in rows
        ],
        "inferred_walking_links": False,
    }
