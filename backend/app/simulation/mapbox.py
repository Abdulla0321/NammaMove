"""Mapbox street routing used by the operator simulation."""

from bisect import bisect_left
from dataclasses import dataclass
from itertools import pairwise
from math import asin, cos, radians, sin, sqrt
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

Longitude = Annotated[float, Field(ge=-180, le=180)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Point = tuple[Longitude, Latitude]
Profile = Literal["walking", "driving-traffic"]
BENGALURU_BOUNDS = "77.35,12.70,77.90,13.25"


class Line(BaseModel):
    type: Literal["LineString"]
    coordinates: list[Point] = Field(min_length=2, max_length=30000)


class StreetRoute(BaseModel):
    duration: float = Field(ge=0, le=86400)
    distance: float = Field(ge=0, le=300000)
    geometry: Line
    legs: list["DirectionsLeg"] = Field(default_factory=list)

    @property
    def segment_seconds(self) -> list[float]:
        durations = [
            duration for leg in self.legs if leg.annotation for duration in leg.annotation.duration
        ]
        if len(durations) != len(self.geometry.coordinates) - 1 or sum(durations) <= 0:
            return []
        return durations


class Annotations(BaseModel):
    duration: list[Annotated[float, Field(ge=0, le=86400)]]


class DirectionsLeg(BaseModel):
    annotation: Annotations | None = None


class DirectionsResponse(BaseModel):
    code: str
    routes: list[StreetRoute] = Field(default_factory=list)


class GeocodePoint(BaseModel):
    type: Literal["Point"]
    coordinates: Point


class Feature(BaseModel):
    geometry: GeocodePoint


class GeocodeResponse(BaseModel):
    features: list[Feature]


class MapboxError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class Mapbox:
    def __init__(self, token: str, client: httpx.Client):
        self.token = token
        self.client = client

    def fetch(self, path: str, params: dict[str, str]) -> bytes:
        try:
            result = self.client.get(path, params={**params, "access_token": self.token})
            result.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in {401, 403}:
                raise MapboxError(503, "Mapbox rejected the configured server token") from None
            if status == 429:
                raise MapboxError(503, "Mapbox request limit reached") from None
            raise MapboxError(502, "Mapbox could not process the routing request") from None
        except httpx.RequestError:
            raise MapboxError(502, "Mapbox is temporarily unreachable") from None
        return result.content

    def geocode(self, query: str) -> Point:
        body = self.fetch(
            "/search/geocode/v6/forward",
            {
                "q": query,
                "country": "IN",
                "bbox": BENGALURU_BOUNDS,
                "proximity": "77.59,12.98",
                "limit": "1",
                "autocomplete": "false",
            },
        )
        try:
            response = GeocodeResponse.model_validate_json(body)
        except ValidationError:
            raise MapboxError(502, "Invalid geocoding response from Mapbox") from None
        if not response.features:
            raise MapboxError(404, "Mapbox could not find one of the Bengaluru locations")
        return response.features[0].geometry.coordinates

    def directions(self, profile: Profile, start: Point, end: Point) -> StreetRoute:
        coordinates = ";".join(f"{lng},{lat}" for lng, lat in (start, end))
        body = self.fetch(
            f"/directions/v5/mapbox/{profile}/{coordinates}",
            {
                "geometries": "geojson",
                "overview": "full",
                "steps": "false",
                "annotations": "duration",
            },
        )
        try:
            response = DirectionsResponse.model_validate_json(body)
        except ValidationError:
            raise MapboxError(502, "Invalid directions response from Mapbox") from None
        if response.code == "NoRoute" or response.code == "NoSegment":
            raise MapboxError(404, "Mapbox could not connect the selected locations")
        if response.code != "Ok" or not response.routes:
            raise MapboxError(502, "Mapbox returned no usable street route")
        return response.routes[0]


def meters(start: Point, end: Point) -> float:
    lng1, lat1, lng2, lat2 = map(radians, (*start, *end))
    arc = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 12742000 * asin(sqrt(min(arc, 1)))


@dataclass(frozen=True)
class Track:
    points: list[Point]
    distances: list[float]

    @classmethod
    def build(cls, points: list[Point], segment_seconds: list[float] | None = None) -> "Track":
        distances = [0.0]
        weights = segment_seconds or [meters(start, end) for start, end in pairwise(points)]
        for weight in weights:
            distances.append(distances[-1] + weight)
        return cls(points, distances)

    def position(self, fraction: float) -> Point:
        if fraction <= 0:
            return self.points[0]
        if fraction >= 1:
            return self.points[-1]
        distance = fraction * self.distances[-1]
        if distance == 0:
            return self.points[0]
        index = bisect_left(self.distances, distance)
        start, end = self.points[index - 1 : index + 1]
        span = self.distances[index] - self.distances[index - 1]
        portion = (distance - self.distances[index - 1]) / span
        return (start[0] + portion * (end[0] - start[0]), start[1] + portion * (end[1] - start[1]))
