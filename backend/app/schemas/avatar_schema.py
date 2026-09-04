from typing import Any

from pydantic import BaseModel, ConfigDict


class AvatarBuildResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    backend: str
    source_views: int
    measurements: dict[str, Any]
    body_parameters: dict[str, Any]
    confidence: dict[str, Any]
    profiling_ms: dict[str, Any]
