from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProfileInput(Input):
    display_name: str = Field(min_length=1, max_length=80)
    locale: Literal["en", "kn", "hi"] = "en"
    location_consent: StrictBool = False


class ProfileOutput(Output):
    id: UUID
    display_name: str
    locale: str
    location_consent: bool


class PreferenceInput(Input):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    step_free: bool = False
    max_walk_minutes: int = Field(default=30, ge=0, le=180)


class OperatorInput(Input):
    name: str = Field(min_length=1, max_length=120)
    data_mode: Literal["simulation", "live"] = "simulation"


class OperatorOutput(Output):
    id: UUID
    name: str
    data_mode: str


class StopInput(Input):
    operator_id: UUID
    external_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=160)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class StopOutput(StopInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class JourneyInput(Input):
    origin: str = Field(min_length=1, max_length=160)
    destination: str = Field(min_length=1, max_length=160)


class JourneyOutput(Output):
    id: UUID
    origin: str
    destination: str
    data_mode: str
    itinerary: dict[str, object]
    created_at: datetime


class ReportInput(Input):
    kind: Literal["delay", "road_closure", "station_outage", "accessibility", "other"]
    summary: str = Field(min_length=1, max_length=500)
    data_mode: Literal["simulation", "live"] = "simulation"


class ReportOutput(Output):
    id: UUID
    kind: str
    summary: str
    data_mode: str
    verification: str
    confidence: float
    verified_at: datetime | None
    expires_at: datetime | None


class VerificationInput(Input):
    decision: Literal["verified", "rejected"]
    evidence_source: str = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def expiry_window(self) -> "VerificationInput":
        now = datetime.now(timezone.utc)
        if not now < self.expires_at <= now + timedelta(days=7):
            raise ValueError("Evidence must expire within the next seven days")
        return self


class NotificationOutput(Output):
    id: UUID
    message: str
    data_mode: str
    created_at: datetime
    read_at: datetime | None
