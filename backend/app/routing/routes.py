from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import current_principal
from .contracts import PlanRequest, PlanResponse
from .provider import RoutingProvider

router = APIRouter(prefix="/v1/routing", dependencies=[Depends(current_principal)])


@router.post("/plan", response_model=PlanResponse)
def plan(payload: PlanRequest, request: Request) -> PlanResponse:
    provider: RoutingProvider | None = request.app.state.routing_provider
    settings = request.app.state.settings
    if provider is None or not settings.allow_simulation or settings.app_env == "production":
        raise HTTPException(503, "Synthetic schedule routing is unavailable")
    return provider.plan(payload)
