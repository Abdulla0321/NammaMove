"""Separate identities and policies for each simulated transport provider."""

from .bmtc import BMTC
from .contracts import VehicleId as VehicleId
from .metro import METRO
from .taxi import TAXI

FLEET = {vehicle.id: vehicle for vehicle in (TAXI, METRO, BMTC)}
