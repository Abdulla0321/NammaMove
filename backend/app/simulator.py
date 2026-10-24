from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .engine import EDGES, Incident, Journey, route, service_state

router = APIRouter()


def require_simulation(request: Request) -> None:
    if not request.app.state.settings.allow_simulation:
        raise HTTPException(404, "Simulation is disabled")


class RouteRequest(BaseModel):
    origin: str = Field(min_length=1, max_length=160)
    destination: str = Field(min_length=1, max_length=160)
    incidents: list["IncidentRequest"] = Field(default_factory=list, max_length=50)


class IncidentRequest(BaseModel):
    id: str
    affected_edges: list[str]
    kind: str = "disruption"
    verified: bool = False
    delay_minutes: int = Field(default=0, ge=0, le=1440)
    blocked: bool = False


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "simulation"}


@router.get("/network", dependencies=[Depends(require_simulation)])
def network() -> dict[str, object]:
    return {
        "stops": sorted(set([x.source for x in EDGES] + [x.target for x in EDGES])),
        "edges": [e.__dict__ for e in EDGES],
        "mode": "simulation",
    }


@router.post("/journeys/plan", dependencies=[Depends(require_simulation)])
def plan(req: RouteRequest) -> Journey:
    incidents = [
        Incident(i.id, tuple(i.affected_edges), i.kind, i.verified, i.delay_minutes, i.blocked)
        for i in req.incidents
    ]
    result = route(req.origin, req.destination, incidents)
    if result is None:
        raise HTTPException(status_code=404, detail="No route found in the sample network")
    return result


@router.get("/services/status", dependencies=[Depends(require_simulation)])
def status(
    last_seen_seconds: Annotated[int | None, Query(ge=0)] = None, operator_cancelled: bool = False
) -> dict[str, str]:
    service, feed = service_state(last_seen_seconds, operator_cancelled)
    return {
        "serviceStatus": service,
        "feedStatus": feed,
        "notice": "Missing GPS data alone never confirms cancellation.",
    }
