from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class BodyMeasurements(BaseModel):
    """Known measurements the avatar pipeline fits against.

    Extra keys are kept so free-form notes captured before this schema still
    round-trip; the named fields are the ones body-model fitting reads.
    """

    model_config = ConfigDict(extra="allow")

    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    chest_cm: float | None = Field(default=None, gt=0, le=300)
    waist_cm: float | None = Field(default=None, gt=0, le=300)
    hip_cm: float | None = Field(default=None, gt=0, le=300)
    inseam_cm: float | None = Field(default=None, gt=0, le=200)


class BodyProfilePersistRequest(StrictRequestModel):
    measurements: BodyMeasurements = Field(default_factory=BodyMeasurements)
    fit_preferences: dict[str, Any] = Field(default_factory=dict)


class BodyProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    measurements: dict[str, Any]
    fit_preferences: dict[str, Any]


class BodyProfileListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body_profiles: list[BodyProfileResponse]
    limit: int
    offset: int
    total: int
