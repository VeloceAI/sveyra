from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class OutfitCreateRequest(StrictRequestModel):
    occasion: str = Field(min_length=1, max_length=100)
    item_ids: list[UUID] = Field(default_factory=list, max_length=100)
    rationale: dict[str, Any] = Field(default_factory=dict)


class OutfitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    occasion: str
    item_ids: list[UUID]
    rationale: dict[str, Any]


class OutfitListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outfits: list[OutfitResponse]
    limit: int
    offset: int
    total: int
