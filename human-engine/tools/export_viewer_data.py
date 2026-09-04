"""Build the payload the three.js viewer reads.

    python tools/export_viewer_data.py

Writes viewer/threejs/avatar_data.json, which is build output and gitignored.
Joint limits come from skeleton/limits.py, so the viewer enforces the same
rules the engine does rather than a copy that drifts.
"""

from __future__ import annotations

import base64
import json
import pathlib

import numpy as np

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.body import change_muscle, change_weight
from sveyra_human.body.anatomy import measurements
from sveyra_human.body.cage import build_cage
from sveyra_human.body.mesh_deformer import vertex_part_map
from sveyra_human.rig import compute_skin_weights, effective_parent, joint_order
from sveyra_human.skeleton.limits import as_dict as limits_as_dict
from sveyra_human.skeleton.model import build_skeleton

OUT = pathlib.Path(__file__).resolve().parents[1] / "viewer" / "threejs" / "avatar_data.json"


def b64(array: np.ndarray) -> str:
    return base64.b64encode(array.tobytes()).decode()


def main() -> int:
    engine = SveyraHumanEngine("balanced")
    base = BodyParameters(height=178.0, waist_width=34.0, chest_width=40.0)
    variants = {
        "base": ("Baseline", base),
        "lighter": ("-15 kg", change_weight(base, -15.0)[0]),
        "heavier": ("+15 kg", change_weight(base, 15.0)[0]),
        "muscular": ("Muscle +1", change_muscle(base, 1.0)[0]),
        "tall": ("196 cm", BodyParameters(height=196.0, waist_width=32.0, chest_width=39.0)),
    }

    order = joint_order()
    payload: dict = {
        "order": list(variants),
        "joints": order,
        "parents": [
            order.index(effective_parent(j, order)) if effective_parent(j, order) else -1
            for j in order
        ],
        "limits": limits_as_dict(),
        "variants": {},
    }

    first = True
    for key, (label, params) in variants.items():
        mesh = engine.build_parametric(params)._mesh
        skeleton = build_skeleton(params)
        if first:
            first = False
            payload["indices"] = b64(mesh.faces.astype(np.uint32))
            payload["vertexCount"] = int(mesh.vertex_count)
            payload["triangleCount"] = int(mesh.face_count)
            indices, weights, _ = compute_skin_weights(mesh.vertices, skeleton)
            payload["skinIndex"] = b64(indices.astype(np.uint16))
            payload["skinWeight"] = b64(weights.astype(np.float32))
            labels = vertex_part_map(build_cage(params, skeleton.positions), subdivisions=1)
            names = sorted(set(labels))
            payload["partNames"] = names
            payload["partOf"] = [names.index(name) for name in labels]

        verts = (mesh.vertices * 0.01).astype(np.float32)
        offset_x = float(verts[:, 0].mean())
        offset_z = float(verts[:, 2].mean())
        verts[:, 0] -= offset_x
        verts[:, 2] -= offset_z
        joints = np.array([skeleton.positions[j] for j in order]) * 0.01
        joints[:, 0] -= offset_x
        joints[:, 2] -= offset_z

        payload["variants"][key] = {
            "label": label,
            "positions": b64(verts),
            "normals": b64(mesh.normals().astype(np.float32)),
            "joints": b64(joints.astype(np.float32)),
            "measurements": {k: round(float(v), 1) for k, v in measurements(params).items()},
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload), encoding="utf-8")
    print(f"wrote {OUT.name} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
