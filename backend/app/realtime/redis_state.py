"""Synthetic-only atomic event state. No network feed, queue, route or delivery API.

One source metadata key serializes writers. Payload keys expire independently;
metadata retains bounded ordering/dedup guards without retaining GPS history.
"""

import json
import re
from datetime import date, datetime, timedelta
from hashlib import sha256
from math import ceil
from typing import Literal, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError, WatchError
from redis.retry import Retry

from app.realtime.replay import Freshness, Kind, Position, ReplayEvent, Service, _distance

WriteOutcome = Literal[
    "accepted",
    "duplicate",
    "conflicting_id",
    "out_of_order",
    "quarantined",
    "capacity",
    "contended",
    "unavailable",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Guard(_Model):
    observed_at: AwareDatetime
    expires_at: AwareDatetime


class _Seen(_Model):
    fingerprint: str
    expires_at: AwareDatetime


class _Metadata(_Model):
    policy: str
    clock: AwareDatetime
    guards: dict[str, _Guard] = Field(default_factory=dict, max_length=1000)
    seen: dict[str, _Seen] = Field(default_factory=dict, max_length=1000)


class Observation(_Model):
    event: ReplayEvent
    received_at: AwareDatetime


class ChannelSnapshot(_Model):
    freshness: Freshness = "unavailable"
    observed_at: AwareDatetime | None = None
    received_at: AwareDatetime | None = None
    observed_age_seconds: float | None = None


class Prediction(_Model):
    basis: Literal["synthetic_trip_update"] = "synthetic_trip_update"
    delay_seconds: int
    eta_uncertain: Literal[True] = True


class TrackingSnapshot(_Model):
    data_mode: Literal["simulation"] = "simulation"
    storage_status: Literal["available", "unavailable"]
    vehicle: ChannelSnapshot = Field(default_factory=ChannelSnapshot)
    trip_update: ChannelSnapshot = Field(default_factory=ChannelSnapshot)
    alert: ChannelSnapshot = Field(default_factory=ChannelSnapshot)
    observed_position: Position | None = None
    service: Service = "unknown"
    predicted: Prediction | None = None
    scheduled_information: Literal["not_loaded"] = "not_loaded"
    notice: str = "Synthetic observations and predictions; not live or verified service."


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _aware(now: datetime) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("An aware clock is required")


def tracking_client(url: str) -> Redis:
    """Create a bounded owner-configured connection; do not log resolved URLs."""
    return Redis.from_url(
        url,
        socket_timeout=0.25,
        socket_connect_timeout=0.25,
        retry=Retry(NoBackoff(), 0),
        max_connections=16,
    )


class RedisTrackingState:
    """Bounded synchronous worker primitive; callers supply validated fixture events.

    Redis access is owner-configured with a short socket/connect timeout, no
    automatic retry, no eviction and no persistence for synthetic GPS payloads.
    The class never fetches URLs or accepts request-owned source authorization.
    """

    def __init__(
        self,
        client: Redis,
        *,
        namespace: str,
        source_id: str,
        fixture_trips: frozenset[tuple[str, date]],
        fresh_seconds: int = 90,
        retention_seconds: int = 900,
        max_records: int = 1000,
        max_attempts: int = 8,
        max_speed_mps: float = 70,
    ) -> None:
        if not re.fullmatch(r"nammamove:simulation:[a-zA-Z0-9_-]{1,64}", namespace):
            raise ValueError("Use an isolated simulation namespace")
        if not 1 <= len(source_id) <= 100 or not 1 <= len(fixture_trips) <= 1000:
            raise ValueError("Configure a bounded synthetic source/trip catalog")
        if not all(1 <= len(trip) <= 100 for trip, _ in fixture_trips):
            raise ValueError("Invalid fixture trip catalog")
        if not 0 < fresh_seconds < retention_seconds <= 900:
            raise ValueError("Invalid freshness/retention")
        if not 1 <= max_records <= 1000 or not 1 <= max_attempts <= 16:
            raise ValueError("Invalid capacity/retry limits")
        if not 0 < max_speed_mps <= 100:
            raise ValueError("Invalid speed bound")
        connection = client.connection_pool.connection_kwargs
        for option in ("socket_timeout", "socket_connect_timeout"):
            timeout = connection.get(option)
            if not isinstance(timeout, (int, float)) or not 0 < timeout <= 1:
                raise ValueError("Worker connections require bounded timeouts")
        retry = connection.get("retry")
        if not isinstance(retry, Retry) or retry.get_retries() != 0:
            raise ValueError("Worker connections must disable hidden retries")
        self.client = client
        self.source_id = source_id
        self.fixture_trips = fixture_trips
        self.fresh_seconds = fresh_seconds
        self.retention_seconds = retention_seconds
        self.max_records = max_records
        self.max_attempts = max_attempts
        self.max_speed_mps = max_speed_mps
        # Shared hash tag keeps transactions within one Redis Cluster slot.
        self.prefix = f"{namespace}:{{{_digest(source_id)}}}:"
        self.metadata_key = self.prefix + "metadata"
        self.policy = _digest(
            json.dumps(
                [
                    source_id,
                    sorted((trip, str(day)) for trip, day in fixture_trips),
                    fresh_seconds,
                    retention_seconds,
                    max_records,
                    max_speed_mps,
                ]
            )
        )

    def _key(self, trip_id: str, day: date, kind: Kind) -> str:
        return self.prefix + _digest(json.dumps([trip_id, str(day), kind]))

    def _metadata(self, raw: bytes | str | None, now: datetime) -> _Metadata:
        if raw is None:
            return _Metadata(policy=self.policy, clock=now)
        if len(raw) > 524288:
            raise ValueError("Oversized metadata")
        state = _Metadata.model_validate_json(raw)
        if state.policy != self.policy or now < state.clock:
            raise ValueError("Policy or clock mismatch")
        return _Metadata(
            policy=state.policy,
            clock=state.clock,
            guards={k: v for k, v in state.guards.items() if now < v.expires_at},
            seen={k: v for k, v in state.seen.items() if now < v.expires_at},
        )

    def _observation(self, raw: bytes | str | None, now: datetime) -> Observation | None:
        if raw is None:
            return None
        if len(raw) > 4096:
            raise ValueError("Oversized snapshot")
        value = Observation.model_validate_json(raw)
        if value.event.source_id != self.source_id:
            raise ValueError("Snapshot source mismatch")
        age = (now - value.event.observed_at).total_seconds()
        return value if 0 <= age < self.retention_seconds else None

    def ingest(self, event: ReplayEvent, *, now: datetime) -> WriteOutcome:
        """Atomically store an observation and its guards, or return a bounded failure.

        A lost EXEC response returns unavailable; replaying the same event safely
        resolves to duplicate if Redis committed it. No local success is assumed.
        """
        _aware(now)
        event = ReplayEvent.model_validate(event.model_dump())
        age = (now - event.observed_at).total_seconds()
        if (
            event.source_id != self.source_id
            or (event.trip_id, event.service_date) not in self.fixture_trips
            or not 0 <= age < self.retention_seconds
        ):
            return "quarantined"
        key = self._key(event.trip_id, event.service_date, event.kind)
        identity = _digest(event.event_id)
        fingerprint = _digest(event.model_dump_json())
        for _ in range(self.max_attempts):
            try:
                with self.client.pipeline() as transaction:
                    transaction.watch(self.metadata_key, key)  # type: ignore[no-untyped-call]
                    raw_metadata = cast(bytes | str | None, transaction.get(self.metadata_key))
                    state = self._metadata(raw_metadata, now)
                    seen = state.seen.get(identity)
                    if seen is not None:
                        return "duplicate" if seen.fingerprint == fingerprint else "conflicting_id"
                    guard = state.guards.get(key)
                    if guard is not None and event.observed_at <= guard.observed_at:
                        return "out_of_order"
                    previous = self._observation(
                        cast(bytes | str | None, transaction.get(key)), now
                    )
                    if previous is not None and (
                        raw_metadata is None
                        or self._key(
                            previous.event.trip_id, previous.event.service_date, previous.event.kind
                        )
                        != key
                    ):
                        return "unavailable"
                    if (
                        previous is not None
                        and previous.event.position is not None
                        and event.position is not None
                        and previous.event.vehicle_id == event.vehicle_id
                    ):
                        seconds = (event.observed_at - previous.event.observed_at).total_seconds()
                        if (
                            seconds <= 0
                            or _distance(previous.event.position, event.position) / seconds
                            > self.max_speed_mps
                        ):
                            return "quarantined"
                    if len(state.seen) >= self.max_records or (
                        key not in state.guards and len(state.guards) >= self.max_records
                    ):
                        return "capacity"
                    expires = now + timedelta(seconds=self.retention_seconds)
                    state.seen[identity] = _Seen(fingerprint=fingerprint, expires_at=expires)
                    state.guards[key] = _Guard(observed_at=event.observed_at, expires_at=expires)
                    next_state = state.model_copy(update={"clock": now})
                    encoded = next_state.model_dump_json()
                    if len(encoded.encode()) > 524288:
                        return "capacity"
                    transaction.multi()
                    transaction.set(self.metadata_key, encoded, ex=self.retention_seconds)
                    # Observation-based TTL: delayed receipt cannot extend GPS retention.
                    transaction.set(
                        key,
                        Observation(event=event, received_at=now).model_dump_json(),
                        px=max(1, ceil((self.retention_seconds - age) * 1000)),
                    )
                    transaction.execute()
                    return "accepted"
            except WatchError:
                continue
            except (RedisError, ValueError):
                return "unavailable"
        return "contended"

    def snapshot(self, trip_id: str, day: date, *, now: datetime) -> TrackingSnapshot:
        """Read a consistent set of channels; outage/corruption fails closed."""
        _aware(now)
        if (trip_id, day) not in self.fixture_trips:
            raise ValueError("Unknown synthetic trip")
        keys = [self._key(trip_id, day, kind) for kind in ("vehicle", "trip_update", "alert")]
        for _ in range(self.max_attempts):
            try:
                with self.client.pipeline() as transaction:
                    transaction.watch(self.metadata_key, *keys)  # type: ignore[no-untyped-call]
                    raw_metadata = cast(bytes | str | None, transaction.get(self.metadata_key))
                    self._metadata(raw_metadata, now)
                    values = [
                        self._observation(cast(bytes | str | None, transaction.get(k)), now)
                        for k in keys
                    ]
                    if raw_metadata is None and any(v is not None for v in values):
                        raise ValueError("Missing ordering metadata")
                    transaction.multi()
                    transaction.ping()
                    transaction.execute()
                    for key, value in zip(keys, values, strict=True):
                        if (
                            value is not None
                            and self._key(
                                value.event.trip_id, value.event.service_date, value.event.kind
                            )
                            != key
                        ):
                            raise ValueError("Snapshot key mismatch")
                    return self._snapshot(values, now)
            except WatchError:
                continue
            except (RedisError, ValueError):
                break
        return TrackingSnapshot(storage_status="unavailable")

    def _snapshot(self, values: list[Observation | None], now: datetime) -> TrackingSnapshot:
        channels: list[ChannelSnapshot] = []
        for value in values:
            if value is None:
                channels.append(ChannelSnapshot())
                continue
            age = (now - value.event.observed_at).total_seconds()
            channels.append(
                ChannelSnapshot(
                    freshness="fresh" if age <= self.fresh_seconds else "stale",
                    observed_at=value.event.observed_at,
                    received_at=value.received_at,
                    observed_age_seconds=age,
                )
            )
        vehicle, trip, _ = values
        service: Service = "unknown"
        predicted = None
        if trip is not None and channels[1].freshness == "fresh":
            service = trip.event.service or "unknown"
            if service in {"scheduled", "delayed"} and trip.event.delay_seconds is not None:
                predicted = Prediction(delay_seconds=trip.event.delay_seconds)
        return TrackingSnapshot(
            storage_status="available",
            vehicle=channels[0],
            trip_update=channels[1],
            alert=channels[2],
            service=service,
            predicted=predicted,
            observed_position=vehicle.event.position
            if vehicle is not None and channels[0].freshness == "fresh"
            else None,
        )
