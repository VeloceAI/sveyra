from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AvatarBuildResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    backend: str
    source_views: int
    measurements: dict[str, Any]
    body_parameters: dict[str, Any]
    confidence: dict[str, Any]
    profiling_ms: dict[str, Any]


class CaptureCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ready: bool
    views: dict[str, Any]
    overall: list[str]


class CanonicalAvatarResponse(BaseModel):
    """A viewable rigged topology seed, explicitly not an identity claim."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    backend: str
    stage: str
    topology_id: str
    topology_version: str
    rig_id: str
    rig_version: str
    height_cm: float
    vertex_count: int
    triangle_count: int
    joint_count: int
    rigged: bool
    parameter_fitted: bool = False
    identity_fitted: bool
    photoreal_ready: bool
    deformation_method: str | None = None
    supported_measurements: list[str] = Field(default_factory=list)
    applied_measurement_ratios: dict[str, float] = Field(default_factory=dict)
    clamped_measurements: list[str] = Field(default_factory=list)
    limitations: list[str]


class HumanEnginePreviewRequest(BaseModel):
    """Developer controls for the fixed-topology measurement fitter, in cm."""

    model_config = ConfigDict(extra="forbid")

    height_cm: float = Field(default=178.0, ge=50.0, le=260.0)
    shoulder_width_cm: float | None = Field(default=None, gt=0, le=100)
    shoulder_depth_cm: float | None = Field(default=None, gt=0, le=80)
    neck_width_cm: float | None = Field(default=None, gt=0, le=50)
    chest_width_cm: float | None = Field(default=None, gt=0, le=100)
    chest_depth_cm: float | None = Field(default=None, gt=0, le=80)
    waist_width_cm: float | None = Field(default=None, gt=0, le=100)
    waist_depth_cm: float | None = Field(default=None, gt=0, le=80)
    hip_width_cm: float | None = Field(default=None, gt=0, le=100)
    hip_depth_cm: float | None = Field(default=None, gt=0, le=80)
    upper_arm_radius_cm: float | None = Field(default=None, gt=0, le=30)
    forearm_radius_cm: float | None = Field(default=None, gt=0, le=30)
    thigh_width_cm: float | None = Field(default=None, gt=0, le=60)
    thigh_depth_cm: float | None = Field(default=None, gt=0, le=60)
    calf_width_cm: float | None = Field(default=None, gt=0, le=50)
    calf_depth_cm: float | None = Field(default=None, gt=0, le=50)
    ankle_width_cm: float | None = Field(default=None, gt=0, le=30)
    head_width_cm: float | None = Field(default=None, gt=0, le=40)
    head_depth_cm: float | None = Field(default=None, gt=0, le=40)

    def engine_measurements(self) -> dict[str, float]:
        values = self.model_dump(exclude_none=True)
        values.pop("height_cm", None)
        return {name.removesuffix("_cm"): float(value) for name, value in values.items()}
