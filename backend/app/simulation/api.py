"""Standalone local operator prototype with synthetic vehicles and demo funds."""

import os
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from hmac import compare_digest
from importlib import import_module
from math import ceil
from pathlib import Path
from secrets import token_urlsafe
from threading import Lock
from time import monotonic, time
from typing import Annotated, Literal

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from .driver_auth import DriverSessions
from .mapbox import Mapbox, MapboxError, Point, StreetRoute, Track, meters
from .providers import FLEET, VehicleId, taxi_fare
from .replay_api import replay_router
from .tracking import ReplayLeg, SimulationStore


class Leg(BaseModel):
    origin: str
    destination: str
    minutes: int
    fare_inr: int = 0
    vehicle: VehicleId | None = None
    path: list[Point] = Field(default_factory=list)
    segment_seconds: list[float] = Field(default_factory=list)
    seconds: float | None = None
    source: Literal["fixture", "mapbox", "simulated_rail"] = "fixture"


class Route(BaseModel):
    id: str
    name: str
    legs: list[Leg]

    @property
    def fare(self) -> int:
        return sum(leg.fare_inr for leg in self.legs)


ORIGIN = "Whitefield"
DESTINATION = "KSR Bengaluru"
METRO = "Whitefield Metro"
MAJESTIC = "Majestic"
METRO_LEG = Leg(origin=METRO, destination=MAJESTIC, minutes=46, fare_inr=60, vehicle="metro-01")
LAST_WALK = Leg(origin=MAJESTIC, destination=DESTINATION, minutes=5)
ROUTES = {
    route.id: route
    for route in (
        Route(
            id="walk-metro",
            name="Walk and metro",
            legs=[
                Leg(origin=ORIGIN, destination=METRO, minutes=12),
                METRO_LEG,
                LAST_WALK,
            ],
        ),
        Route(
            id="cab-metro",
            name="Taxi and metro",
            legs=[
                Leg(origin=ORIGIN, destination=METRO, minutes=6, fare_inr=30, vehicle="cab-01"),
                METRO_LEG,
                LAST_WALK,
            ],
        ),
        Route(
            id="bus",
            name="BMTC bus",
            legs=[
                Leg(origin=ORIGIN, destination=MAJESTIC, minutes=78, fare_inr=30, vehicle="bus-01"),
                LAST_WALK,
            ],
        ),
    )
}


class Journey(BaseModel):
    id: str
    route: Route
    leg_index: int = 0
    stage: Literal["ready", "accepted", "boarded", "complete"] = "ready"
    ticket: str | None = None


class LedgerEntry(BaseModel):
    journey_id: str
    leg_index: int
    vehicle: VehicleId
    amount_inr: int


class Booking(BaseModel):
    route_id: str
    plan_id: str | None = None


class Plan(BaseModel):
    origin: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)


class MapPlan(BaseModel):
    plan_id: str
    routes: list[Route]


class Scan(BaseModel):
    journey_id: str
    leg_index: int
    ticket: str = Field(max_length=128)
    action: Literal["board", "exit"]


class Progress(BaseModel):
    journey_id: str
    leg_index: int


class StaffLogin(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=256)


WHITEFIELD_STATION: Point = (77.8251, 12.9957)
MAJESTIC_STATION: Point = (77.5727, 12.9757)
KNOWN_LOCATIONS: dict[str, Point] = {
    "whitefield": (77.7500, 12.9698),
    "ksr bengaluru": (77.5685, 12.9784),
}


def street_leg(
    route: StreetRoute,
    origin: str,
    destination: str,
    vehicle: VehicleId | None = None,
    fare: int = 0,
    extra_seconds: int = 0,
) -> Leg:
    seconds = max(1, route.duration + extra_seconds)
    return Leg(
        origin=origin,
        destination=destination,
        minutes=ceil(seconds / 60),
        fare_inr=fare,
        vehicle=vehicle,
        path=route.geometry.coordinates,
        segment_seconds=route.segment_seconds,
        seconds=seconds,
        source="mapbox",
    )


def map_routes(mapbox: Mapbox, payload: Plan) -> list[Route]:
    origin, destination = payload.origin.strip(), payload.destination.strip()
    if not origin or not destination:
        raise MapboxError(422, "Enter both Bengaluru locations")
    start = KNOWN_LOCATIONS.get(origin.casefold()) or mapbox.geocode(origin)
    end = KNOWN_LOCATIONS.get(destination.casefold()) or mapbox.geocode(destination)
    if meters(start, end) < 25:
        raise MapboxError(422, "Choose two different locations")
    road = mapbox.directions("driving-traffic", start, end)
    cab_fare = taxi_fare(road.distance)
    routes = [
        Route(
            id="cab-direct",
            name="Direct taxi",
            legs=[
                street_leg(road, origin, destination, "cab-01", cab_fare),
            ],
        ),
        Route(
            id="bus",
            name="Simulated BMTC",
            legs=[
                street_leg(road, origin, destination, "bus-01", 30, extra_seconds=600),
            ],
        ),
    ]
    station_a, station_b = WHITEFIELD_STATION, MAJESTIC_STATION
    name_a, name_b = METRO, MAJESTIC
    if meters(start, station_a) > meters(start, station_b):
        station_a, station_b = station_b, station_a
        name_a, name_b = name_b, name_a
    if meters(start, station_a) > 11000 or meters(end, station_b) > 4000:
        return routes
    rail = Leg(
        origin=name_a,
        destination=name_b,
        minutes=46,
        fare_inr=60,
        vehicle="metro-01",
        path=[station_a, station_b],
        seconds=46 * 60,
        source="simulated_rail",
    )
    try:
        last = (
            []
            if meters(station_b, end) < 25
            else [street_leg(mapbox.directions("walking", station_b, end), name_b, destination)]
        )
        access = (
            []
            if meters(start, station_a) < 25
            else [street_leg(mapbox.directions("walking", start, station_a), origin, name_a)]
        )
        routes.append(Route(id="walk-metro", name="Walk and metro", legs=[*access, rail, *last]))
        if access:
            first = mapbox.directions("driving-traffic", start, station_a)
            cab = street_leg(first, origin, name_a, "cab-01", taxi_fare(first.distance, minimum=30))
            routes.append(Route(id="cab-metro", name="Taxi and metro", legs=[cab, rail, *last]))
    except MapboxError as exc:
        if exc.status != 404:
            raise
    return routes


def create_demo(
    api_key: str | None = None,
    *,
    mapbox: Mapbox | None = None,
    clock: Callable[[], float] = monotonic,
    speed: int = 30,
    store: SimulationStore | None = None,
    wall_clock: Callable[[], float] = time,
    driver_passwords: Mapping[VehicleId, str] | None = None,
    integration_key: str | None = None,
) -> FastAPI:
    if not 1 <= speed <= 120:
        raise ValueError("Simulation speed must be between 1 and 120")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if mapbox is not None:
                mapbox.client.close()

    app = FastAPI(
        title="NammaMove operator simulation",
        description="Mapbox-backed routing, simulated fleet and demo INR",
        lifespan=lifespan,
    )
    key = api_key if api_key is not None else os.environ.get("NAMMAMOVE_DEMO_KEY")
    lock = Lock()
    scanner_keys = {vehicle: token_urlsafe(24) for vehicle in FLEET}
    driver_sessions = DriverSessions(driver_passwords or {}, clock)
    ledger: list[LedgerEntry] = []
    journey: Journey | None = None
    balance = 750
    held = 0
    pending: tuple[float, MapPlan] | None = None
    track: Track | None = None
    started: float | None = None
    ApiKey = Annotated[str | None, Header(alias="X-Demo-Key")]
    StaffToken = Annotated[str | None, Header(alias="X-Staff-Token")]

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, __: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": "Invalid request"}, status_code=422)

    def authorize(value: str | None, expected: str | None) -> None:
        if not expected or not value or not compare_digest(value.encode(), expected.encode()):
            raise HTTPException(401, "Invalid demo credential")

    def authorize_routes(value: str | None) -> None:
        if integration_key and value and compare_digest(value.encode(), integration_key.encode()):
            return
        authorize(value, key)

    def authorize_scanner(vehicle: VehicleId, api_key: str | None, session: str | None) -> None:
        if session is not None:
            driver_sessions.authorize(vehicle, session)
        else:
            authorize(api_key, scanner_keys[vehicle])

    def find_map_route(plan_id: str, route_id: str) -> Route | None:
        if pending is None or pending[0] <= clock() or pending[1].plan_id != plan_id:
            raise HTTPException(409, "Route plan expired. Search again.")
        return next((item for item in pending[1].routes if item.id == route_id), None)

    def replay_legs(plan_id: str, route_id: str) -> list[ReplayLeg]:
        with lock:
            route = find_map_route(plan_id, route_id)
        if route is None:
            raise HTTPException(404, "Unknown route")
        return [
            ReplayLeg(
                vehicle=leg.vehicle,
                source="mapbox" if leg.source == "mapbox" else "simulated_rail",
                seconds=leg.seconds or 1,
                points=leg.path,
                segment_seconds=leg.segment_seconds,
            )
            for leg in route.legs
        ]

    app.include_router(
        replay_router(store, lambda value: authorize(value, key), replay_legs, wall_clock, speed)
    )

    def current(journey_id: str, leg_index: int) -> Journey:
        if (
            journey is None
            or journey.id != journey_id
            or journey.leg_index != leg_index
            or journey.stage == "complete"
        ):
            raise HTTPException(409, "Leg is no longer active")
        return journey

    def prepare(active: Journey) -> None:
        nonlocal track, started
        track, started = None, None
        if active.stage != "complete":
            leg = active.route.legs[active.leg_index]
            if leg.path:
                track = Track.build(leg.path, leg.segment_seconds)
                if leg.vehicle is None:
                    started = clock()

    def advance(active: Journey) -> None:
        active.leg_index += 1
        active.ticket = None
        active.stage = "complete" if active.leg_index == len(active.route.legs) else "ready"
        prepare(active)

    def motion() -> dict[str, object] | None:
        if journey is None or track is None:
            return None
        leg = journey.route.legs[journey.leg_index]
        duration = leg.seconds or 1
        elapsed = 0.0 if started is None else max(0, clock() - started) * speed
        progress = min(elapsed / duration, 1)
        return {
            "journey_id": journey.id,
            "leg_index": journey.leg_index,
            "vehicle": leg.vehicle,
            "position": track.position(progress),
            "progress": progress,
            "remaining_simulation_seconds": ceil(max(0, duration - elapsed)),
            "phase": "waiting" if started is None else ("arrived" if progress == 1 else "moving"),
        }

    def require_arrival() -> None:
        position = motion()
        if position is not None and position["phase"] != "arrived":
            raise HTTPException(409, "Await simulated arrival before completing this leg")

    @app.get("/", include_in_schema=False)
    def console() -> FileResponse:
        return FileResponse(Path(__file__).with_name("console.html"))

    @app.get("/driver", include_in_schema=False)
    def driver() -> FileResponse:
        return FileResponse(Path(__file__).with_name("driver.html"))

    @app.post("/demo/v1/staff/login")
    def staff_login(payload: StaffLogin, response: Response) -> dict[str, str]:
        vehicle, token = driver_sessions.sign_in(payload.username, payload.password)
        response.headers["Cache-Control"] = "no-store"
        return {"vehicle": vehicle, "operator": FLEET[vehicle].operator, "session": token}

    @app.get("/demo/v1/fleet/{vehicle}/assignment")
    def assignment(vehicle: VehicleId, x_staff_token: StaffToken = None) -> dict[str, object]:
        driver_sessions.authorize(vehicle, x_staff_token)
        with lock:
            if journey is None or journey.stage == "complete":
                return {"assignment": None}
            leg = journey.route.legs[journey.leg_index]
            if leg.vehicle != vehicle:
                return {"assignment": None}
            return {
                "assignment": {
                    "journey_id": journey.id,
                    "leg_index": journey.leg_index,
                    "stage": journey.stage,
                    "origin": leg.origin,
                    "destination": leg.destination,
                    "minutes": leg.minutes,
                    "fare_inr": leg.fare_inr,
                    "motion": motion(),
                }
            }

    @app.post("/demo/v1/routes")
    def plan(payload: Plan, x_demo_key: ApiKey = None) -> list[Route]:
        authorize_routes(x_demo_key)
        if (payload.origin.strip().casefold(), payload.destination.strip().casefold()) != (
            ORIGIN.casefold(),
            DESTINATION.casefold(),
        ):
            raise HTTPException(404, "Demo corridor is Whitefield to KSR Bengaluru")
        return list(ROUTES.values())

    @app.post("/demo/v1/map/routes")
    def plan_map(payload: Plan, x_demo_key: ApiKey = None) -> MapPlan:
        nonlocal pending
        authorize_routes(x_demo_key)
        if mapbox is None:
            raise HTTPException(503, "Set MAPBOX_ACCESS_TOKEN in the operator server environment")
        try:
            routes = map_routes(mapbox, payload)
        except MapboxError as exc:
            raise HTTPException(exc.status, str(exc)) from None
        result = MapPlan(plan_id=token_urlsafe(12), routes=routes)
        with lock:
            pending = (clock() + 600, result)
        return result

    @app.get("/demo/v1/map/progress")
    def map_progress(x_demo_key: ApiKey = None) -> dict[str, object] | None:
        authorize(x_demo_key, key)
        with lock:
            return motion()

    @app.get("/demo/v1/state")
    def state(x_demo_key: ApiKey = None) -> dict[str, object]:
        authorize(x_demo_key, key)
        with lock:
            return {
                "mode": "simulation",
                "routing_source": "mapbox" if mapbox is not None else "fixture",
                "simulation_speed": speed,
                "tracking_configured": store is not None,
                "motion": motion(),
                "journey": journey.model_copy(deep=True) if journey else None,
                "balance_inr": balance,
                "held_inr": held,
                "available_inr": balance - held,
                "ledger": ledger.copy(),
                "fleet": list(FLEET.values()),
                "operator_credits_inr": {
                    vehicle: sum(entry.amount_inr for entry in ledger if entry.vehicle == vehicle)
                    for vehicle in FLEET
                },
            }

    @app.get("/demo/v1/journey/status")
    def journey_status(x_demo_key: ApiKey = None) -> dict[str, object] | None:
        authorize(x_demo_key, key)
        with lock:
            if journey is None:
                return None
            return {"id": journey.id, "leg_index": journey.leg_index, "stage": journey.stage}

    @app.get("/demo/v1/fleet/{vehicle}/credential")
    def credential(vehicle: VehicleId, x_demo_key: ApiKey = None) -> dict[str, str]:
        authorize(x_demo_key, key)
        return {"vehicle": vehicle, "scanner_key": scanner_keys[vehicle]}

    @app.post("/demo/v1/ticket/qr", response_class=Response)
    def ticket_qr(payload: Progress, x_demo_key: ApiKey = None) -> Response:
        authorize(x_demo_key, key)
        with lock:
            ticket = current(payload.journey_id, payload.leg_index).ticket
        if ticket is None:
            raise HTTPException(409, "Vehicle must accept this leg first")
        try:
            encoder = import_module("qrcode")
            svg = import_module("qrcode.image.svg")
        except ModuleNotFoundError as exc:
            raise HTTPException(503, "Install the operator demo QR requirement") from exc
        image = encoder.make(ticket, image_factory=svg.SvgPathImage)
        return Response(
            image.to_string(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"}
        )

    @app.post("/demo/v1/journeys", status_code=201)
    def book(payload: Booking, x_demo_key: ApiKey = None) -> Journey:
        nonlocal journey, held, pending
        authorize(x_demo_key, key)
        with lock:
            if payload.plan_id is not None:
                route = find_map_route(payload.plan_id, payload.route_id)
            elif mapbox is not None:
                raise HTTPException(409, "Select a route from a Mapbox plan")
            else:
                route = ROUTES.get(payload.route_id)
            if route is None:
                raise HTTPException(404, "Unknown route")
            if journey and journey.stage != "complete":
                raise HTTPException(409, "Finish the active demo journey")
            if balance < max(500, route.fare):
                raise HTTPException(409, "Insufficient demo balance")
            held = route.fare
            journey = Journey(id=token_urlsafe(12), route=route)
            pending = None
            prepare(journey)
            return journey.model_copy(deep=True)

    @app.post("/demo/v1/walk")
    def walk(payload: Progress, x_demo_key: ApiKey = None) -> Journey:
        authorize(x_demo_key, key)
        with lock:
            active = current(payload.journey_id, payload.leg_index)
            if active.route.legs[active.leg_index].vehicle is not None:
                raise HTTPException(409, "This leg requires a vehicle scan")
            require_arrival()
            advance(active)
            return active.model_copy(deep=True)

    @app.post("/demo/v1/fleet/{vehicle}/accept", response_model_exclude={"ticket"})
    def accept(
        vehicle: VehicleId,
        payload: Progress,
        x_demo_key: ApiKey = None,
        x_staff_token: StaffToken = None,
    ) -> Journey:
        authorize_scanner(vehicle, x_demo_key, x_staff_token)
        with lock:
            active = current(payload.journey_id, payload.leg_index)
            if active.route.legs[active.leg_index].vehicle != vehicle or active.stage != "ready":
                raise HTTPException(409, "Vehicle cannot accept this leg")
            active.ticket = token_urlsafe(24)
            active.stage = "accepted"
            return active.model_copy(deep=True)

    @app.post("/demo/v1/fleet/{vehicle}/scan", response_model_exclude={"ticket"})
    def scan(
        vehicle: VehicleId,
        payload: Scan,
        x_demo_key: ApiKey = None,
        x_staff_token: StaffToken = None,
    ) -> Journey:
        nonlocal balance, held, started
        authorize_scanner(vehicle, x_demo_key, x_staff_token)
        with lock:
            active = current(payload.journey_id, payload.leg_index)
            leg = active.route.legs[active.leg_index]
            if (
                leg.vehicle != vehicle
                or active.ticket is None
                or not compare_digest(active.ticket.encode(), payload.ticket.encode())
            ):
                raise HTTPException(409, "Invalid ticket for this vehicle and leg")
            if payload.action == "board" and active.stage == "accepted":
                active.stage = "boarded"
                if track is not None:
                    started = clock()
            elif payload.action == "exit" and active.stage == "boarded":
                require_arrival()
                ledger.append(
                    LedgerEntry(
                        journey_id=active.id,
                        leg_index=active.leg_index,
                        vehicle=vehicle,
                        amount_inr=leg.fare_inr,
                    )
                )
                balance -= leg.fare_inr
                held -= leg.fare_inr
                advance(active)
            else:
                raise HTTPException(409, "Scan is out of sequence")
            return active.model_copy(deep=True)

    return app


def configured_app() -> FastAPI:
    token = os.environ.get("MAPBOX_ACCESS_TOKEN", "").strip()
    path = os.environ.get("NAMMAMOVE_SIMULATION_DB")
    client = httpx.Client(base_url="https://api.mapbox.com", timeout=8) if token else None
    return create_demo(
        mapbox=Mapbox(token, client) if client is not None else None,
        speed=int(os.environ.get("NAMMAMOVE_SIMULATION_SPEED", "30")),
        store=SimulationStore(Path(path)) if path else None,
        driver_passwords={
            "cab-01": os.environ.get("NAMMAMOVE_TAXI_PASSWORD", ""),
            "metro-01": os.environ.get("NAMMAMOVE_METRO_PASSWORD", ""),
            "bus-01": os.environ.get("NAMMAMOVE_BMTC_PASSWORD", ""),
        },
        integration_key=os.environ.get("NAMMAMOVE_PARTNER_KEY"),
    )


app = configured_app()
