from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import StrictRequestModel


def _looks_like_url_or_storage_ref(value: str) -> bool:
    lowered = value.lower().strip()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("gs://")
        or lowered.startswith("memory://")
        or "://" in lowered
    )


def _reject_unsafe_attribute_values(value: object, path: str = "attributes") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _reject_unsafe_attribute_values(nested, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_unsafe_attribute_values(nested, f"{path}[{index}]")
        return
    if isinstance(value, (bytes, bytearray)):
        raise ValueError(f"{path} must not contain raw bytes")
    if isinstance(value, str) and _looks_like_url_or_storage_ref(value):
        raise ValueError(f"{path} must not contain URLs or storage references")


class WardrobeItemCreateRequest(StrictRequestModel):
    category: str = Field(min_length=1, max_length=100)
    color: str = Field(min_length=1, max_length=100)
    brand: str = Field(min_length=1, max_length=100)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("attributes")
    @classmethod
    def attributes_must_be_safe(cls, value: dict[str, Any]) -> dict[str, Any]:
        _reject_unsafe_attribute_values(value)
        return value


class WardrobeItemUpdateRequest(StrictRequestModel):
    category: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, min_length=1, max_length=100)
    brand: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, Any] | None = None

    @field_validator("attributes")
    @classmethod
    def attributes_must_be_safe(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None:
            _reject_unsafe_attribute_values(value)
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "WardrobeItemUpdateRequest":
        if (
            self.category is None
            and self.color is None
            and self.brand is None
            and self.attributes is None
        ):
            raise ValueError("At least one of category, color, brand, attributes is required")
        return self


class WardrobeItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    category: str
    color: str
    brand: str
    attributes: dict[str, Any]


class WardrobeItemListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wardrobe_items: list[WardrobeItemResponse]
    limit: int
    offset: int
    total: int
