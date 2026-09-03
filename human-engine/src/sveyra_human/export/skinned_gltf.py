"""Skinned GLB export.

A glTF skin needs three things the unskinned path does not: a node per joint
with local transforms, an inverse bind matrix per joint, and per-vertex joint
indices and weights. Assembling those is fiddly enough to keep apart from the
plain mesh export.

Everything is metres, Y up, right handed. The engine works in centimetres, so
the conversion happens here and nowhere else.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pygltflib

from sveyra_human.body.mesh_deformer import SurfaceMesh
from sveyra_human.rig.skeleton import (
    effective_parent,
    inverse_bind_matrices,
    joint_order,
    local_translations,
)
from sveyra_human.rig.weights import compute_skin_weights, validate_weights
from sveyra_human.skeleton.model import Skeleton

CM_TO_M = 0.01


def _pad(data: bytes, alignment: int = 4) -> bytes:
    remainder = len(data) % alignment
    return data if remainder == 0 else data + b"\x00" * (alignment - remainder)


def export_skinned_glb(
    mesh: SurfaceMesh, skeleton: Skeleton, path: str | Path, name: str = "SveyraHuman"
) -> Path:
    """Write a rigged GLB: mesh, skeleton, and skin weights."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    order = joint_order()
    indices_per_vertex, weights, bone_names = compute_skin_weights(mesh.vertices, skeleton)
    validate_weights(indices_per_vertex, weights, len(bone_names))
    if bone_names != order:
        raise RuntimeError("skin weight bone order does not match the joint order")

    positions = (mesh.vertices * CM_TO_M).astype(np.float32)
    normals = mesh.normals().astype(np.float32)
    triangles = mesh.faces.astype(np.uint32).reshape(-1)
    joints = indices_per_vertex.astype(np.uint16)
    skin_weights = weights.astype(np.float32)
    ibm = inverse_bind_matrices(skeleton, order)
    # glTF matrices are column-major.
    ibm_bytes = _pad(np.transpose(ibm, (0, 2, 1)).astype(np.float32).tobytes())

    chunks = [
        _pad(positions.tobytes()),
        _pad(normals.tobytes()),
        _pad(triangles.tobytes()),
        _pad(joints.tobytes()),
        _pad(skin_weights.tobytes()),
        ibm_bytes,
    ]
    offsets: list[int] = []
    running = 0
    for chunk in chunks:
        offsets.append(running)
        running += len(chunk)
    blob = b"".join(chunks)

    targets = [
        pygltflib.ARRAY_BUFFER,
        pygltflib.ARRAY_BUFFER,
        pygltflib.ELEMENT_ARRAY_BUFFER,
        pygltflib.ARRAY_BUFFER,
        pygltflib.ARRAY_BUFFER,
        None,  # inverse bind matrices are not a vertex attribute
    ]
    buffer_views = [
        pygltflib.BufferView(
            buffer=0, byteOffset=offset, byteLength=len(chunk), target=target
        )
        for offset, chunk, target in zip(offsets, chunks, targets, strict=True)
    ]

    accessors = [
        pygltflib.Accessor(
            bufferView=0,
            componentType=pygltflib.FLOAT,
            count=len(positions),
            type=pygltflib.VEC3,
            min=positions.min(axis=0).tolist(),
            max=positions.max(axis=0).tolist(),
        ),
        pygltflib.Accessor(
            bufferView=1, componentType=pygltflib.FLOAT, count=len(normals), type=pygltflib.VEC3
        ),
        pygltflib.Accessor(
            bufferView=2,
            componentType=pygltflib.UNSIGNED_INT,
            count=len(triangles),
            type=pygltflib.SCALAR,
        ),
        pygltflib.Accessor(
            bufferView=3,
            componentType=pygltflib.UNSIGNED_SHORT,
            count=len(joints),
            type=pygltflib.VEC4,
        ),
        pygltflib.Accessor(
            bufferView=4,
            componentType=pygltflib.FLOAT,
            count=len(skin_weights),
            type=pygltflib.VEC4,
        ),
        pygltflib.Accessor(
            bufferView=5, componentType=pygltflib.FLOAT, count=len(order), type=pygltflib.MAT4
        ),
    ]

    # Node 0 is the mesh; joints follow, so joint i is node i + 1.
    translations = local_translations(skeleton, order)
    nodes: list[pygltflib.Node] = [pygltflib.Node(mesh=0, skin=0, name=name)]
    for joint in order:
        children = [
            order.index(other) + 1
            for other in order
            if effective_parent(other, order) == joint
        ]
        nodes.append(
            pygltflib.Node(
                name=joint,
                translation=[float(v) for v in translations[joint]],
                children=children or None,
            )
        )

    roots = [order.index(j) + 1 for j in order if effective_parent(j, order) is None]

    gltf = pygltflib.GLTF2(
        scene=0,
        scenes=[pygltflib.Scene(nodes=[0, *roots])],
        nodes=nodes,
        meshes=[
            pygltflib.Mesh(
                name=name,
                primitives=[
                    pygltflib.Primitive(
                        attributes=pygltflib.Attributes(
                            POSITION=0, NORMAL=1, JOINTS_0=3, WEIGHTS_0=4
                        ),
                        indices=2,
                        material=0,
                    )
                ],
            )
        ],
        skins=[
            pygltflib.Skin(
                name="SveyraSkeleton",
                inverseBindMatrices=5,
                joints=[order.index(j) + 1 for j in order],
                skeleton=roots[0] if roots else None,
            )
        ],
        materials=[
            pygltflib.Material(
                name="skin_placeholder",
                pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                    baseColorFactor=[0.76, 0.63, 0.55, 1.0],
                    metallicFactor=0.0,
                    roughnessFactor=0.85,
                ),
                doubleSided=False,
            )
        ],
        accessors=accessors,
        bufferViews=buffer_views,
        buffers=[pygltflib.Buffer(byteLength=len(blob))],
    )

    gltf.set_binary_blob(blob)
    gltf.save_binary(str(target))
    _assert_readable(target)
    return target


def _assert_readable(path: Path) -> None:
    with path.open("rb") as handle:
        magic, version, _ = struct.unpack("<III", handle.read(12))
    if magic != 0x46546C67 or version != 2:
        raise RuntimeError(f"{path} is not a valid GLB container")
