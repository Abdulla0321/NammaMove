"""Simulation provider identities and configurable demo fare rules."""

from math import ceil
from typing import Literal

from pydantic import BaseModel

VehicleId = Literal["cab-01", "metro-01", "bus-01"]


class Vehicle(BaseModel):
    id: VehicleId
    operator: str
    assignment: str
    driver: str
    username: str


TAXI = Vehicle(
    id="cab-01",
    operator="Demo Taxi",
    assignment="DEMO-CAB-01",
    driver="Asha",
    username="taxi-driver",
)
METRO = Vehicle(
    id="metro-01",
    operator="Namma Metro demo",
    assignment="Purple Line",
    driver="Metro validator",
    username="metro-validator",
)
BMTC = Vehicle(
    id="bus-01",
    operator="BMTC demo",
    assignment="DEMO-BUS-01",
    driver="Ravi",
    username="bmtc-driver",
)
FLEET = {vehicle.id: vehicle for vehicle in (TAXI, METRO, BMTC)}


def taxi_fare(distance_meters: float, minimum: int = 40) -> int:
    return max(minimum, ceil(distance_meters / 1000 * 16))
