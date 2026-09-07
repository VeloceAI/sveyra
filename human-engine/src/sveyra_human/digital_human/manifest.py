"""Serializable metadata for a SVEYRA digital human.

The manifest deliberately stores opaque asset references rather than URLs or
image bytes. Product storage owns the bytes; this package describes what was
built, what evidence informed it, and which parts remain inferred.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Literal

SCHEMA_VERSION = "1.0"

AssetRole = Literal[
    "body_mesh",
    "hair_geometry",
    "albedo_texture",
    "normal_texture",
    "roughness_texture",
    "subsurface_texture",
    "animation",
]
CaptureMode = Literal[
    "single_image",
    "multi_view_images",
    "guided_video",
    "depth_assisted",
]
ScaleSource = Literal[
    "reported_height",
    "calibration_object",
    "depth_sensor",
    "unknown",
]
EvidenceBasis = Literal["measured", "observed", "inferred", "template"]
HairRepresentation = Literal["none", "shell", "cards", "strands", "neural"]
ProvenanceKind = Literal["original", "dependency", "reference", "asset"]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_REFERENCE_PREFIXES = ("http://", "https://", "file://", "data:")


def _require_text(value: str, name: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True)
class AssetFile:
    """One stored component, addressed through a provider-neutral reference."""

    role: AssetRole
    reference: str
    media_type: str
    sha256: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.reference, "reference")
        _require_text(self.media_type, "media_type")
        lowered = self.reference.lower()
        if lowered.startswith(_FORBIDDEN_REFERENCE_PREFIXES):
            raise ValueError("reference must be opaque; URLs and embedded bytes are forbidden")
        if self.sha256 is not None and _SHA256.fullmatch(self.sha256) is None:
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")


@dataclass(frozen=True)
class CaptureEvidence:
    """How the source person was captured, without retaining biometric bytes."""

    mode: CaptureMode
    source_views: int
    scale_source: ScaleSource
    consent_reference: str
    body_capture: bool = True
    face_capture: bool = False
    neutral_expression: bool = False

    def __post_init__(self) -> None:
        if self.source_views < 1:
            raise ValueError("source_views must be at least one")
        _require_text(self.consent_reference, "consent_reference")


@dataclass(frozen=True)
class RegionEvidence:
    """Whether a human region was observed, measured, or reconstructed by prior."""

    basis: EvidenceBasis
    confidence: float
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("region confidence must be between zero and one")


@dataclass(frozen=True)
class GeometryManifest:
    """Canonical surface contract shared by identity, animation, and garments."""

    topology_id: str
    topology_version: str
    vertex_count: int
    triangle_count: int
    lod_count: int = 1
    units: Literal["meter"] = "meter"
    up_axis: Literal["Y"] = "Y"
    forward_axis: Literal["-Z"] = "-Z"
    watertight: bool = False
    has_hands: bool = False
    has_feet: bool = False
    has_eyes: bool = False
    has_mouth_cavity: bool = False
    has_teeth: bool = False
    has_tongue: bool = False

    def __post_init__(self) -> None:
        _require_text(self.topology_id, "topology_id")
        _require_text(self.topology_version, "topology_version")
        if self.vertex_count <= 0 or self.triangle_count <= 0:
            raise ValueError("geometry counts must be positive")
        if self.lod_count < 1:
            raise ValueError("lod_count must be at least one")


@dataclass(frozen=True)
class RigManifest:
    """Body and facial controls carried by the reconstructed identity."""

    skeleton_id: str
    joint_count: int
    facial_blendshape_standard: Literal["none", "arkit-52", "facs-custom"] = "none"
    facial_blendshape_count: int = 0
    has_finger_rig: bool = False
    has_eye_gaze: bool = False
    has_eyelids: bool = False
    has_jaw: bool = False
    has_tongue_rig: bool = False
    corrective_shapes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.skeleton_id, "skeleton_id")
        if self.joint_count <= 0:
            raise ValueError("joint_count must be positive")
        if self.facial_blendshape_count < 0:
            raise ValueError("facial_blendshape_count must not be negative")


@dataclass(frozen=True)
class AppearanceManifest:
    """Physically based appearance separated from capture-scene lighting."""

    texture_resolution: int
    texture_maps: tuple[str, ...] = ()
    hair_representation: HairRepresentation = "none"
    lighting_neutralized: bool = False
    has_eye_material: bool = False
    has_skin_subsurface: bool = False

    def __post_init__(self) -> None:
        if self.texture_resolution <= 0:
            raise ValueError("texture_resolution must be positive")
        if len(set(self.texture_maps)) != len(self.texture_maps):
            raise ValueError("texture_maps must not contain duplicates")


@dataclass(frozen=True)
class ProvenanceRecord:
    """File-level origin and licence record for copied or adapted material."""

    component: str
    kind: ProvenanceKind
    origin: str
    license_id: str
    copied: bool = False
    source_path: str | None = None
    notice: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.component, "component"),
            (self.origin, "origin"),
            (self.license_id, "license_id"),
        ):
            _require_text(value, name)
        if self.copied and not self.source_path:
            raise ValueError("copied material requires a source_path")


@dataclass(frozen=True)
class DigitalHumanManifest:
    """The durable identity contract for one SVEYRA digital human."""

    asset_id: str
    capture: CaptureEvidence
    geometry: GeometryManifest
    rig: RigManifest
    appearance: AppearanceManifest
    files: tuple[AssetFile, ...]
    measurements_cm: dict[str, float]
    regions: dict[str, RegionEvidence]
    provenance: tuple[ProvenanceRecord, ...] = ()
    schema_version: str = field(default=SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        _require_text(self.asset_id, "asset_id")
        roles = [asset.role for asset in self.files]
        if len(set(roles)) != len(roles):
            raise ValueError("each asset role may appear only once")
        for name, value in self.measurements_cm.items():
            _require_text(name, "measurement name")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"measurement {name!r} must be positive and finite")
        for name in self.regions:
            _require_text(name, "region name")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> DigitalHumanManifest:
        """Restore a manifest while re-running every nested validation rule."""
        version = value.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported digital-human schema {version!r}; expected {SCHEMA_VERSION!r}"
            )
        capture = CaptureEvidence(**value["capture"])  # type: ignore[arg-type]
        geometry = GeometryManifest(**value["geometry"])  # type: ignore[arg-type]
        rig_data = dict(value["rig"])  # type: ignore[arg-type]
        rig_data["corrective_shapes"] = tuple(rig_data.get("corrective_shapes", ()))
        rig = RigManifest(**rig_data)  # type: ignore[arg-type]
        appearance_data = dict(value["appearance"])  # type: ignore[arg-type]
        appearance_data["texture_maps"] = tuple(appearance_data.get("texture_maps", ()))
        appearance = AppearanceManifest(**appearance_data)  # type: ignore[arg-type]
        files = tuple(AssetFile(**item) for item in value["files"])  # type: ignore[arg-type]
        regions = {
            name: RegionEvidence(
                basis=item["basis"],
                confidence=item["confidence"],
                warnings=tuple(item.get("warnings", ())),
            )
            for name, item in value["regions"].items()  # type: ignore[union-attr]
        }
        provenance = tuple(
            ProvenanceRecord(**item) for item in value.get("provenance", ())  # type: ignore[arg-type]
        )
        return cls(
            asset_id=value["asset_id"],  # type: ignore[arg-type]
            capture=capture,
            geometry=geometry,
            rig=rig,
            appearance=appearance,
            files=files,
            measurements_cm=dict(value["measurements_cm"]),  # type: ignore[arg-type]
            regions=regions,
            provenance=provenance,
        )
