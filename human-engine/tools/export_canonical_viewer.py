"""Export the canonical human as a skinned mesh a browser can pose.

The viewer has been drawing an eighteen bone approximation with rigid parts,
because the generated surface had no skin weights and a hand written blend
tore the mesh at every joint. The canonical rig has real weights, four
influences per vertex, which is exactly what THREE.SkinnedMesh consumes. Skin
it on the GPU with the library's own implementation rather than by hand.

Vertices are exported unsplit. The surface mesh splits them at UV seams, which
breaks the one to one correspondence with the weight table, and there are no
textures yet to justify carrying UVs.

    python human-engine/tools/export_canonical_viewer.py
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from sveyra_human.body.anatomy import measurements  # noqa: E402
from sveyra_human.body.figures import DEFAULT_HEIGHT_CM, figure  # noqa: E402
from sveyra_human.canonical.collision import body_volumes  # noqa: E402
from sveyra_human.canonical.deformation import deform_canonical_human  # noqa: E402
from sveyra_human.canonical.render import drawable  # noqa: E402
from sveyra_human.canonical.rig import load_canonical_rig  # noqa: E402

OUT = ROOT / "viewer" / "threejs" / "canonical_data.json"


def b64(array: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(array).tobytes()).decode()


def bone_table(rig) -> dict:
    """Bones as three.js wants them: a parent index and a local offset each."""
    heads = np.array([bone.head_cm for bone in rig.bones], dtype=np.float64) * 0.01
    # The root has no parent, which arrives as None; three.js wants -1.
    parents = [-1 if bone.parent_index is None else int(bone.parent_index) for bone in rig.bones]
    local = heads.copy()
    for index, parent in enumerate(parents):
        if parent >= 0:
            local[index] = heads[index] - heads[parent]
    # Direction each bone points at rest. Poses are authored anatomically, as a
    # bend or a twist, and this is what lets the client turn that into a
    # rotation in the bone's own frame. The rig rests in an A-pose with the arms
    # already down, so no axis can be assumed from the bone's name.
    tails = np.array([bone.tail_cm for bone in rig.bones], dtype=np.float64) * 0.01
    direction = tails - heads
    lengths = np.linalg.norm(direction, axis=1, keepdims=True)
    direction = direction / np.where(lengths < 1e-9, 1.0, lengths)

    return {
        "names": [bone.name for bone in rig.bones],
        "parents": parents,
        "local": [[round(float(v), 6) for v in row] for row in local],
        "direction": [[round(float(v), 5) for v in row] for row in direction],
        "restHead": [[round(float(v), 5) for v in row] for row in heads],
    }


def main() -> int:
    rig = load_canonical_rig()
    payload: dict = {
        "rigId": rig.rig_id,
        "topologyId": rig.topology_id,
        "bones": bone_table(rig),
        "skinIndex": b64(rig.joint_indices.astype(np.uint16)),
        "skinWeight": b64(rig.weights.astype(np.float32)),
        "order": [],
        "figures": {},
    }

    for kind in ("man", "woman", "child"):
        params = figure(kind)
        body, deformed, _ = deform_canonical_human(params)
        vertices, faces, normals = drawable(body)
        if "indices" not in payload:
            payload["indices"] = b64(faces)
            payload["vertexCount"] = int(body.vertex_count)
            payload["triangleCount"] = int(faces.size // 3)

        payload["order"].append(kind)
        bone_heads = {bone.name: np.asarray(bone.head_cm, dtype=float) for bone in deformed.bones}
        payload["figures"][kind] = {
            "label": f"{kind.title()} {DEFAULT_HEIGHT_CM[kind]:.0f} cm",
            "positions": b64(vertices),
            "normals": b64(normals),
            # Each figure has its own skeleton: a child is not a scaled adult.
            "bones": bone_table(deformed),
            "measurements": {k: round(float(v), 1) for k, v in measurements(params).items()},
            # Rigid volumes, so a viewer can refuse a pose that drives a limb
            # into the body. Per figure, because a child's are not an adult's
            # scaled down.
            "volumes": {
                # A three.js bone matrix expects local coordinates.  Canonical
                # capsules are model-space for the reconstruction solver, so
                # convert only at this runtime boundary.
                group: [c.to_bone_local_dict(bone_heads[c.bone]) for c in capsules]
                for group, capsules in body_volumes(body, deformed).items()
            },
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload), encoding="utf-8")
    print(
        f"wrote {OUT.name}: {payload['vertexCount']} vertices, "
        f"{payload['triangleCount']} triangles, {len(rig.bones)} bones, "
        f"{OUT.stat().st_size // 1024} KB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
