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
from sveyra_human.canonical.deformation import deform_canonical_human  # noqa: E402
from sveyra_human.canonical.rig import load_canonical_rig  # noqa: E402

OUT = ROOT / "viewer" / "threejs" / "canonical_data.json"


def b64(array: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(array).tobytes()).decode()


def triangulate(polygons: tuple[tuple[int, ...], ...]) -> np.ndarray:
    """Fan triangulation. The base mesh is quads, so this is exact, not an
    approximation: a quad becomes its two triangles and nothing moves."""
    out: list[tuple[int, int, int]] = []
    for polygon in polygons:
        for i in range(1, len(polygon) - 1):
            out.append((polygon[0], polygon[i], polygon[i + 1]))
    return np.asarray(out, dtype=np.uint32).reshape(-1)


def vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Area weighted normals, which is what accumulating face normals gives."""
    normals = np.zeros_like(vertices)
    tri = faces.reshape(-1, 3)
    a, b, c = vertices[tri[:, 0]], vertices[tri[:, 1]], vertices[tri[:, 2]]
    face = np.cross(b - a, c - a)
    for column in range(3):
        np.add.at(normals, tri[:, column], face)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.where(lengths < 1e-12, 1.0, lengths)


def bone_table(rig) -> dict:
    """Bones as three.js wants them: a parent index and a local offset each."""
    heads = np.array([bone.head_cm for bone in rig.bones], dtype=np.float64) * 0.01
    # The root has no parent, which arrives as None; three.js wants -1.
    parents = [-1 if bone.parent_index is None else int(bone.parent_index) for bone in rig.bones]
    local = heads.copy()
    for index, parent in enumerate(parents):
        if parent >= 0:
            local[index] = heads[index] - heads[parent]
    return {
        "names": [bone.name for bone in rig.bones],
        "parents": parents,
        "local": [[round(float(v), 6) for v in row] for row in local],
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
        vertices = (body.vertices_cm * 0.01).astype(np.float32)
        faces = triangulate(body.polygons)
        if "indices" not in payload:
            payload["indices"] = b64(faces)
            payload["vertexCount"] = int(body.vertex_count)
            payload["triangleCount"] = int(faces.size // 3)

        payload["order"].append(kind)
        payload["figures"][kind] = {
            "label": f"{kind.title()} {DEFAULT_HEIGHT_CM[kind]:.0f} cm",
            "positions": b64(vertices),
            "normals": b64(vertex_normals(vertices.astype(np.float64), faces).astype(np.float32)),
            # Each figure has its own skeleton: a child is not a scaled adult.
            "bones": bone_table(deformed),
            "measurements": {k: round(float(v), 1) for k, v in measurements(params).items()},
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
