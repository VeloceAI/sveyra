from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import StrictRequestModel


class RecommendationRequest(StrictRequestModel):
    occasion: str = Field(min_length=1, max_length=100)
    required_item_ids: list[UUID] = Field(default_factory=list, max_length=8)
    excluded_item_ids: list[UUID] = Field(default_factory=list, max_length=20)
    replacement_item_id: UUID | None = None

    @model_validator(mode="after")
    def validate_item_constraints(self) -> "RecommendationRequest":
        required = set(self.required_item_ids)
        excluded = set(self.excluded_item_ids)
        if len(required) != len(self.required_item_ids):
            raise ValueError("required_item_ids must not contain duplicates")
        if len(excluded) != len(self.excluded_item_ids):
            raise ValueError("excluded_item_ids must not contain duplicates")
        if required & excluded:
            raise ValueError("an item cannot be both required and excluded")
        if self.replacement_item_id in required:
            raise ValueError("replacement_item_id cannot also be required")
        return self


class RecommendationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_ids: list[UUID]
    rationale: str


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occasion: str
    recommendations: list[RecommendationCandidate]
