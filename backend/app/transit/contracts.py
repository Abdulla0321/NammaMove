"""Provenance is mandatory; static schedules never become live vehicle data."""

from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    provider: Literal["bmtc", "bmrcl", "synthetic"]
    data_mode: Literal["scheduled", "simulation"]
    source_url: str = Field(min_length=1, max_length=500)
    license_id: str = Field(min_length=1, max_length=80)
    license_url: str = Field(min_length=1, max_length=500)
    attribution: str = Field(min_length=1, max_length=500)
    authorization: Literal["open", "authorized", "simulation"]
    authorization_reference: str = Field(min_length=1, max_length=200)
    publisher: str = Field(min_length=1, max_length=120)
    authority: Literal["agency", "community", "synthetic"]
    retrieved_at: AwareDatetime
    published_at: AwareDatetime | None = None
    version: str = Field(min_length=1, max_length=160)
    quality_notes: list[str] = Field(default_factory=list, max_length=20)

    @property
    def feed_id(self) -> str:
        return self.provider + ":" + self.data_mode

    @model_validator(mode="after")
    def provenance(self) -> "Manifest":
        for value in (self.source_url, self.license_url):
            parts = urlsplit(value)
            if (
                parts.scheme not in {"https", "http"}
                or not parts.hostname
                or parts.username
                or parts.password
                or parts.query
                or parts.fragment
            ):
                raise ValueError("Public provenance URLs must omit credentials, query and fragment")
        if any(not note.strip() or len(note) > 500 for note in self.quality_notes):
            raise ValueError("Quality notes must be nonempty and at most 500 characters")
        if self.authority == "community" and not self.quality_notes:
            raise ValueError("Community feeds require explicit quality limitations")
        now = datetime.now(timezone.utc)
        if self.retrieved_at > now + timedelta(minutes=5) or (
            self.published_at is not None
            and self.published_at > self.retrieved_at + timedelta(minutes=5)
        ):
            raise ValueError("Feed timestamps cannot be in the future")
        if self.data_mode == "simulation":
            if self.authorization != "simulation" or self.authority != "synthetic":
                raise ValueError("Simulation requires synthetic provenance")
        elif (
            self.authorization == "simulation"
            or self.authority == "synthetic"
            or self.provider == "synthetic"
        ):
            raise ValueError("Scheduled feeds need reviewed non-synthetic provenance")
        return self


class RealtimeObservation(BaseModel):
    """Future adapter boundary only. No GTFS-RT worker or cancellation inference."""

    model_config = ConfigDict(extra="forbid")
    observed_at: AwareDatetime | None = None
    mode: Literal["live", "simulation"] = "live"

    def freshness(self, now: datetime) -> str:
        if self.mode == "simulation":
            return "simulation"
        if self.observed_at is None:
            return "unavailable"
        age = (now - self.observed_at).total_seconds()
        if age < -30:
            return "unavailable"
        return "live" if age <= 300 else "stale"
