from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    wardrobe_item_id: UUID | None


class MediaAssetAccessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
