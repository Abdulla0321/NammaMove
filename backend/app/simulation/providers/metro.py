from ..mapbox import Point
from .contracts import Vehicle

METRO = Vehicle(
    id="metro-01",
    operator="Namma Metro demo",
    assignment="Purple Line",
    driver="Metro validator",
    username="metro-validator",
)
WHITEFIELD_STATION: Point = (77.8251, 12.9957)
MAJESTIC_STATION: Point = (77.5727, 12.9757)
DEMO_FARE_INR = 60
DEMO_RIDE_MINUTES = 46
