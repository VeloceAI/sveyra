"""Versioned contracts for a measurable, photoreal, animatable digital human."""

from sveyra_human.digital_human.acceptance import (
    is_photoreal_animation_ready,
    photoreal_animation_issues,
)
from sveyra_human.digital_human.manifest import (
    AppearanceManifest,
    AssetFile,
    CaptureEvidence,
    DigitalHumanManifest,
    GeometryManifest,
    ProvenanceRecord,
    RegionEvidence,
    RigManifest,
)

__all__ = [
    "AppearanceManifest",
    "AssetFile",
    "CaptureEvidence",
    "DigitalHumanManifest",
    "GeometryManifest",
    "ProvenanceRecord",
    "RegionEvidence",
    "RigManifest",
    "is_photoreal_animation_ready",
    "photoreal_animation_issues",
]
