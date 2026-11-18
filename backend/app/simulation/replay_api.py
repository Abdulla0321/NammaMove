"""Authenticated API for independent, durable simulation runs."""

from collections.abc import Callable
from sqlite3 import Error as StorageError
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from .tracking import (
    PositionSample,
    ReplayLeg,
    SamplePage,
    SimulationRun,
    SimulationStore,
    Timeline,
)

ApiKey = Annotated[str | None, Header(alias="X-Demo-Key")]


class StartSimulation(BaseModel):
    plan_id: str = Field(max_length=64)
    route_id: str = Field(max_length=64)
    speed: int | None = Field(default=None, ge=1, le=120)


def replay_router(
    store: SimulationStore | None,
    authorize: Callable[[str | None], None],
    resolve: Callable[[str, str], list[ReplayLeg]],
    clock: Callable[[], float],
    speed: int,
) -> APIRouter:
    router = APIRouter(prefix="/demo/v1/simulations", tags=["simulation tracking"])

    def database(key: str | None) -> SimulationStore:
        authorize(key)
        if store is None:
            raise HTTPException(503, "Configure NAMMAMOVE_SIMULATION_DB to enable durable runs")
        return store

    def load(run_id: UUID, key: str | None) -> SimulationRun:
        try:
            run = database(key).get(run_id)
        except StorageError:
            raise HTTPException(503, "Simulation database unavailable") from None
        if run is None:
            raise HTTPException(404, "Simulation not found")
        return run

    @router.post("", status_code=201)
    def start(payload: StartSimulation, x_demo_key: ApiKey = None) -> SimulationRun:
        target = database(x_demo_key)
        legs = resolve(payload.plan_id, payload.route_id)
        try:
            return target.start(payload.route_id, legs, clock(), payload.speed or speed)
        except StorageError:
            raise HTTPException(503, "Simulation database unavailable") from None

    @router.get("")
    def recent(
        limit: Annotated[int, Query(ge=1, le=100)] = 25, x_demo_key: ApiKey = None
    ) -> list[UUID]:
        try:
            return database(x_demo_key).recent(limit)
        except StorageError:
            raise HTTPException(503, "Simulation database unavailable") from None

    @router.get("/{run_id}")
    def run(run_id: UUID, x_demo_key: ApiKey = None) -> SimulationRun:
        return load(run_id, x_demo_key)

    @router.get("/{run_id}/position")
    def position(run_id: UUID, x_demo_key: ApiKey = None) -> PositionSample:
        timeline = Timeline.build(load(run_id, x_demo_key))
        return timeline.sample(timeline.latest_tick(clock()))

    @router.get("/{run_id}/positions")
    def positions(
        run_id: UUID,
        after: Annotated[int, Query(ge=-1)] = -1,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        x_demo_key: ApiKey = None,
    ) -> SamplePage:
        timeline = Timeline.build(load(run_id, x_demo_key))
        end = min(timeline.latest_tick(clock()), after + limit)
        samples = [timeline.sample(tick) for tick in range(after + 1, end + 1)]
        return SamplePage(samples=samples, next_after=samples[-1].tick if samples else after)

    return router
