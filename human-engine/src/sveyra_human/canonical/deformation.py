"""Rig-aware, topology-preserving deformation of the canonical human."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Final

import numpy as np

from sveyra_human.body.parameters import BodyParameters
from sveyra_human.canonical.body import CanonicalBodyMesh, load_canonical_body
from sveyra_human.canonical.rig import CanonicalBone, CanonicalRig, load_canonical_rig

MIN_APPLIED_RATIO: Final = 0.60
MAX_APPLIED_RATIO: Final = 1.60
SUPPORTED_FIELDS: Final = (
    "shoulder_width", "shoulder_depth", "neck_width",
    "chest_width", "chest_depth", "waist_width", "waist_depth",
    "hip_width", "hip_depth", "upper_arm_radius", "forearm_radius",
    "thigh_width", "thigh_depth", "calf_width", "calf_depth",
    "ankle_width", "head_width", "head_depth",
)
GROUPS: Final = (
    "torso", "neck", "head", "upperarm.L", "upperarm.R",
    "lowerarm.L", "lowerarm.R", "hand.L", "hand.R", "upperleg.L",
    "upperleg.R", "lowerleg.L", "lowerleg.R", "foot.L", "foot.R",
)


@dataclass(frozen=True)
class CanonicalDeformationReport:
    method: str
    supported_fields: tuple[str, ...]
    requested_ratios: dict[str, float]
    applied_ratios: dict[str, float]
    clamped_fields: tuple[str, ...]

    @property
    def parameter_fitted(self) -> bool:
        return any(not math.isclose(value, 1.0) for value in self.applied_ratios.values())

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "parameter_fitted": self.parameter_fitted}


@dataclass(frozen=True)
class _Context:
    height: float
    ratios: dict[str, float]
    rig: CanonicalRig
    centre_y: np.ndarray
    centre_z: np.ndarray
    arms: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]
    legs: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]
    shoulder_delta: dict[str, np.ndarray]
    hip_delta: dict[str, np.ndarray]


def deform_canonical_human(
    params: BodyParameters,
    body: CanonicalBodyMesh | None = None,
    rig: CanonicalRig | None = None,
) -> tuple[CanonicalBodyMesh, CanonicalRig, CanonicalDeformationReport]:
    """Apply supported measurements without changing topology or skin weights."""
    neutral = BodyParameters(height=float(params.height))
    requested, applied, clamped = _ratios(params, neutral)
    source_body = (body or load_canonical_body()).scaled_to_height(params.height)
    source_rig = (rig or load_canonical_rig()).scaled_to_height(params.height)
    if source_body.vertex_count != source_rig.vertex_count:
        raise ValueError("canonical body and rig vertex counts differ")
    if source_body.topology_id != source_rig.topology_id:
        raise ValueError("canonical body and rig target different topologies")

    context = _context(source_rig, float(params.height), applied)
    bone_groups = np.asarray([_group(bone.name) for bone in source_rig.bones], dtype=object)
    vertices = np.zeros_like(source_body.vertices_cm, dtype=np.float64)
    routed = np.zeros(source_body.vertex_count, dtype=np.float64)
    for group in GROUPS:
        weight = np.sum(
            np.where(bone_groups[source_rig.joint_indices] == group, source_rig.weights, 0.0),
            axis=1,
        )
        if np.any(weight):
            vertices += _deform(source_body.vertices_cm, group, context) * weight[:, None]
            routed += weight
    if not np.allclose(routed, 1.0, atol=1e-5):
        raise ValueError("canonical rig contains an unrouted semantic bone")

    fitted_body = replace(source_body, vertices_cm=vertices.astype(np.float32))
    fitted_rig = replace(
        source_rig,
        bones=tuple(_deform_bone(bone, context) for bone in source_rig.bones),
    )
    report = CanonicalDeformationReport(
        method="rig_weighted_cross_section_v1",
        supported_fields=SUPPORTED_FIELDS,
        requested_ratios=requested,
        applied_ratios=applied,
        clamped_fields=clamped,
    )
    return fitted_body, fitted_rig, report


def _ratios(
    params: BodyParameters, neutral: BodyParameters
) -> tuple[dict[str, float], dict[str, float], tuple[str, ...]]:
    requested: dict[str, float] = {}
    applied: dict[str, float] = {}
    clamped: list[str] = []
    for field in SUPPORTED_FIELDS:
        target, baseline = float(getattr(params, field)), float(getattr(neutral, field))
        if not math.isfinite(target) or target <= 0:
            raise ValueError(f"{field} must be finite and positive")
        ratio = target / baseline
        safe = float(np.clip(ratio, MIN_APPLIED_RATIO, MAX_APPLIED_RATIO))
        requested[field], applied[field] = round(ratio, 6), round(safe, 6)
        if not math.isclose(ratio, safe):
            clamped.append(field)
    return requested, applied, tuple(clamped)


def _group(name: str) -> str:
    side = ".L" if name.endswith(".L") else ".R" if name.endswith(".R") else ""
    routes = (
        (("shoulder01", "upperarm"), "upperarm"),
        (("lowerarm",), "lowerarm"),
        (("wrist", "finger", "metacarpal"), "hand"),
        (("upperleg",), "upperleg"),
        (("lowerleg",), "lowerleg"),
        (("foot", "toe"), "foot"),
    )
    for prefixes, region in routes:
        if side and name.startswith(prefixes):
            return f"{region}{side}"
    if name.startswith("neck"):
        return "neck"
    face_prefixes = (
        "head", "jaw", "eye", "special", "levator", "temporalis", "oculi",
        "orbicularis", "oris", "risorius", "tongue",
    )
    return "head" if name.startswith(face_prefixes) else "torso"


def _head(rig: CanonicalRig, name: str) -> np.ndarray:
    try:
        return np.asarray(next(bone.head_cm for bone in rig.bones if bone.name == name))
    except StopIteration as exc:
        raise ValueError(f"canonical rig is missing required bone {name!r}") from exc


def _context(rig: CanonicalRig, height: float, ratios: dict[str, float]) -> _Context:
    centres = np.asarray([
        _head(rig, name)
        for name in ("root", "spine03", "spine02", "spine01", "neck01", "head")
    ])
    order = np.argsort(centres[:, 1])
    context = _Context(
        height, ratios, rig, centres[order, 1], centres[order, 2], {}, {}, {}, {}
    )
    for side in ("L", "R"):
        shoulder = _head(rig, f"upperarm01.{side}")
        elbow = _head(rig, f"lowerarm01.{side}")
        wrist = _head(rig, f"wrist.{side}")
        context.arms[side] = (shoulder, elbow, wrist)
        context.shoulder_delta[side] = _torso(shoulder[None, :], context)[0] - shoulder

        hip = _head(rig, f"upperleg01.{side}")
        knee = _head(rig, f"lowerleg01.{side}")
        ankle = _head(rig, f"foot.{side}")
        context.legs[side] = (hip, knee, ankle)
        context.hip_delta[side] = _torso(hip[None, :], context)[0] - hip
    return context


def _profile(
    values: np.ndarray, positions: tuple[float, ...], samples: tuple[float, ...]
) -> np.ndarray:
    output = np.interp(values, positions, samples)
    for index in range(len(positions) - 1):
        selected = (values > positions[index]) & (values < positions[index + 1])
        t = (values[selected] - positions[index]) / (positions[index + 1] - positions[index])
        eased = t * t * (3.0 - 2.0 * t)
        output[selected] = samples[index] + (samples[index + 1] - samples[index]) * eased
    return output


def _centre_z(points: np.ndarray, context: _Context) -> np.ndarray:
    return np.interp(points[:, 1], context.centre_y, context.centre_z)


def _torso(points: np.ndarray, context: _Context) -> np.ndarray:
    normal_y = points[:, 1] / context.height
    levels = (0.0, 0.52, 0.62, 0.72, 0.818, 0.87, 1.0)
    width = _profile(normal_y, levels, tuple(context.ratios[name] for name in (
        "hip_width", "hip_width", "waist_width", "chest_width",
        "shoulder_width", "neck_width", "head_width",
    )))
    depth = _profile(normal_y, levels, tuple(context.ratios[name] for name in (
        "hip_depth", "hip_depth", "waist_depth", "chest_depth",
        "shoulder_depth", "neck_width", "head_depth",
    )))
    result = points.astype(np.float64, copy=True)
    centre = _centre_z(points, context)
    result[:, 0] *= width
    result[:, 2] = centre + (points[:, 2] - centre) * depth
    return result


def _central(points: np.ndarray, context: _Context, width: str, depth: str) -> np.ndarray:
    result = points.astype(np.float64, copy=True)
    centre = _centre_z(points, context)
    result[:, 0] *= context.ratios[width]
    result[:, 2] = centre + (points[:, 2] - centre) * context.ratios[depth]
    return result


def _centres(points: np.ndarray, start: np.ndarray, end: np.ndarray) -> np.ndarray:
    axis = end - start
    denominator = float(np.dot(axis, axis))
    if denominator <= 0:
        raise ValueError("canonical rig contains a zero-length segment")
    t = np.clip(((points - start) @ axis) / denominator, 0.0, 1.0)
    return start + t[:, None] * axis


def _segment(
    points: np.ndarray,
    start: np.ndarray,
    end: np.ndarray,
    width: float,
    depth: float,
    move: np.ndarray,
) -> np.ndarray:
    centre = _centres(points, start, end)
    result = points.astype(np.float64, copy=True) + move
    result[:, 0] = centre[:, 0] + move[0] + (points[:, 0] - centre[:, 0]) * width
    result[:, 2] = centre[:, 2] + move[2] + (points[:, 2] - centre[:, 2]) * depth
    return result


def _deform(points: np.ndarray, group: str, context: _Context) -> np.ndarray:
    if group == "torso":
        return _torso(points, context)
    if group == "neck":
        return _central(points, context, "neck_width", "neck_width")
    if group == "head":
        return _central(points, context, "head_width", "head_depth")

    region, side = group.split(".", maxsplit=1)
    if region in {"upperarm", "lowerarm", "hand"}:
        shoulder, elbow, wrist = context.arms[side]
        move = context.shoulder_delta[side]
        if region == "upperarm":
            ratio = context.ratios["upper_arm_radius"]
            return _segment(points, shoulder, elbow, ratio, ratio, move)
        if region == "lowerarm":
            ratio = context.ratios["forearm_radius"]
            return _segment(points, elbow, wrist, ratio, ratio, move)
        return points.astype(np.float64, copy=True) + move

    hip, knee, ankle = context.legs[side]
    move = context.hip_delta[side]
    if region == "upperleg":
        return _segment(
            points, hip, knee, context.ratios["thigh_width"],
            context.ratios["thigh_depth"], move,
        )
    if region == "lowerleg":
        return _segment(
            points, knee, ankle, context.ratios["calf_width"],
            context.ratios["calf_depth"], move,
        )
    result = points.astype(np.float64, copy=True) + move
    ankle_ratio = context.ratios["ankle_width"]
    result[:, 0] = ankle[0] + move[0] + (points[:, 0] - ankle[0]) * ankle_ratio
    result[:, 2] = ankle[2] + move[2] + (points[:, 2] - ankle[2]) * math.sqrt(ankle_ratio)
    return result


def _deform_bone(bone: CanonicalBone, context: _Context) -> CanonicalBone:
    points = np.asarray([bone.head_cm, bone.tail_cm], dtype=np.float64)
    transformed = _deform(points, _group(bone.name), context)
    return replace(
        bone,
        head_cm=tuple(float(value) for value in transformed[0]),
        tail_cm=tuple(float(value) for value in transformed[1]),
    )
