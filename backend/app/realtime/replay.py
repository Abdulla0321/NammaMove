"""Bounded, deterministic fixture replay; deliberately not a GTFS-RT decoder.

No production source, API endpoint, graph closure or device location is enabled.
"""

from collections import Counter, OrderedDict
from datetime import date, datetime
from hashlib import sha256
from math import asin, cos, radians, sin, sqrt
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Kind = Literal["vehicle", "trip_update", "alert"]
Service = Literal["unknown", "scheduled", "delayed", "cancelled"]
Freshness = Literal["fresh", "stale", "unavailable"]
Outcome = Literal[
    "accepted", "duplicate", "conflicting_id", "out_of_order", "quarantined", "capacity"
]


class Position(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ReplayEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    source_id: str = Field(min_length=1, max_length=100)
    event_id: str = Field(min_length=1, max_length=100)
    trip_id: str = Field(min_length=1, max_length=100)
    service_date: date
    kind: Kind
    observed_at: AwareDatetime
    position: Position | None = None
    vehicle_id: str | None = Field(default=None, min_length=1, max_length=100)
    service: Service | None = None
    delay_seconds: int | None = Field(default=None, ge=-3600, le=86400)
    data_mode: Literal["simulation"] = "simulation"

    @model_validator(mode="after")
    def payload_matches_channel(self) -> "ReplayEvent":
        if self.kind != "vehicle" and (self.position is not None or self.vehicle_id is not None):
            raise ValueError("Only vehicle observations may contain vehicle positions")
        if self.kind != "trip_update" and (
            self.service is not None or self.delay_seconds is not None
        ):
            raise ValueError("Only independent trip updates may change service or delay")
        if self.kind == "trip_update" and self.service is None:
            raise ValueError("Trip update must state its independent service evidence")
        if self.position is not None and self.vehicle_id is None:
            raise ValueError("A position needs a vehicle identity")
        return self


class ChannelView(BaseModel):
    model_config = ConfigDict(frozen=True)
    freshness: Freshness
    observed_age_seconds: float | None


class TripView(BaseModel):
    model_config = ConfigDict(frozen=True)
    data_mode: Literal["simulation"] = "simulation"
    vehicle: ChannelView
    trip_update: ChannelView
    alert: ChannelView
    service: Service
    position: Position | None
    delay_seconds: int | None
    eta_uncertain: bool = True
    notice: str = "Synthetic replay; not live service or a current travel recommendation."


Key = tuple[str, str, date, Kind]


def _aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An aware clock is required")


def _distance(a: Position, b: Position) -> float:
    lat = radians(b.latitude - a.latitude)
    lon = radians(b.longitude - a.longitude)
    h = sin(lat / 2) ** 2 + cos(radians(a.latitude)) * cos(radians(b.latitude)) * sin(lon / 2) ** 2
    return 6371000 * 2 * asin(sqrt(min(1.0, max(0.0, h))))


class FixtureReplay:
    """Single-process fixture harness; trust is constructor-owned, never event-owned.

    No raw history/quarantine payloads are retained. Limits fail closed rather
    than evicting active ordering/idempotency records. A future durable worker
    must implement atomic ordering and deduplication across processes.
    """

    def __init__(
        self,
        fixture_sources: frozenset[str],
        *,
        fresh_seconds: int = 90,
        retention_seconds: int = 900,
        max_records: int = 1000,
        max_speed_mps: float = 70,
    ) -> None:
        if not fixture_sources or not 0 < fresh_seconds < retention_seconds:
            raise ValueError("Configure fixture sources and positive bounded freshness/retention")
        if max_records < 1 or not 0 < max_speed_mps <= 100:
            raise ValueError("Invalid capacity or speed bound")
        self.sources = fixture_sources
        self.fresh_seconds = fresh_seconds
        self.retention_seconds = retention_seconds
        self.max_records = max_records
        self.max_speed_mps = max_speed_mps
        self._events: dict[Key, ReplayEvent] = {}
        self._seen: OrderedDict[tuple[str, str], tuple[str, datetime]] = OrderedDict()
        self._clock: datetime | None = None
        self.metrics: Counter[str] = Counter()

    def _expire(self, now: datetime) -> None:
        _aware(now)
        if self._clock is not None and now < self._clock:
            raise ValueError("Replay receipt clock cannot move backwards")
        self._clock = now
        self._events = {
            key: event
            for key, event in self._events.items()
            if (now - event.observed_at).total_seconds() < self.retention_seconds
        }
        self._seen = OrderedDict(
            (key, entry)
            for key, entry in self._seen.items()
            if (now - entry[1]).total_seconds() < self.retention_seconds
        )

    def _result(self, result: Outcome) -> Outcome:
        self.metrics[result] += 1
        return result

    def ingest(self, event: ReplayEvent, *, now: datetime) -> Outcome:
        self._expire(now)
        age = (now - event.observed_at).total_seconds()
        if event.source_id not in self.sources or age < 0 or age >= self.retention_seconds:
            return self._result("quarantined")
        identity = (event.source_id, event.event_id)
        fingerprint = sha256(event.model_dump_json().encode()).hexdigest()
        seen = self._seen.get(identity)
        if seen is not None:
            return self._result("duplicate" if seen[0] == fingerprint else "conflicting_id")
        key = (event.source_id, event.trip_id, event.service_date, event.kind)
        previous = self._events.get(key)
        if previous is not None and event.observed_at <= previous.observed_at:
            return self._result("out_of_order")
        if previous is not None and previous.position is not None and event.position is not None:
            if previous.vehicle_id == event.vehicle_id:
                seconds = (event.observed_at - previous.observed_at).total_seconds()
                if _distance(previous.position, event.position) / seconds > self.max_speed_mps:
                    return self._result("quarantined")
        if len(self._seen) >= self.max_records or (
            key not in self._events and len(self._events) >= self.max_records
        ):
            return self._result("capacity")
        self._seen[identity] = (fingerprint, now)
        self._events[key] = event
        return self._result("accepted")

    def view(self, source_id: str, trip_id: str, service_date: date, *, now: datetime) -> TripView:
        self._expire(now)

        def channel(kind: Kind) -> tuple[ChannelView, ReplayEvent | None]:
            event = self._events.get((source_id, trip_id, service_date, kind))
            if event is None:
                return ChannelView(freshness="unavailable", observed_age_seconds=None), None
            age = (now - event.observed_at).total_seconds()
            return ChannelView(
                freshness="fresh" if age <= self.fresh_seconds else "stale",
                observed_age_seconds=age,
            ), event

        vehicle_view, vehicle = channel("vehicle")
        trip_view, trip = channel("trip_update")
        alert_view, _ = channel("alert")
        # Stale independent service evidence becomes unknown, never a fresh cancellation.
        service: Service = "unknown"
        if trip is not None and trip_view.freshness == "fresh" and trip.service is not None:
            service = trip.service
        return TripView(
            vehicle=vehicle_view,
            trip_update=trip_view,
            alert=alert_view,
            service=service,
            position=vehicle.position
            if vehicle is not None and vehicle_view.freshness == "fresh"
            else None,
            delay_seconds=trip.delay_seconds
            if trip is not None and trip_view.freshness == "fresh"
            else None,
        )
