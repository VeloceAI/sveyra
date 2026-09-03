from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class ProfilePersistRequest(StrictRequestModel):
    preferences: dict[str, Any] = Field(default_factory=dict)
    dislikes: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)


class PersistedProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False, extra="forbid")

    user_id: UUID
    email: str
    style_profile_id: UUID
    preferences: dict[str, Any]
    dislikes: dict[str, Any]
    budget: dict[str, Any]
    created_at: datetime | None
