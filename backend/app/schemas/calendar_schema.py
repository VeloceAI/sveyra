from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class WearLogPersistRequest(StrictRequestModel):
    worn_on: date
    outfit_id: UUID | None = None
    item_ids: list[UUID] = Field(default_factory=list, max_length=100)
    occasion: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=500)
    planned: bool = False


class WearLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    worn_on: date
    outfit_id: UUID | None
    item_ids: list[UUID]
    occasion: str | None
    note: str | None
    planned: bool


class WearLogListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[WearLogResponse]
    start: date
    end: date
    total: int


class WornItemStat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: UUID
    times_worn: int


class WardrobeUsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    most_worn: list[WornItemStat]
    never_worn_item_ids: list[UUID]
    logged_days: int
