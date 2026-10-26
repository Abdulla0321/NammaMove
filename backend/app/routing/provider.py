"""Bounded OTP 2.7 GraphQL adapter. No silent simulator or stale-graph fallback."""

import json
import math
import threading
import time
from datetime import timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from .contracts import GraphManifest, Itinerary, Leg, PlanRequest, PlanResponse, Point

QUERY = """query Plan($origin: PlanLabeledLocationInput!, $destination: PlanLabeledLocationInput!,
$dateTime: PlanDateTimeInput!, $modes: PlanModesInput!, $preferences: PlanPreferencesInput!, $window: Duration!) {
 planConnection(origin:$origin,destination:$destination,dateTime:$dateTime,modes:$modes,
 preferences:$preferences,first:16,searchWindow:$window) {
 routingErrors { code }
 edges { node { start end legs { mode distance start {scheduledTime} end {scheduledTime}
 from {lat lon} to {lat lon} route {gtfsId} trip {gtfsId directionId wheelchairAccessible} } } }
 } }"""


class RoutingProvider(Protocol):
    manifest: GraphManifest

    def plan(self, request: PlanRequest) -> PlanResponse: ...


def point(manifest: GraphManifest, value: Point) -> Point:
    if value.stop_id is not None:
        if value.stop_id not in manifest.stops:
            raise HTTPException(422, "Unknown stop in this graph version")
        return manifest.stops[value.stop_id]
    return value


def distance(a: Point, b: Point) -> float:
    assert (
        a.latitude is not None
        and a.longitude is not None
        and b.latitude is not None
        and b.longitude is not None
    )
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(b.longitude - a.longitude)
    return (
        6371000
        * 2
        * math.asin(
            min(
                1,
                math.sqrt(
                    math.sin(dlat / 2) ** 2
                    + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
                ),
            )
        )
    )


class OTPProvider:
    def __init__(
        self, url: str, manifest: GraphManifest, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        self.url = url.rstrip("/") + "/otp/gtfs/v1"
        self.manifest = manifest
        self.transport = transport
        self.slots = threading.BoundedSemaphore(4)

    def response(
        self, request: PlanRequest, itineraries: list[Itinerary], reason: str | None = None
    ) -> PlanResponse:
        return PlanResponse(
            graph_id=self.manifest.graph_id,
            graph_sha256=self.manifest.graph_sha256,
            source_attribution=self.manifest.attribution,
            source_license=self.manifest.license_id,
            otp_version=self.manifest.otp_version,
            status="ok" if itineraries else "no_route",
            reason=reason,
            preference=request.preference,
            itineraries=itineraries,
        )

    def variables(
        self, request: PlanRequest, origin: Point, destination: Point
    ) -> dict[str, object]:
        def location(value: Point) -> dict[str, object]:
            return {
                "location": {
                    "coordinate": {"latitude": value.latitude, "longitude": value.longitude}
                }
            }

        transit = [{"mode": mode} for mode in request.modes if mode != "WALK"]
        modes: dict[str, object] = {
            "direct": ["WALK"],
            "directOnly": not transit,
            "transitOnly": request.transit_required,
            "transit": {
                "access": ["WALK"],
                "egress": ["WALK"],
                "transfer": ["WALK"],
                "transit": transit,
            },
        }
        return {
            "origin": location(origin),
            "destination": location(destination),
            "dateTime": {
                "latestArrival" if request.arrive_by else "earliestDeparture": (
                    request.when + timedelta(minutes=10) if request.arrive_by else request.when
                ).isoformat()
            },
            "window": "PT130M" if request.arrive_by else "PT2H",
            "modes": modes,
            "preferences": {
                "accessibility": {"wheelchair": {"enabled": request.wheelchair}},
                "transit": {
                    "transfer": {"maximumTransfers": request.max_transfers, "slack": "PT60S"},
                    "timetable": {"excludeRealTimeUpdates": True},
                },
                "street": {"walk": {"speed": 1.3}},
            },
        }

    def fetch(self, variables: dict[str, object]) -> dict[str, Any]:
        started = time.monotonic()
        try:
            with httpx.Client(
                transport=self.transport,
                timeout=httpx.Timeout(1.5),
                follow_redirects=False,
                trust_env=False,
            ) as client:
                with client.stream(
                    "POST", self.url, json={"query": QUERY, "variables": variables}
                ) as response:
                    if response.status_code != 200:
                        raise ValueError("Provider HTTP failure")
                    payload = bytearray()
                    for chunk in response.iter_bytes():
                        payload.extend(chunk)
                        if len(payload) > 2_000_000 or time.monotonic() - started > 1.5:
                            raise ValueError("Provider budget exceeded")
            data = json.loads(payload)
            if not isinstance(data, dict) or data.get("errors"):
                raise ValueError("GraphQL failure")
            connection = data["data"]["planConnection"]
            if (
                not isinstance(connection, dict)
                or not isinstance(connection.get("edges"), list)
                or len(connection["edges"]) > 16
            ):
                raise ValueError("Provider contract failure")
            allowed_errors = {
                "LOCATION_NOT_FOUND",
                "NO_STOPS_IN_RANGE",
                "NO_TRANSIT_CONNECTION",
                "NO_TRANSIT_CONNECTION_IN_SEARCH_WINDOW",
                "OUTSIDE_BOUNDS",
                "OUTSIDE_SERVICE_PERIOD",
                "WALKING_BETTER_THAN_TRANSIT",
            }
            if not isinstance(connection.get("routingErrors"), list) or any(
                not isinstance(error, dict) or error.get("code") not in allowed_errors
                for error in connection["routingErrors"]
            ):
                raise ValueError("Provider error contract failure")
            return connection
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            raise HTTPException(503, "Routing provider unavailable or incompatible") from None

    def normalize(self, raw: dict[str, Any], request: PlanRequest) -> Itinerary | None:
        from pydantic import AwareDatetime, TypeAdapter

        timestamp = TypeAdapter(AwareDatetime)
        start = timestamp.validate_python(raw["start"])
        end = timestamp.validate_python(raw["end"])
        if end < start or not isinstance(raw["legs"], list) or not 1 <= len(raw["legs"]) <= 64:
            raise ValueError("Invalid itinerary")
        legs = []
        for item in raw["legs"]:
            trip = item.get("trip") or {}
            route = item.get("route") or {}
            legs.append(
                Leg(
                    mode=item["mode"],
                    start=item["start"]["scheduledTime"],
                    end=item["end"]["scheduledTime"],
                    distance_m=item["distance"],
                    from_lat=item["from"]["lat"],
                    from_lon=item["from"]["lon"],
                    to_lat=item["to"]["lat"],
                    to_lon=item["to"]["lon"],
                    route_id=route.get("gtfsId"),
                    trip_id=trip.get("gtfsId"),
                    direction_id=trip.get("directionId"),
                    wheelchair_status=trip.get("wheelchairAccessible"),
                )
            )
        for requested, returned in (
            (
                point(self.manifest, request.origin),
                Point(latitude=legs[0].from_lat, longitude=legs[0].from_lon),
            ),
            (
                point(self.manifest, request.destination),
                Point(latitude=legs[-1].to_lat, longitude=legs[-1].to_lon),
            ),
        ):
            if distance(requested, returned) > 50:
                raise ValueError("Provider returned different endpoints")
        if (not request.arrive_by and start > request.when + timedelta(hours=2)) or (
            request.arrive_by and end < request.when - timedelta(hours=2)
        ):
            return None
        if start != legs[0].start or end != legs[-1].end:
            raise ValueError("Provider timestamp mismatch")
        for previous, next_leg in zip(legs, legs[1:]):
            if (
                next_leg.start < previous.end
                or distance(
                    Point(latitude=previous.to_lat, longitude=previous.to_lon),
                    Point(latitude=next_leg.from_lat, longitude=next_leg.from_lon),
                )
                > 50
            ):
                raise ValueError("Disconnected or overlapping legs")
        # OTP 2.7 can miss an arrival-boundary connection (real fixture regression).
        # Query a padded window, then enforce the caller's exact deadline here.
        if request.arrive_by and end > request.when:
            return None
        if not request.arrive_by and start < request.when:
            raise ValueError("Provider violated time bound")
        transit = [leg for leg in legs if leg.mode != "WALK"]
        walking = sum(leg.distance_m for leg in legs if leg.mode == "WALK")
        if (
            walking > request.max_walk_m + 0.05
            or ("WALK" not in request.modes and walking > 0.05)
            or any(leg.mode not in request.modes for leg in transit)
            or max(0, len(transit) - 1) > request.max_transfers
            or (request.transit_required and not transit)
        ):
            return None
        for previous, next_leg in zip(transit, transit[1:]):
            between = sum(
                (leg.end - leg.start).total_seconds()
                for leg in legs
                if leg.mode == "WALK" and leg.start >= previous.end and leg.end <= next_leg.start
            )
            if (next_leg.start - previous.end).total_seconds() < between + 60:
                raise ValueError("Insufficient transfer slack")
        if request.wheelchair and any(leg.wheelchair_status != "POSSIBLE" for leg in transit):
            return None
        fares = [
            self.manifest.route_fares_inr.get((leg.route_id or "").split(":")[-1])
            for leg in transit
        ]
        total = (
            None
            if any(value is None for value in fares)
            else sum(value for value in fares if value is not None)
        )
        explanations = [
            "SIMULATION: independently authored schedule and streets; no live Bengaluru coverage.",
            "Physical duration uses scheduled timestamps; generalized costs are not added to ETA.",
            "Preference ranks only up to 16 provider candidates in a two-hour search window.",
        ]
        for leg in legs:
            if leg.mode == "WALK":
                explanations.append(f"Walk {leg.distance_m:.0f} m on the authored street graph.")
            else:
                explanations.append(
                    f"Take {(leg.route_id or leg.mode).split(':')[-1]}, direction {leg.direction_id or 'unknown'}, from {leg.start.isoformat()} to {leg.end.isoformat()}."
                )
        if request.wheelchair:
            explanations.append(
                "Static wheelchair constraints applied; lifts and paths are not live-verified."
            )
        if total is None:
            explanations.append("Fare unavailable; unknown is never interpreted as free.")
        if not transit:
            explanations.append("Walking-only street itinerary; no scheduled transit is used.")
        return Itinerary(
            start=start,
            end=end,
            duration_seconds=int((end - start).total_seconds()),
            initial_wait_seconds=max(0, int((start - request.when).total_seconds()))
            if not request.arrive_by
            else 0,
            elapsed_from_requested_departure_seconds=int((end - request.when).total_seconds())
            if not request.arrive_by
            else None,
            walking_m=walking,
            transfers=max(0, len(transit) - 1),
            fare_inr=total,
            fare_status="unknown"
            if total is None
            else "known_synthetic_per_boarding"
            if transit
            else "free_walking",
            legs=legs,
            explanations=explanations,
        )

    def plan(self, request: PlanRequest) -> PlanResponse:
        if request.graph_id is not None and request.graph_id != self.manifest.graph_id:
            raise HTTPException(409, "Graph version changed; request a fresh plan")
        origin, destination = (
            point(self.manifest, request.origin),
            point(self.manifest, request.destination),
        )
        if distance(origin, destination) < 1:
            return self.response(request, [], "same_location")
        local_day = request.when.astimezone(ZoneInfo("Asia/Kolkata")).date()
        if (
            not self.manifest.service_start
            <= local_day
            <= self.manifest.service_end + timedelta(days=1)
        ):
            return self.response(request, [], "outside_graph_service_coverage")
        if not self.slots.acquire(blocking=False):
            raise HTTPException(503, "Routing capacity busy; retry later")
        try:
            connection = self.fetch(self.variables(request, origin, destination))
            if connection.get("routingErrors") and not connection["edges"]:
                return self.response(request, [], "no_feasible_route_in_search_window")
            itineraries = []
            try:
                for edge in connection["edges"]:
                    itinerary = self.normalize(edge["node"], request)
                    if itinerary is not None:
                        itineraries.append(itinerary)
            except (ValueError, KeyError, TypeError, ValidationError):
                raise HTTPException(
                    503, "Routing provider returned inconsistent schedules"
                ) from None

            def key(item: Itinerary) -> tuple[float, ...]:
                time_score = -item.start.timestamp() if request.arrive_by else item.end.timestamp()
                if request.preference == "cheapest":
                    return (float(item.fare_inr is None), float(item.fare_inr or 0), time_score)
                if request.preference == "fewest_transfers":
                    return (float(item.transfers), time_score)
                if request.preference == "least_walking":
                    return (item.walking_m, time_score)
                return (time_score, float(item.duration_seconds))

            itineraries.sort(key=key)
            return self.response(
                request,
                itineraries[: request.limit],
                None if itineraries else "no_feasible_route_in_search_window",
            )
        finally:
            self.slots.release()
