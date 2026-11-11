"""Bounded synthetic GTFS-RT normalization, without network or runtime activation.

Only a conservative v2 FULL_DATASET subset is supported. Decoding is atomic and
stateless: omitted entities provide no evidence, never cancellation/recovery.
"""

from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Literal

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

from app.realtime.replay import Position, ReplayEvent, Service


class FeedRejected(ValueError):
    """Sanitized failure; no raw feed, identifiers or provider text in errors."""


class _Fields(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class _Trip(_Fields):
    trip_id: str = Field(min_length=1, max_length=100)
    start_date: str = Field(pattern=r"^\d{8}$")
    schedule_relationship: Literal["SCHEDULED", "CANCELED"] = "SCHEDULED"
    route_id: str | None = Field(default=None, max_length=100)
    start_time: str | None = Field(default=None, max_length=8)
    direction_id: int | None = Field(default=None, ge=0, le=1)


class _VehicleIdentity(_Fields):
    id: str = Field(min_length=1, max_length=100)


class _Vehicle(_Fields):
    trip: _Trip
    vehicle: _VehicleIdentity
    timestamp: int = Field(gt=0)
    position: Position


class _Update(_Fields):
    trip: _Trip
    timestamp: int = Field(gt=0)
    delay: int | None = Field(default=None, ge=-3600, le=86400)
    # Stop-level predictions need a separate uncertainty-aware contract.


class _Selector(_Fields):
    trip: _Trip


class _Period(_Fields):
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)


class _Translation(_Fields):
    text: str = Field(max_length=2000)
    language: str | None = Field(default=None, max_length=20)


class _Text(_Fields):
    translation: list[_Translation] = Field(max_length=8)


class _Alert(_Fields):
    informed_entity: list[_Selector] = Field(min_length=1, max_length=16)
    active_period: list[_Period] = Field(default_factory=list, max_length=32)
    cause: str | None = Field(default=None, max_length=50)
    effect: str | None = Field(default=None, max_length=50)
    header_text: _Text
    description_text: _Text | None = None


class _Entity(_Fields):
    id: str = Field(min_length=1, max_length=100)
    is_deleted: bool | None = None
    vehicle: _Vehicle | None = None
    trip_update: _Update | None = None
    alert: _Alert | None = None


class _Header(_Fields):
    gtfs_realtime_version: Literal["2.0"]
    incrementality: Literal["FULL_DATASET"] = "FULL_DATASET"
    timestamp: int = Field(gt=0)
    feed_version: str | None = Field(default=None, max_length=100)


class _Feed(_Fields):
    header: _Header
    entity: list[_Entity] = Field(default_factory=list, max_length=1000)


class FixtureBatch(BaseModel):
    model_config = ConfigDict(frozen=True)
    data_mode: Literal["simulation"] = "simulation"
    header_at: datetime
    feed_age_seconds: float
    events: tuple[ReplayEvent, ...]
    notice: str = "Synthetic GTFS-RT subset; no live service or verified incidents."


class FixtureGtfsRtAdapter:
    """Constructor-owned synthetic source/static-trip scope; no request trust flags.

    Reject unsupported protobuf fields rather than silently guessing semantics.
    Byte limits bound parsing before allocation; all output is built before return.
    This normalizer is not a full-snapshot state replacement or a durable worker.
    """

    def __init__(
        self,
        source_id: str,
        fixture_trips: frozenset[tuple[str, date]],
        *,
        max_bytes: int = 262144,
        max_entities: int = 1000,
        max_events: int = 1000,
        retention_seconds: int = 900,
    ) -> None:
        if not 1 <= len(source_id) <= 100 or not fixture_trips or len(fixture_trips) > 1000:
            raise ValueError("Configure a bounded synthetic source/trip catalog")
        if not all(1 <= len(trip) <= 100 for trip, _ in fixture_trips):
            raise ValueError("Invalid fixture trip catalog")
        if not 1 <= max_bytes <= 1048576 or not 1 <= max_entities <= 1000:
            raise ValueError("Invalid byte/entity limits")
        if not 1 <= max_events <= 1000 or not 1 <= retention_seconds <= 900:
            raise ValueError("Invalid event/retention limits")
        self.source_id = source_id
        self.fixture_trips = fixture_trips
        self.max_bytes = max_bytes
        self.max_entities = max_entities
        self.max_events = max_events
        self.retention_seconds = retention_seconds

    def decode(self, payload: bytes, *, now: datetime) -> FixtureBatch:
        """Validate one authored fixture feed; reject atomically with sanitized errors."""
        try:
            return self._decode(payload, now=now)
        except (ValueError, OverflowError, OSError, DecodeError):
            raise FeedRejected("Synthetic GTFS-RT feed rejected") from None

    def _decode(self, payload: bytes, *, now: datetime) -> FixtureBatch:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Aware receipt clock required")
        if not payload or len(payload) > self.max_bytes:
            raise ValueError("Payload size")
        message = gtfs_realtime_pb2.FeedMessage()
        message.ParseFromString(payload)
        if not message.IsInitialized() or len(message.entity) > self.max_entities:
            raise ValueError("Incomplete or oversized feed")
        original = message.SerializeToString(deterministic=True)
        message.DiscardUnknownFields()
        if message.SerializeToString(deterministic=True) != original:
            raise ValueError("Unsupported wire fields")
        feed = _Feed.model_validate(MessageToDict(message, preserving_proto_field_name=True))
        header_at = datetime.fromtimestamp(feed.header.timestamp, timezone.utc)
        age = (now - header_at).total_seconds()
        if not 0 <= age < self.retention_seconds:
            raise ValueError("Header clock")
        events: list[ReplayEvent] = []
        identities: set[str] = set()
        for entity in feed.entity:
            if entity.id in identities or entity.is_deleted is not None:
                raise ValueError("Duplicate ID or unsupported deletion")
            identities.add(entity.id)
            if sum(x is not None for x in (entity.vehicle, entity.trip_update, entity.alert)) != 1:
                raise ValueError("Ambiguous channel")
            if entity.vehicle is not None:
                item = entity.vehicle
                if item.trip.schedule_relationship != "SCHEDULED":
                    raise ValueError("Vehicle cannot state cancellation")
                events.append(
                    self._event(
                        entity,
                        item.trip,
                        item.timestamp,
                        "vehicle",
                        position=item.position,
                        vehicle_id=item.vehicle.id,
                    )
                )
            elif entity.trip_update is not None:
                update = entity.trip_update
                service: Service = "scheduled"
                if update.trip.schedule_relationship == "CANCELED":
                    if update.delay is not None:
                        raise ValueError("Cancelled trip cannot predict delay")
                    service = "cancelled"
                elif update.delay is not None and update.delay > 0:
                    service = "delayed"
                events.append(
                    self._event(
                        entity,
                        update.trip,
                        update.timestamp,
                        "trip_update",
                        service=service,
                        delay_seconds=update.delay,
                    )
                )
            elif entity.alert is not None:
                alert = entity.alert
                for period in alert.active_period:
                    if (
                        period.start is not None
                        and period.end is not None
                        and period.end <= period.start
                    ):
                        raise ValueError("Invalid alert interval")
                active = not alert.active_period or any(
                    (p.start is None or p.start <= now.timestamp())
                    and (p.end is None or now.timestamp() < p.end)
                    for p in alert.active_period
                )
                for selector in alert.informed_entity:
                    # Validate static selectors even for inactive alerts.
                    event = self._event(entity, selector.trip, feed.header.timestamp, "alert")
                    if active:
                        events.append(event)
            if len(events) > self.max_events:
                raise ValueError("Fanout limit")
        for event in events:
            if (
                event.observed_at > header_at
                or not 0 <= (now - event.observed_at).total_seconds() < self.retention_seconds
            ):
                raise ValueError("Observation clock")
        return FixtureBatch(header_at=header_at, feed_age_seconds=age, events=tuple(events))

    def _event(
        self,
        entity: _Entity,
        trip: _Trip,
        timestamp: int,
        kind: Literal["vehicle", "trip_update", "alert"],
        *,
        position: Position | None = None,
        vehicle_id: str | None = None,
        service: Service | None = None,
        delay_seconds: int | None = None,
    ) -> ReplayEvent:
        day = datetime.strptime(trip.start_date, "%Y%m%d").date()
        if (trip.trip_id, day) not in self.fixture_trips or trip.start_time is not None:
            raise ValueError("Unmatched or frequency-based fixture trip")
        identity = sha256(
            f"{entity.model_dump_json()}|{trip.trip_id}|{day}|{kind}|{timestamp}".encode()
        ).hexdigest()
        return ReplayEvent(
            source_id=self.source_id,
            event_id=identity,
            trip_id=trip.trip_id,
            service_date=day,
            kind=kind,
            observed_at=datetime.fromtimestamp(timestamp, timezone.utc),
            position=position,
            vehicle_id=vehicle_id,
            service=service,
            delay_seconds=delay_seconds,
        )
