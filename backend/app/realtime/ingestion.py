"""Bounded synthetic FULL_DATASET transactions and explicitly driven worker queue.

No fetcher, API startup hook, durable log, source authorization or delivery channel.
"""

from collections import Counter, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import ceil
from threading import Lock
from typing import Literal, Protocol, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from redis.exceptions import RedisError, WatchError

from app.realtime.gtfs_rt import AlertInterval, FeedRejected, FixtureGtfsRtAdapter, SnapshotEvent
from app.realtime.redis_state import (
    Observation,
    RedisTrackingState,
    TrackingSnapshot,
    _aware,
    _digest,
)
from app.realtime.replay import Kind, _distance

FeedOutcome = Literal[
    "accepted",
    "duplicate",
    "out_of_order",
    "conflict",
    "rejected",
    "capacity",
    "quarantined",
    "contended",
    "unavailable",
]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class _Guard(_Model):
    observed_at: AwareDatetime
    fingerprint: str
    expires_at: AwareDatetime
    received_at: AwareDatetime
    vehicle_fingerprint: str | None = None


class _Record(_Model):
    key: str
    channel_key: str
    event_fingerprint: str = Field(pattern="^[a-f0-9]{64}$")
    trip_id: str
    day: date
    kind: Kind
    expires_at: AwareDatetime
    intervals: tuple[tuple[int | None, int | None], ...] = ()

    def active(self, now: datetime) -> bool:
        return not self.intervals or any(
            (start is None or start <= now.timestamp()) and (end is None or now.timestamp() < end)
            for start, end in self.intervals
        )


class _Manifest(_Model):
    policy: str
    header_at: AwareDatetime
    fingerprint: str
    received_at: AwareDatetime
    records: tuple[_Record, ...] = Field(max_length=1000)
    guards: dict[str, _Guard] = Field(max_length=1000)


class FeedSnapshot(_Model):
    data_mode: Literal["simulation"] = "simulation"
    header_at: AwareDatetime | None = None
    received_at: AwareDatetime | None = None
    feed_freshness: Literal["fresh", "stale", "unavailable"] = "unavailable"
    tracking: TrackingSnapshot
    notice: str = "Synthetic whole-feed snapshot; not live or verified service."


class RedisFullDataset:
    """One source/version's atomic snapshot, isolated from event-state keys.

    All replacements, deletions and the ordering manifest commit in one EXEC.
    Payloads have individual observation/interval TTLs; guards contain no GPS.
    """

    def __init__(
        self,
        adapter: FixtureGtfsRtAdapter,
        state: RedisTrackingState,
        *,
        expected_feed_version: str | None = None,
    ) -> None:
        if (
            adapter.source_id != state.source_id
            or adapter.fixture_trips != state.fixture_trips
            or adapter.retention_seconds != state.retention_seconds
            or expected_feed_version is not None
            and not 1 <= len(expected_feed_version) <= 100
        ):
            raise ValueError("Matching bounded synthetic adapter/state configuration required")
        self.adapter = adapter
        self.state = state
        self.client = state.client
        self.version = expected_feed_version
        self.prefix = state.prefix + "full:"
        self.key = self.prefix + "manifest"
        self.policy = _digest(state.policy + "|full-v2|" + repr(expected_feed_version))

    def _manifest(self, raw: bytes | str | None, now: datetime) -> _Manifest | None:
        if raw is None:
            return None
        if len(raw) > 1048576:
            raise ValueError("Oversized manifest")
        result = _Manifest.model_validate_json(raw)
        if result.policy != self.policy or now < result.received_at:
            raise ValueError("Policy or clock mismatch")
        if any(not record.key.startswith(self.prefix + "payload:") for record in result.records):
            raise ValueError("Invalid manifest scope")
        if len({r.key for r in result.records}) != len(result.records):
            raise ValueError("Duplicate generation records")
        if any((r.trip_id, r.day) not in self.state.fixture_trips for r in result.records):
            raise ValueError("Unknown generation scope")
        return result

    def _record(self, item: SnapshotEvent, generation: str) -> _Record:
        event = item.event
        # Alerts may coexist for the same trip; other channels must be unambiguous.
        identity = event.event_id if event.kind == "alert" else event.kind
        channel_key = _digest(f"{event.trip_id}|{event.service_date}|{identity}")
        key = self.prefix + "payload:" + generation + ":" + channel_key
        expires = event.observed_at + timedelta(seconds=self.state.retention_seconds)
        if item.intervals and all(p.end is not None for p in item.intervals):
            end = max(p.end for p in item.intervals if p.end is not None)
            if end < expires.timestamp():
                expires = datetime.fromtimestamp(end, tz=expires.tzinfo)
        return _Record(
            key=key,
            channel_key=channel_key,
            event_fingerprint=_digest(event.model_dump_json()),
            trip_id=event.trip_id,
            day=event.service_date,
            kind=event.kind,
            expires_at=expires,
            intervals=tuple((period.start, period.end) for period in item.intervals),
        )

    def _validate_observation(
        self, record: _Record, raw: bytes | None, manifest: _Manifest, now: datetime
    ) -> Observation | None:
        if raw is None and now < record.expires_at:
            raise ValueError("Incomplete snapshot generation")
        observation = self.state._observation(raw, now)
        if observation is None:
            if raw is not None and now < record.expires_at:
                raise ValueError("Unexpected observation clock for unexpired record")
            return None
        item = SnapshotEvent(
            event=observation.event,
            intervals=tuple(AlertInterval(start=start, end=end) for start, end in record.intervals),
        )
        if self._record(item, manifest.fingerprint) != record:
            raise ValueError("Generation payload integrity mismatch")
        if not observation.event.observed_at <= observation.received_at <= manifest.received_at:
            raise ValueError("Generation receipt mismatch")
        guard = manifest.guards.get(record.channel_key)
        if observation.event.kind != "alert" and (
            guard is None
            or guard.fingerprint != record.event_fingerprint
            or guard.observed_at != observation.event.observed_at
            or guard.received_at != observation.received_at
        ):
            raise ValueError("Observation ordering/receipt guard mismatch")
        return observation

    def ingest(self, payload: bytes, *, now: datetime) -> FeedOutcome:
        """Validate before touching Redis; failed feeds never withdraw valid evidence."""
        _aware(now)
        try:
            batch = self.adapter.decode(payload, now=now)
        except FeedRejected:
            return "rejected"
        if batch.feed_version != self.version:
            return "rejected"
        records = tuple(self._record(item, batch.fingerprint) for item in batch.snapshot_events)
        if len({record.key for record in records}) != len(records):
            return "rejected"
        if len(records) > self.state.max_records:
            return "capacity"
        for _ in range(self.state.max_attempts):
            try:
                with self.client.pipeline() as tx:
                    tx.watch(self.key)  # type: ignore[no-untyped-call]
                    previous = self._manifest(cast(bytes | None, tx.get(self.key)), now)
                    if previous is not None:
                        if batch.header_at < previous.header_at:
                            return "out_of_order"
                        if (
                            batch.header_at == previous.header_at
                            and batch.fingerprint != previous.fingerprint
                        ):
                            return "conflict"
                    guards = (
                        {}
                        if previous is None
                        else {
                            key: guard
                            for key, guard in previous.guards.items()
                            if now < guard.expires_at
                        }
                    )
                    old_records = {} if previous is None else {r.key: r for r in previous.records}
                    old_keys = list(old_records)
                    if old_keys:
                        tx.watch(*old_keys)  # type: ignore[no-untyped-call]
                    raw_values = cast(list[bytes | None], tx.mget(old_keys)) if old_keys else []
                    old_values = dict(zip(old_keys, raw_values, strict=True))
                    old_channels = {r.channel_key: r.key for r in old_records.values()}
                    # Validate the whole previous generation before any deletion, even for omissions.
                    for record in old_records.values():
                        if old_values[record.key] is None and now < record.expires_at:
                            # A concurrent replacement may have just removed this generation.
                            # Validate WATCH before classifying it as missing/corrupt state.
                            tx.multi()
                            tx.ping()
                            tx.execute()
                            return "unavailable"
                        assert previous is not None
                        self._validate_observation(record, old_values[record.key], previous, now)
                    if previous is not None and batch.header_at == previous.header_at:
                        # Acknowledging an ambiguous commit requires an intact generation.
                        tx.multi()
                        tx.ping()
                        tx.execute()
                        return "duplicate"
                    for item, record in zip(batch.snapshot_events, records, strict=True):
                        event = item.event
                        if event.kind == "alert":
                            continue
                        fingerprint = _digest(event.model_dump_json())
                        guard = guards.get(record.channel_key)
                        if guard is not None:
                            if event.observed_at < guard.observed_at:
                                return "out_of_order"
                            if (
                                event.observed_at == guard.observed_at
                                and fingerprint != guard.fingerprint
                            ):
                                return "conflict"
                        raw = old_values.get(old_channels.get(record.channel_key, ""))
                        old = self.state._observation(raw, now)
                        if (
                            old is None
                            and guard is not None
                            and event.position is not None
                            and event.vehicle_id is not None
                            and guard.vehicle_fingerprint == _digest(event.vehicle_id)
                            and event.observed_at > guard.observed_at
                        ):
                            # Omission removes GPS payloads, not permission to bypass speed checks.
                            # No comparison baseline: quarantine until guard expiry or reassignment.
                            return "quarantined"
                        if (
                            old is not None
                            and old.event.position is not None
                            and event.position is not None
                        ):
                            if old.event.vehicle_id == event.vehicle_id:
                                seconds = (
                                    event.observed_at - old.event.observed_at
                                ).total_seconds()
                                if (
                                    seconds > 0
                                    and _distance(old.event.position, event.position) / seconds
                                    > self.state.max_speed_mps
                                ):
                                    return "quarantined"
                        # Identical observations never renew their receipt-retained guard.
                        if guard is None or event.observed_at > guard.observed_at:
                            guards[record.channel_key] = _Guard(
                                observed_at=event.observed_at,
                                fingerprint=fingerprint,
                                expires_at=now + timedelta(seconds=self.state.retention_seconds),
                                received_at=now,
                                vehicle_fingerprint=_digest(event.vehicle_id)
                                if event.vehicle_id is not None
                                else None,
                            )
                    if len(guards) > self.state.max_records:
                        return "capacity"
                    manifest = _Manifest(
                        policy=self.policy,
                        header_at=batch.header_at,
                        fingerprint=batch.fingerprint,
                        received_at=now,
                        records=records,
                        guards=guards,
                    )
                    encoded = manifest.model_dump_json()
                    if len(encoded.encode()) > 1048576:
                        return "capacity"
                    tx.multi()
                    if old_keys:
                        tx.delete(*old_keys)
                    for item, record in zip(batch.snapshot_events, records, strict=True):
                        event = item.event
                        remaining = (record.expires_at - now).total_seconds()
                        if remaining <= 0:
                            continue
                        old = self.state._observation(
                            old_values.get(old_channels.get(record.channel_key, "")), now
                        )
                        guard = guards.get(record.channel_key)
                        receipt = (
                            guard.received_at
                            if guard is not None
                            else old.received_at
                            if old is not None and old.event == event
                            else now
                        )
                        tx.set(
                            record.key,
                            Observation(event=event, received_at=receipt).model_dump_json(),
                            px=max(1, ceil(remaining * 1000)),
                        )
                    # Retain header ordering beyond payload expiry, but never indefinitely.
                    tx.set(self.key, encoded, ex=self.state.retention_seconds)
                    tx.execute()
                    return "accepted"
            except WatchError:
                continue
            except (RedisError, ValueError):
                return "unavailable"
        return "contended"

    def snapshot(self, trip_id: str, day: date, *, now: datetime) -> FeedSnapshot:
        """Read the entire manifest generation atomically; interval expiry needs no poller."""
        _aware(now)
        if (trip_id, day) not in self.state.fixture_trips:
            raise ValueError("Unknown synthetic trip")
        for _ in range(self.state.max_attempts):
            try:
                with self.client.pipeline() as tx:
                    tx.watch(self.key)  # type: ignore[no-untyped-call]
                    manifest = self._manifest(cast(bytes | None, tx.get(self.key)), now)
                    if manifest is None:
                        return FeedSnapshot(tracking=TrackingSnapshot(storage_status="available"))
                    records = list(manifest.records)
                    keys = [r.key for r in records]
                    if keys:
                        tx.watch(*keys)  # type: ignore[no-untyped-call]
                    raw = cast(list[bytes | None], tx.mget(keys)) if keys else []
                    values: list[Observation | None] = [None, None, None]
                    for record, value in zip(records, raw, strict=True):
                        observation = self._validate_observation(record, value, manifest, now)
                        if observation is None:
                            continue
                        event = observation.event
                        if (event.trip_id, event.service_date, event.kind) != (
                            record.trip_id,
                            record.day,
                            record.kind,
                        ):
                            raise ValueError("Payload scope mismatch")
                        if record.trip_id == trip_id and record.day == day and record.active(now):
                            index = ("vehicle", "trip_update", "alert").index(record.kind)
                            values[index] = observation
                    tx.multi()
                    tx.ping()
                    tx.execute()
                    age = (now - manifest.header_at).total_seconds()
                    return FeedSnapshot(
                        header_at=manifest.header_at,
                        received_at=manifest.received_at,
                        feed_freshness="fresh"
                        if age <= self.state.fresh_seconds
                        else "stale"
                        if age < self.state.retention_seconds
                        else "unavailable",
                        tracking=self.state._snapshot(values, now),
                    )
            except WatchError:
                continue
            except (RedisError, ValueError):
                break
        return FeedSnapshot(tracking=TrackingSnapshot(storage_status="unavailable"))


@dataclass(frozen=True)
class _Job:
    payload: bytes
    submitted_at: datetime
    due_at: datetime
    attempts: int = 0


class WorkerResult(_Model):
    data_mode: Literal["simulation"] = "simulation"
    outcome: FeedOutcome
    attempts: int
    retry_scheduled: bool


class FeedStore(Protocol):
    adapter: FixtureGtfsRtAdapter

    def ingest(self, payload: bytes, *, now: datetime) -> FeedOutcome: ...


class FullDatasetWorker:
    """Explicit tick-driven local queue: no threads/timers/network start implicitly.

    Capacity includes in-flight and retry jobs. No oldest-job eviction; producers
    must retain and resubmit on backpressure. Process restart loses this queue.
    """

    def __init__(
        self,
        store: FeedStore,
        *,
        max_jobs: int = 8,
        max_bytes: int = 2097152,
        max_attempts: int = 3,
    ) -> None:
        if not 1 <= max_jobs <= 64 or not 1 <= max_bytes <= 8388608 or not 1 <= max_attempts <= 5:
            raise ValueError("Invalid bounded queue/retry policy")
        self.store = store
        self.max_jobs = max_jobs
        self.max_bytes = max_bytes
        self.max_attempts = max_attempts
        self._jobs: deque[_Job] = deque()
        self._lock = Lock()
        self._processing = Lock()
        self._count = 0
        self._bytes = 0
        self.metrics: Counter[str] = Counter()

    @property
    def pending(self) -> int:
        """Queued plus in-flight jobs, including retries."""
        with self._lock:
            return self._count

    def submit(
        self, payload: bytes, *, now: datetime
    ) -> Literal["queued", "backpressure", "rejected"]:
        """Nonblocking bounded admission, without decoding or retaining oversized data."""
        _aware(now)
        if (
            not isinstance(payload, bytes)
            or not payload
            or len(payload) > self.store.adapter.max_bytes
        ):
            return "rejected"
        with self._lock:
            if self._count >= self.max_jobs or self._bytes + len(payload) > self.max_bytes:
                self.metrics["backpressure"] += 1
                return "backpressure"
            self._jobs.append(_Job(payload=payload, submitted_at=now, due_at=now))
            self._count += 1
            self._bytes += len(payload)
            return "queued"

    def run_one(self, *, now: datetime) -> WorkerResult | None:
        """Run at most one due job; retry after 1/2/4/8 seconds, never sleep internally."""
        _aware(now)
        if not self._processing.acquire(blocking=False):
            return None
        try:
            with self._lock:
                job = next((j for j in self._jobs if j.due_at <= now), None)
                if job is None:
                    return None
                self._jobs.remove(job)
            try:
                outcome = self.store.ingest(job.payload, now=now)
            except Exception:
                # Do not strand a removed job's reserved capacity or expose raw errors.
                # Unknown failures are fail-closed and use the same finite retry budget.
                outcome = "unavailable"
                with self._lock:
                    self.metrics["worker_error"] += 1
            attempts = job.attempts + 1
            retry = outcome in {"unavailable", "contended"} and attempts < self.max_attempts
            with self._lock:
                self.metrics[outcome] += 1
                if retry:
                    self._jobs.append(
                        _Job(
                            payload=job.payload,
                            submitted_at=job.submitted_at,
                            due_at=now + timedelta(seconds=2 ** (attempts - 1)),
                            attempts=attempts,
                        )
                    )
                else:
                    self._count -= 1
                    self._bytes -= len(job.payload)
                    if outcome in {"unavailable", "contended"}:
                        self.metrics["retry_exhausted"] += 1
            return WorkerResult(outcome=outcome, attempts=attempts, retry_scheduled=retry)
        finally:
            self._processing.release()
