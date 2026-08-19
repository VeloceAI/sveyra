from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class BodyProfilePersistRequest(StrictRequestModel):
    measurements: dict[str, Any] = Field(default_factory=dict)
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
