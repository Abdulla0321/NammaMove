"""Explicit bounded synthetic retention/recovery ticks; never API startup work."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Event, Lock
from typing import Literal

from app.realtime.durable import DurableIngestion
from app.realtime.redis_state import _aware


@dataclass(frozen=True)
class MaintenanceResult:
    """Sanitized operational result with no payloads or connection details."""

    status: str
    attempt: int
    evidence: int = 0
    payloads: int = 0
    data_mode: Literal["simulation"] = "simulation"


class IngestionMaintenance:
    """One preconfigured source per scheduler; SQL/RLS remains authoritative.

    Operators explicitly construct one scheduler per authorized source (no source
    discovery). Each tick performs at most one retention transaction and one
    recovery transaction. Retry state is bounded and local, not a durable queue.
    """

    def __init__(
        self, store: DurableIngestion, *, interval_seconds: int = 60, max_attempts: int = 4
    ) -> None:
        if not 1 <= interval_seconds <= 900 or not 1 <= max_attempts <= 5:
            raise ValueError("Invalid bounded maintenance policy")
        self.store = store
        self.interval_seconds = interval_seconds
        self.max_attempts = max_attempts
        self.due_at: datetime | None = None
        self.last_tick: datetime | None = None
        self.attempt = 0
        self._mutex = Lock()

    def tick(self, *, now: datetime) -> MaintenanceResult:
        """Apply retention and recover with original TTLs; never sleep internally."""
        with self._mutex:
            return self._tick(now=now)

    def _tick(self, *, now: datetime) -> MaintenanceResult:
        _aware(now)
        if self.last_tick is not None and now < self.last_tick:
            raise ValueError("Maintenance clock regression")
        self.last_tick = now
        if self.due_at is not None and now < self.due_at:
            return MaintenanceResult("idle", self.attempt)
        self.attempt += 1
        counts = {"evidence": 0, "payloads": 0}
        try:
            counts = self.store.retain(now=now, apply=True)
            success = self.store.recover(now=now)
        except Exception:
            # No exception text/provider content/connection details are retained.
            success = False
        attempt = self.attempt
        if success or attempt >= self.max_attempts:
            self.attempt = 0
            self.due_at = now + timedelta(seconds=self.interval_seconds)
            status = "completed" if success else "exhausted"
        else:
            self.due_at = now + timedelta(seconds=2 ** (attempt - 1))
            status = "retry"
        return MaintenanceResult(status, attempt, counts["evidence"], counts["payloads"])

    def run(
        self,
        stop: Event,
        *,
        max_ticks: int,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Explicit stoppable loop with a caller-chosen finite execution budget."""
        if not 1 <= max_ticks <= 86400:
            raise ValueError("Invalid maintenance loop budget")
        for _ in range(max_ticks):
            if stop.is_set():
                return
            self.tick(now=clock())
            if stop.wait(1):
                return
