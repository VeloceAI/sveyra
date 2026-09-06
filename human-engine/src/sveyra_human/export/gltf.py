"""GLB export.

glTF is metres, Y up, right handed. The engine works in centimetres because
that is how humans are measured, so the scale conversion happens here and
nowhere else.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pygltflib

from sveyra_human.body.mesh_deformer import SurfaceMesh

CM_TO_M = 0.01


def _pad(data: bytes, alignment: int = 4) -> bytes:
    remainder = len(data) % alignment
    return data if remainder == 0 else data + b"\x00" * (alignment - remainder)


def export_glb(mesh: SurfaceMesh, path: str | Path, name: str = "SveyraHuman") -> Path:
    """Write a single-mesh GLB with positions, normals and indices."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    positions = (mesh.vertices * CM_TO_M).astype(np.float32)
    normals = mesh.normals().astype(np.float32)
    indices = mesh.faces.astype(np.uint32).reshape(-1)

    pos_bytes = _pad(positions.tobytes())
    nrm_bytes = _pad(normals.tobytes())
    idx_bytes = _pad(indices.tobytes())
    blob = pos_bytes + nrm_bytes + idx_bytes

    gltf = pygltflib.GLTF2(
        scene=0,
        scenes=[pygltflib.Scene(nodes=[0])],
        nodes=[pygltflib.Node(mesh=0, name=name)],
        meshes=[
            pygltflib.Mesh(
                name=name,
                primitives=[
                    pygltflib.Primitive(
                        attributes=pygltflib.Attributes(POSITION=0, NORMAL=1),
                        indices=2,
                        material=0,
                    )
                ],
            )
        ],
        materials=[
            pygltflib.Material(
                name="skin_placeholder",
                pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                    # Flat neutral. Real skin arrives with projective texturing
                    # in Phase 5; this is explicitly not a skin tone estimate.
                    baseColorFactor=[0.76, 0.63, 0.55, 1.0],
                    metallicFactor=0.0,
                    roughnessFactor=0.85,
                ),
                doubleSided=False,
            )
        ],
        accessors=[
            pygltflib.Accessor(
                bufferView=0,
                componentType=pygltflib.FLOAT,
                count=int(positions.shape[0]),
                type=pygltflib.VEC3,
                min=positions.min(axis=0).tolist(),
                max=positions.max(axis=0).tolist(),
            ),
            pygltflib.Accessor(
                bufferView=1,
                componentType=pygltflib.FLOAT,
                count=int(normals.shape[0]),
                type=pygltflib.VEC3,
            ),
            pygltflib.Accessor(
                bufferView=2,
                componentType=pygltflib.UNSIGNED_INT,
                count=int(indices.shape[0]),
                type=pygltflib.SCALAR,
            ),
        ],
        bufferViews=[
            pygltflib.BufferView(
                buffer=0,
                byteOffset=0,
                byteLength=len(pos_bytes),
                target=pygltflib.ARRAY_BUFFER,
            ),
            pygltflib.BufferView(
                buffer=0,
                byteOffset=len(pos_bytes),
                byteLength=len(nrm_bytes),
                target=pygltflib.ARRAY_BUFFER,
            ),
            pygltflib.BufferView(
                buffer=0,
                byteOffset=len(pos_bytes) + len(nrm_bytes),
                byteLength=len(idx_bytes),
                target=pygltflib.ELEMENT_ARRAY_BUFFER,
            ),
        ],
        buffers=[pygltflib.Buffer(byteLength=len(blob))],
    )

    gltf.set_binary_blob(blob)
    gltf.save_binary(str(target))
    _assert_readable(target)
    return target


def _assert_readable(path: Path) -> None:
    """Fail loudly here rather than in a viewer three steps downstream."""
    with path.open("rb") as handle:
        magic, version, _ = struct.unpack("<III", handle.read(12))
    if magic != 0x46546C67 or version != 2:
        raise RuntimeError(f"{path} is not a valid GLB container")
