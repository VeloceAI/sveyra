"""Clean conversion from reviewed MPFB rig assets into Sveyra's rig schema."""

from __future__ import annotations

from typing import Any

from sveyra_human.canonical.body import (
    CANONICAL_TOPOLOGY_ID,
    CANONICAL_TOPOLOGY_VERSION,
)
from sveyra_human.canonical.obj import ObjDocument
from sveyra_human.canonical.rig import (
    CANONICAL_RIG_ID,
    CANONICAL_RIG_SCHEMA_VERSION,
    CANONICAL_RIG_VERSION,
    CanonicalRigError,
)


def _topological_names(raw_rig: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise CanonicalRigError(f"cycle in source rig at bone {name!r}")
        raw = raw_rig.get(name)
        if not isinstance(raw, dict):
            raise CanonicalRigError(f"source bone {name!r} must be an object")
        visiting.add(name)
        parent = raw.get("parent")
        if parent:
            if not isinstance(parent, str) or parent not in raw_rig:
                raise CanonicalRigError(f"source bone {name!r} has unknown parent {parent!r}")
            visit(parent)
        visiting.remove(name)
        visited.add(name)
        ordered.append(name)

    for name in raw_rig:
        visit(name)
    return ordered


def _point_to_sveyra_cm(value: object, ground_offset_cm: float) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise CanonicalRigError("source rig point must contain three coordinates")
    try:
        x, depth, vertical = (float(coordinate) for coordinate in value)
    except (TypeError, ValueError) as exc:
        raise CanonicalRigError("source rig point contains invalid coordinates") from exc
    return [
        round(x * 100.0, 7),
        round(vertical * 100.0 + ground_offset_cm, 7),
        round(-depth * 100.0, 7),
    ]


def _endpoint(raw: dict[str, Any], field: str, ground_offset_cm: float) -> list[float]:
    endpoint = raw.get(field)
    if not isinstance(endpoint, dict) or "default_position" not in endpoint:
        raise CanonicalRigError(f"source bone has no {field} default_position")
    return _point_to_sveyra_cm(endpoint["default_position"], ground_offset_cm)


def convert_mpfb_rig(
    raw_rig: object,
    raw_weights: object,
    source_body: ObjDocument,
    body_group: str = "body",
    maximum_influences: int = 4,
) -> dict[str, object]:
    """Convert CC0 data without executing or adapting MPFB program code."""
    if not isinstance(raw_rig, dict) or not raw_rig:
        raise CanonicalRigError("source rig must be a non-empty object")
    if not isinstance(raw_weights, dict) or raw_weights.get("license") != "CC0":
        raise CanonicalRigError("source weights must explicitly declare license CC0")
    weight_groups = raw_weights.get("weights")
    if not isinstance(weight_groups, dict):
        raise CanonicalRigError("source weights document has no weights object")
    if maximum_influences != 4:
        raise CanonicalRigError("the portable glTF skin contract requires four influences")

    source_faces = source_body.faces_in_group(body_group)
    used_source_vertices = sorted(
        {index for face in source_faces for index in face.vertex_indices}
    )
    if not used_source_vertices:
        raise CanonicalRigError(f"source body group {body_group!r} has no vertices")
    source_to_canonical = {
        source: canonical for canonical, source in enumerate(used_source_vertices)
    }

    ordered_names = _topological_names(raw_rig)
    joint_for_name = {name: index for index, name in enumerate(ordered_names)}
    source_min_y_cm = min(source_body.vertices[index][1] for index in used_source_vertices) * 10.0
    source_max_y_cm = max(source_body.vertices[index][1] for index in used_source_vertices) * 10.0
    ground_offset_cm = -source_min_y_cm

    bones: list[dict[str, object]] = []
    for name in ordered_names:
        raw = raw_rig[name]
        parent_name = raw.get("parent")
        bones.append(
            {
                "name": name,
                "parent_index": joint_for_name[parent_name] if parent_name else None,
                "head_cm": _endpoint(raw, "head", ground_offset_cm),
                "tail_cm": _endpoint(raw, "tail", ground_offset_cm),
                "source_roll_radians": round(float(raw.get("roll", 0.0)), 9),
            }
        )

    influences: list[list[tuple[int, float]]] = [
        [] for _ in range(len(used_source_vertices))
    ]
    filtered_entries = 0
    source_entries = 0
    for bone_name, entries in weight_groups.items():
        if bone_name not in joint_for_name:
            raise CanonicalRigError(f"weight group {bone_name!r} has no source bone")
        if not isinstance(entries, list):
            raise CanonicalRigError(f"weight group {bone_name!r} must be a list")
        joint = joint_for_name[bone_name]
        for entry in entries:
            source_entries += 1
            if not isinstance(entry, list) or len(entry) != 2:
                raise CanonicalRigError(f"weight entry for {bone_name!r} must be [vertex, weight]")
            try:
                source_vertex, weight = int(entry[0]), float(entry[1])
            except (TypeError, ValueError) as exc:
                raise CanonicalRigError(f"invalid weight entry for {bone_name!r}") from exc
            canonical_vertex = source_to_canonical.get(source_vertex)
            if canonical_vertex is None:
                filtered_entries += 1
                continue
            if weight > 0.0:
                influences[canonical_vertex].append((joint, weight))

    joint_rows: list[list[int]] = []
    weight_rows: list[list[float]] = []
    dropped_influences = 0
    dropped_weight = 0.0
    for vertex, vertex_influences in enumerate(influences):
        if not vertex_influences:
            raise CanonicalRigError(f"canonical vertex {vertex} has no surviving skin weight")
        ordered = sorted(vertex_influences, key=lambda item: (-item[1], item[0]))
        dropped_influences += max(0, len(ordered) - maximum_influences)
        dropped_weight += sum(weight for _, weight in ordered[maximum_influences:])
        retained = ordered[:maximum_influences]
        total = sum(weight for _, weight in retained)
        if total <= 0.0:
            raise CanonicalRigError(f"canonical vertex {vertex} has zero total skin weight")
        joints = [joint for joint, _ in retained]
        weights = [weight / total for _, weight in retained]
        while len(joints) < maximum_influences:
            joints.append(0)
            weights.append(0.0)
        rounded_weights = [round(weight, 8) for weight in weights]
        rounded_weights[0] = round(1.0 - sum(rounded_weights[1:]), 8)
        joint_rows.append(joints)
        weight_rows.append(rounded_weights)

    weighted_bones = len({joint for row in joint_rows for joint in row})
    return {
        "schema_version": CANONICAL_RIG_SCHEMA_VERSION,
        "topology_id": CANONICAL_TOPOLOGY_ID,
        "topology_version": CANONICAL_TOPOLOGY_VERSION,
        "rig_id": CANONICAL_RIG_ID,
        "rig_version": CANONICAL_RIG_VERSION,
        "base_height_cm": round(source_max_y_cm - source_min_y_cm, 7),
        "bones": bones,
        "skin": {
            "maximum_influences": maximum_influences,
            "joint_indices": joint_rows,
            "weights": weight_rows,
        },
        "conversion_statistics": {
            "canonical_vertices": len(used_source_vertices),
            "source_bones": len(raw_rig),
            "weighted_bones_after_filtering": weighted_bones,
            "source_weight_entries": source_entries,
            "filtered_non_body_entries": filtered_entries,
            "dropped_body_influences_over_limit": dropped_influences,
            "dropped_body_weight_before_renormalization": round(dropped_weight, 8),
        },
    }
