"""Expiring local staff sessions scoped to one simulated fleet vehicle."""

from collections.abc import Callable, Mapping
from hmac import compare_digest
from secrets import token_urlsafe
from threading import Lock

from fastapi import HTTPException

from .providers import FLEET, VehicleId


class DriverSessions:
    def __init__(self, passwords: Mapping[VehicleId, str], clock: Callable[[], float]):
        self.passwords = {vehicle: value.encode() for vehicle, value in passwords.items() if value}
        self.clock = clock
        self.lock = Lock()
        self.sessions: dict[VehicleId, tuple[str, float]] = {}
        self.attempts: dict[VehicleId, tuple[float, int]] = {}

    def sign_in(self, username: str, password: str) -> tuple[VehicleId, str]:
        vehicle = next((item.id for item in FLEET.values() if item.username == username), None)
        if vehicle is None:
            raise HTTPException(401, "Invalid staff credentials")
        with self.lock:
            now = self.clock()
            started, count = self.attempts.get(vehicle, (now, 0))
            if now - started >= 60:
                started, count = now, 0
            if count >= 8:
                raise HTTPException(429, "Too many sign-in attempts. Try again in a minute.")
            expected = self.passwords.get(vehicle)
            if not expected or not compare_digest(expected, password.encode()):
                self.attempts[vehicle] = (started, count + 1)
                raise HTTPException(401, "Invalid staff credentials")
            self.attempts.pop(vehicle, None)
            token = token_urlsafe(32)
            self.sessions[vehicle] = (token, now + 1800)
            return vehicle, token

    def authorize(self, vehicle: VehicleId, token: str | None) -> None:
        with self.lock:
            session = self.sessions.get(vehicle)
            if (
                not token
                or not session
                or self.clock() >= session[1]
                or not compare_digest(session[0].encode(), token.encode())
            ):
                raise HTTPException(401, "Invalid or expired staff session")
