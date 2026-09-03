from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class MediaAssetCreateRequest(StrictRequestModel):
    reference: str = Field(min_length=1, max_length=512)
    wardrobe_item_id: UUID | None = None


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    wardrobe_item_id: UUID | None
    reference: str


class MediaAssetAccessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
