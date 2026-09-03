"""Public data contracts.

The identity of a SVEYRA human is the parameter set, not the photographs. An
avatar written out here must be reconstructible from its JSON alone, without
rerunning image analysis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from sveyra_human.body.parameters import BodyParameters

SCHEMA_VERSION = "0.1"

QualityMode = Literal["draft", "balanced", "high"]

# Subdivision rounds per quality mode. Draft stays cage-resolution for fast
# iteration; high is for export.
SUBDIVISIONS: dict[str, int] = {"draft": 0, "balanced": 1, "high": 2}


@dataclass
class AvatarBuildRequest:
    """Inputs for a photo-driven build.

    Images accept a filesystem path, raw bytes or a numpy array. Nothing here
    names a cloud provider: storage is the caller's problem, not the engine's.

    Photo fields are accepted and validated now but not yet consumed - image
    understanding is Phase 2. See docs/STATUS.md.
    """

    height_cm: float

    front_image: object | None = None
    side_image: object | None = None
    back_image: object | None = None
    face_image: object | None = None

    optional_face_45: object | None = None
    optional_extra_images: list[object] = field(default_factory=list)

    body_type_hint: str | None = None
    manual_measurements: dict[str, float] = field(default_factory=dict)

    quality_mode: QualityMode = "balanced"
    texture_resolution: int = 1024

    provider_configuration: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.height_cm <= 0:
            raise ValueError("height_cm must be positive")
        if self.quality_mode not in SUBDIVISIONS:
            raise ValueError(f"unknown quality_mode: {self.quality_mode}")
        if self.texture_resolution not in (512, 1024, 2048, 4096):
            raise ValueError("texture_resolution must be 512, 1024, 2048 or 4096")

    @property
    def supplied_views(self) -> int:
        candidates = (self.front_image, self.side_image, self.back_image, self.face_image)
        return sum(1 for c in candidates if c is not None)


@dataclass
class QualityReport:
    """Per-view confidence and anything the caller should not trust blindly."""

    overall: float
    views: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "overall": round(self.overall, 4),
            "views": {k: round(v, 4) for k, v in self.views.items()},
            "warnings": list(self.warnings),
        }


@dataclass
class AvatarArtifact:
    """Everything one reconstruction produced."""

    body_parameters: BodyParameters
    measurements: dict[str, float]
    skeleton: dict[str, object]
    quality: QualityReport
    profiling_ms: dict[str, float] = field(default_factory=dict)
    source_views: int = 0
    _mesh: object | None = None
    _skeleton: object | None = None

    def metadata(self) -> dict[str, object]:
        return {
            "version": SCHEMA_VERSION,
            "height_cm": self.body_parameters.height,
            "body_parameters": self.body_parameters.to_dict(),
            "measurements": self.measurements,
            "confidence": self.quality.to_dict(),
            "source_views": self.source_views,
            "profiling_ms": self.profiling_ms,
        }

    def export(self, path: str | Path, rigged: bool = True) -> Path:
        """Write the GLB, plus the JSON sidecars next to it.

        Rigged by default: an avatar that cannot be posed is of little use to a
        try-on viewer. Pass rigged=False for a plain static mesh.
        """
        from sveyra_human.export.gltf import export_glb
        from sveyra_human.export.metadata import write_sidecars
        from sveyra_human.export.skinned_gltf import export_skinned_glb

        if self._mesh is None:
            raise RuntimeError("artifact carries no mesh")
        target = Path(path)
        if rigged and self._skeleton is not None:
            export_skinned_glb(self._mesh, self._skeleton, target)  # type: ignore[arg-type]
        else:
            export_glb(self._mesh, target)  # type: ignore[arg-type]
        write_sidecars(self, target.parent)
        return target

    def as_garment_body(self) -> object:
        """Hand this avatar to a garment engine across the narrow contract."""
        from sveyra_human.garment.body_adapter import SveyraBody

        if self._mesh is None or self._skeleton is None:
            raise RuntimeError("artifact carries no mesh or skeleton")
        return SveyraBody(
            parameters=self.body_parameters,
            skeleton=self._skeleton,  # type: ignore[arg-type]
            mesh=self._mesh,  # type: ignore[arg-type]
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.metadata(), indent=indent)
