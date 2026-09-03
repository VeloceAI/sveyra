from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import StrictRequestModel


class GapRequest(StrictRequestModel):
    pass


class WardrobeGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["top", "bottom", "shoes"]
    priority: Literal["high"]
    reason: str


class GapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gaps: list[WardrobeGap]
