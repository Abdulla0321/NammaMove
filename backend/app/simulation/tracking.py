"""Persistent, deterministic simulation runs and per-second position replay."""

from bisect import bisect_right
from contextlib import closing
from dataclasses import dataclass
from math import ceil, floor
from pathlib import Path
from sqlite3 import Connection, connect
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .mapbox import Point, Track


class ReplayLeg(BaseModel):
    vehicle: str | None
    source: Literal["mapbox", "simulated_rail"]
    seconds: Annotated[float, Field(gt=0, le=172800)]
    points: list[Point] = Field(min_length=2, max_length=30000)
    segment_seconds: list[float] = Field(default_factory=list)


class SimulationRun(BaseModel):
    id: UUID
    route_id: str
    started_at: float
    speed: Annotated[int, Field(ge=1, le=120)]
    legs: list[ReplayLeg] = Field(min_length=1, max_length=10)


class PositionSample(BaseModel):
    id: str
    simulation_id: UUID
    tick: int
    observed_at: float
    leg_index: int
    vehicle: str | None
    source: Literal["mapbox", "simulated_rail"]
    position: Point
    progress: float
    phase: Literal["moving", "complete"]


class SamplePage(BaseModel):
    samples: list[PositionSample]
    next_after: int


@dataclass(frozen=True)
class Timeline:
    run: SimulationRun
    ends: list[float]
    tracks: list[Track]

    @classmethod
    def build(cls, run: SimulationRun) -> "Timeline":
        ends: list[float] = []
        total = 0.0
        for leg in run.legs:
            total += leg.seconds
            ends.append(total)
        return cls(run, ends, [Track.build(leg.points, leg.segment_seconds) for leg in run.legs])

    def latest_tick(self, now: float) -> int:
        elapsed = max(0, now - self.run.started_at) * self.run.speed
        return ceil(self.ends[-1]) if elapsed >= self.ends[-1] else floor(elapsed)

    def sample(self, tick: int) -> PositionSample:
        end = self.ends[-1]
        elapsed = min(tick, end)
        index = min(bisect_right(self.ends, elapsed), len(self.run.legs) - 1)
        leg = self.run.legs[index]
        leg_start = self.ends[index - 1] if index else 0
        progress = 1.0 if elapsed == end else (elapsed - leg_start) / (self.ends[index] - leg_start)
        return PositionSample(
            id=f"{self.run.id}:{tick}",
            simulation_id=self.run.id,
            tick=tick,
            observed_at=self.run.started_at + elapsed / self.run.speed,
            leg_index=index,
            vehicle=leg.vehicle,
            source=leg.source,
            position=self.tracks[index].position(progress),
            progress=progress,
            phase="complete" if elapsed == end else "moving",
        )


class SimulationStore:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        """Provision the standalone database explicitly before starting the API."""
        with closing(connect(self.path)) as db, db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS simulation_runs (
                    id TEXT PRIMARY KEY,
                    started_at REAL NOT NULL,
                    definition TEXT NOT NULL
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS simulation_start ON simulation_runs(started_at DESC, id DESC)"
            )

    def connection(self) -> Connection:
        return connect(self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5)

    def start(self, route_id: str, legs: list[ReplayLeg], now: float, speed: int) -> SimulationRun:
        run = SimulationRun(id=uuid4(), route_id=route_id, started_at=now, speed=speed, legs=legs)
        with closing(self.connection()) as db, db:
            db.execute(
                "INSERT INTO simulation_runs VALUES (?, ?, ?)",
                (str(run.id), run.started_at, run.model_dump_json()),
            )
        return run

    def get(self, run_id: UUID) -> SimulationRun | None:
        with closing(self.connection()) as db:
            row = db.execute(
                "SELECT definition FROM simulation_runs WHERE id = ?", (str(run_id),)
            ).fetchone()
        return SimulationRun.model_validate_json(row[0]) if row else None

    def recent(self, limit: int) -> list[UUID]:
        with closing(self.connection()) as db:
            rows = db.execute(
                "SELECT id FROM simulation_runs ORDER BY started_at DESC, id DESC LIMIT ?",
                (limit,),
            )
            return [UUID(row[0]) for row in rows]
