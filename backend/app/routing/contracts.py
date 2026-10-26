"""Versioned routing contracts; fixture data never establishes live service state."""

from datetime import date, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Point(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    stop_id: str | None = Field(default=None, min_length=1, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def complete(self) -> "Point":
        if self.stop_id is not None:
            if self.latitude is not None or self.longitude is not None:
                raise ValueError("Use a stop identifier or coordinates")
        elif self.latitude is None or self.longitude is None:
            raise ValueError("Supply both coordinates")
        return self


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: Point
    destination: Point
    when: AwareDatetime
    arrive_by: bool = False
    preference: Literal["fastest", "cheapest", "fewest_transfers", "least_walking"] = "fastest"
    modes: list[Literal["BUS", "SUBWAY", "WALK"]] = Field(
        default=["BUS", "SUBWAY", "WALK"], min_length=1, max_length=3
    )
    max_walk_m: int = Field(default=2000, ge=0, le=10000)
    max_transfers: int = Field(default=3, ge=0, le=5)
    wheelchair: bool = False
    transit_required: bool = False
    limit: int = Field(default=5, ge=1, le=10)
    graph_id: str | None = Field(default=None, pattern="^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_modes(self) -> "PlanRequest":
        if len(set(self.modes)) != len(self.modes):
            raise ValueError("Modes must be unique")
        if self.transit_required and not set(self.modes) & {"BUS", "SUBWAY"}:
            raise ValueError("Transit mode required")
        return self


class GraphManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    graph_id: str = Field(pattern="^[a-f0-9]{64}$")
    graph_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    data_mode: Literal["simulation"]
    license_id: Literal["CC0-1.0"]
    attribution: str
    otp_version: Literal["2.7.0"]
    otp_image: str
    inputs: dict[str, str]
    stops: dict[str, Point]
    route_fares_inr: dict[str, int] = Field(default_factory=dict)
    service_start: date
    service_end: date
    realtime_enabled: Literal[False]


class Leg(BaseModel):
    mode: Literal["WALK", "BUS", "SUBWAY"]
    start: AwareDatetime
    end: AwareDatetime
    distance_m: float = Field(ge=0, allow_inf_nan=False)
    from_lat: float = Field(ge=-90, le=90)
    from_lon: float = Field(ge=-180, le=180)
    to_lat: float = Field(ge=-90, le=90)
    to_lon: float = Field(ge=-180, le=180)
    route_id: str | None = None
    trip_id: str | None = None
    direction_id: str | None = None
    wheelchair_status: str | None = None

    @model_validator(mode="after")
    def chronological(self) -> "Leg":
        if self.end < self.start:
            raise ValueError("Invalid leg chronology")
        return self


class Itinerary(BaseModel):
    start: datetime
    end: datetime
    duration_seconds: int
    initial_wait_seconds: int
    elapsed_from_requested_departure_seconds: int | None
    walking_m: float
    transfers: int
    fare_inr: int | None
    fare_status: Literal["known_synthetic_per_boarding", "unknown", "free_walking"]
    legs: list[Leg]
    explanations: list[str]


class PlanResponse(BaseModel):
    contract_version: Literal["1"] = "1"
    graph_id: str
    graph_sha256: str
    source_attribution: str
    source_license: str
    otp_version: str
    data_mode: Literal["simulation"] = "simulation"
    confidence: Literal["authored_fixture_only"] = "authored_fixture_only"
    realtime_status: Literal["unavailable"] = "unavailable"
    service_status: Literal["unknown"] = "unknown"
    disruption_overlay_applied: Literal[False] = False
    congestion_safety_verified: Literal[False] = False
    status: Literal["ok", "no_route"]
    reason: str | None = None
    preference: str
    ranking_scope: Literal["bounded_provider_candidates"] = "bounded_provider_candidates"
    itineraries: list[Itinerary]
