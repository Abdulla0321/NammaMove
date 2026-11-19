from typing import Literal

from pydantic import BaseModel

VehicleId = Literal["cab-01", "metro-01", "bus-01"]


class Vehicle(BaseModel):
    id: VehicleId
    operator: str
    assignment: str
    driver: str
    username: str
