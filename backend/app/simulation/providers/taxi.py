from math import ceil

from .contracts import Vehicle

TAXI = Vehicle(
    id="cab-01",
    operator="Demo Taxi",
    assignment="DEMO-CAB-01",
    driver="Asha",
    username="taxi-driver",
)


def taxi_fare(distance_meters: float, minimum: int = 40) -> int:
    return max(minimum, ceil(distance_meters / 1000 * 16))
