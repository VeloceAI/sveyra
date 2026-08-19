from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class RecommendationRequest(StrictRequestModel):
    occasion: str = Field(min_length=1, max_length=100)


class RecommendationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_ids: list[UUID]
    rationale: str


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occasion: str
    recommendations: list[RecommendationCandidate]
