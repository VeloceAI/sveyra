"""Canonical rest rig and dense four-influence skinning contract."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from sveyra_human.canonical.body import (
    CANONICAL_TOPOLOGY_ID,
    CANONICAL_TOPOLOGY_VERSION,
)

CANONICAL_RIG_SCHEMA_VERSION = "1.0"
CANONICAL_RIG_ID = "sveyra-hm08-standard-rig"
CANONICAL_RIG_VERSION = "0.1"
CANONICAL_RIG_ASSET_SHA256 = "df33618b997f9873a88857aaf50e3143918f6bb6ef330279a303ace526de146d"


class CanonicalRigError(ValueError):
    """Raised when rig hierarchy or skinning data violates the contract."""


@dataclass(frozen=True)
class CanonicalBone:
    name: str
    parent_index: int | None
    head_cm: tuple[float, float, float]
    tail_cm: tuple[float, float, float]
    source_roll_radians: float = 0.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise CanonicalRigError("bone name must not be empty")
        coordinates = (*self.head_cm, *self.tail_cm, self.source_roll_radians)
        if not all(math.isfinite(value) for value in coordinates):
            raise CanonicalRigError(f"bone {self.name!r} contains non-finite values")


@dataclass(frozen=True)
class CanonicalRig:
    bones: tuple[CanonicalBone, ...]
    joint_indices: np.ndarray
    weights: np.ndarray
    base_height_cm: float
    topology_id: str = CANONICAL_TOPOLOGY_ID
    topology_version: str = CANONICAL_TOPOLOGY_VERSION
    rig_id: str = CANONICAL_RIG_ID
    rig_version: str = CANONICAL_RIG_VERSION

    def __post_init__(self) -> None:
        if not self.bones:
            raise CanonicalRigError("rig must contain at least one bone")
        if len({bone.name for bone in self.bones}) != len(self.bones):
            raise CanonicalRigError("bone names must be unique")
        for index, bone in enumerate(self.bones):
            parent = bone.parent_index
            if parent is not None and not 0 <= parent < index:
                raise CanonicalRigError(
                    f"bone {bone.name!r} parent must precede it in topological order"
                )
        if self.joint_indices.ndim != 2 or self.joint_indices.shape[1] != 4:
            raise CanonicalRigError("joint_indices must have shape (vertices, 4)")
        if self.weights.shape != self.joint_indices.shape:
            raise CanonicalRigError("weights must match joint_indices shape")
        if not np.isfinite(self.weights).all() or (self.weights < 0).any():
            raise CanonicalRigError("skin weights must be finite and non-negative")
        if self.joint_indices.size and int(self.joint_indices.max()) >= len(self.bones):
            raise CanonicalRigError("skin weight references an unknown bone")
        if not np.allclose(self.weights.sum(axis=1), 1.0, atol=1e-5):
            raise CanonicalRigError("every canonical vertex must have normalized skin weights")
        if np.any(self.weights[:, :-1] < self.weights[:, 1:]):
            raise CanonicalRigError("skin influences must be ordered by descending weight")
        if not math.isfinite(self.base_height_cm) or self.base_height_cm <= 0:
            raise CanonicalRigError("base_height_cm must be finite and positive")

    @property
    def joint_count(self) -> int:
        return len(self.bones)

    @property
    def vertex_count(self) -> int:
        return int(self.weights.shape[0])

    @property
    def root_indices(self) -> tuple[int, ...]:
        return tuple(index for index, bone in enumerate(self.bones) if bone.parent_index is None)

    @property
    def head_positions_cm(self) -> np.ndarray:
        return np.asarray([bone.head_cm for bone in self.bones], dtype=np.float32)

    def scaled_to_height(self, height_cm: float) -> CanonicalRig:
        if not math.isfinite(height_cm) or height_cm <= 0:
            raise ValueError("height_cm must be finite and positive")
        scale = height_cm / self.base_height_cm
        bones = tuple(
            replace(
                bone,
                head_cm=tuple(value * scale for value in bone.head_cm),
                tail_cm=tuple(value * scale for value in bone.tail_cm),
            )
            for bone in self.bones
        )
        return replace(self, bones=bones, base_height_cm=height_cm)

    def local_translations_cm(self) -> np.ndarray:
        heads = self.head_positions_cm.astype(np.float64)
        translations = heads.copy()
        for index, bone in enumerate(self.bones):
            if bone.parent_index is not None:
                translations[index] -= heads[bone.parent_index]
        return translations.astype(np.float32)

    def inverse_bind_matrices_m(self) -> np.ndarray:
        """Translation-only rest transforms for the first portable rig seed."""
        matrices = np.repeat(np.eye(4, dtype=np.float32)[None, :, :], self.joint_count, axis=0)
        matrices[:, :3, 3] = -self.head_positions_cm * 0.01
        return matrices


def canonical_rig_asset_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "canonical" / "hm08_rig_v0.1.json"


def _tuple3(value: object, field: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise CanonicalRigError(f"{field} must contain three coordinates")
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError) as exc:
        raise CanonicalRigError(f"{field} contains invalid coordinates") from exc


def _from_dict(data: object) -> CanonicalRig:
    if not isinstance(data, dict):
        raise CanonicalRigError("canonical rig document must be an object")
    if data.get("schema_version") != CANONICAL_RIG_SCHEMA_VERSION:
        raise CanonicalRigError("unsupported canonical rig schema_version")
    if data.get("topology_id") != CANONICAL_TOPOLOGY_ID:
        raise CanonicalRigError("rig targets a different canonical topology")
    if data.get("topology_version") != CANONICAL_TOPOLOGY_VERSION:
        raise CanonicalRigError("rig targets a different canonical topology version")

    raw_bones = data.get("bones")
    skin = data.get("skin")
    if not isinstance(raw_bones, list) or not isinstance(skin, dict):
        raise CanonicalRigError("canonical rig needs bones and skin")
    bones: list[CanonicalBone] = []
    for index, raw in enumerate(raw_bones):
        if not isinstance(raw, dict):
            raise CanonicalRigError(f"bone {index} must be an object")
        parent = raw.get("parent_index")
        if parent is not None and not isinstance(parent, int):
            raise CanonicalRigError(f"bone {index} parent_index must be an integer or null")
        bones.append(
            CanonicalBone(
                name=str(raw.get("name", "")),
                parent_index=parent,
                head_cm=_tuple3(raw.get("head_cm"), f"bone {index} head_cm"),
                tail_cm=_tuple3(raw.get("tail_cm"), f"bone {index} tail_cm"),
                source_roll_radians=float(raw.get("source_roll_radians", 0.0)),
            )
        )

    try:
        joint_indices = np.asarray(skin["joint_indices"], dtype=np.uint16)
        weights = np.asarray(skin["weights"], dtype=np.float32)
        base_height_cm = float(data["base_height_cm"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CanonicalRigError("invalid canonical skin arrays or base height") from exc

    return CanonicalRig(
        bones=tuple(bones),
        joint_indices=joint_indices,
        weights=weights,
        base_height_cm=base_height_cm,
        rig_id=str(data.get("rig_id", CANONICAL_RIG_ID)),
        rig_version=str(data.get("rig_version", CANONICAL_RIG_VERSION)),
    )


def load_canonical_rig(path: str | Path | None = None) -> CanonicalRig:
    """Load the converted rig; the bundled asset is hash-pinned."""
    source = canonical_rig_asset_path() if path is None else Path(path)
    if path is None:
        if not CANONICAL_RIG_ASSET_SHA256:
            raise CanonicalRigError("bundled canonical rig hash has not been pinned")
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != CANONICAL_RIG_ASSET_SHA256:
            raise CanonicalRigError(
                "bundled canonical rig hash changed; update it only through a reviewed migration"
            )
    return _from_dict(json.loads(source.read_text(encoding="utf-8")))
