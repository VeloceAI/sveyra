"""Portable skinned GLB export for the fixed canonical human topology."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pygltflib

from sveyra_human.canonical.body import CanonicalBodyMesh
from sveyra_human.canonical.rig import CanonicalRig

CM_TO_M = 0.01


def _pad(data: bytes, alignment: int = 4) -> bytes:
    remainder = len(data) % alignment
    return data if remainder == 0 else data + b"\x00" * (alignment - remainder)


def export_canonical_skinned_glb(
    body: CanonicalBodyMesh,
    rig: CanonicalRig,
    path: str | Path,
    name: str = "SveyraCanonicalHuman",
) -> Path:
    """Write a canonical body and its validated 163-joint rest rig as GLB."""
    if (body.topology_id, body.topology_version) != (
        rig.topology_id,
        rig.topology_version,
    ):
        raise ValueError("body and rig target different canonical topologies")
    if body.vertex_count != rig.vertex_count:
        raise ValueError("body vertex count does not match canonical skin weights")

    mesh = body.to_surface_mesh(with_uv=False)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    positions = (mesh.vertices * CM_TO_M).astype(np.float32)
    normals = mesh.normals().astype(np.float32)
    triangles = mesh.faces.astype(np.uint32).reshape(-1)
    joints = rig.joint_indices.astype(np.uint16)
    weights = rig.weights.astype(np.float32)
    inverse_bind = rig.inverse_bind_matrices_m()
    inverse_bind_bytes = _pad(
        np.transpose(inverse_bind, (0, 2, 1)).astype(np.float32).tobytes()
    )

    chunks = [
        _pad(positions.tobytes()),
        _pad(normals.tobytes()),
        _pad(triangles.tobytes()),
        _pad(joints.tobytes()),
        _pad(weights.tobytes()),
        inverse_bind_bytes,
    ]
    offsets: list[int] = []
    running = 0
    for chunk in chunks:
        offsets.append(running)
        running += len(chunk)
    blob = b"".join(chunks)

    buffer_views = [
        pygltflib.BufferView(
            buffer=0,
            byteOffset=offset,
            byteLength=len(chunk),
            target=buffer_target,
        )
        for offset, chunk, buffer_target in zip(
            offsets,
            chunks,
            [
                pygltflib.ARRAY_BUFFER,
                pygltflib.ARRAY_BUFFER,
                pygltflib.ELEMENT_ARRAY_BUFFER,
                pygltflib.ARRAY_BUFFER,
                pygltflib.ARRAY_BUFFER,
                None,
            ],
            strict=True,
        )
    ]
    accessors = [
        pygltflib.Accessor(
            bufferView=0,
            componentType=pygltflib.FLOAT,
            count=body.vertex_count,
            type=pygltflib.VEC3,
            min=positions.min(axis=0).tolist(),
            max=positions.max(axis=0).tolist(),
        ),
        pygltflib.Accessor(
            bufferView=1,
            componentType=pygltflib.FLOAT,
            count=body.vertex_count,
            type=pygltflib.VEC3,
        ),
        pygltflib.Accessor(
            bufferView=2,
            componentType=pygltflib.UNSIGNED_INT,
            count=int(triangles.size),
            type=pygltflib.SCALAR,
        ),
        pygltflib.Accessor(
            bufferView=3,
            componentType=pygltflib.UNSIGNED_SHORT,
            count=body.vertex_count,
            type=pygltflib.VEC4,
        ),
        pygltflib.Accessor(
            bufferView=4,
            componentType=pygltflib.FLOAT,
            count=body.vertex_count,
            type=pygltflib.VEC4,
        ),
        pygltflib.Accessor(
            bufferView=5,
            componentType=pygltflib.FLOAT,
            count=rig.joint_count,
            type=pygltflib.MAT4,
        ),
    ]

    local_translations = rig.local_translations_cm()
    joint_nodes = [
        pygltflib.Node(
            name=bone.name,
            translation=(local_translations[index] * CM_TO_M).tolist(),
            extras={
                "tailCm": list(bone.tail_cm),
                "sourceRollRadians": bone.source_roll_radians,
            },
        )
        for index, bone in enumerate(rig.bones)
    ]
    children: list[list[int]] = [[] for _ in rig.bones]
    for index, bone in enumerate(rig.bones):
        if bone.parent_index is not None:
            children[bone.parent_index].append(index + 1)
    for index, node_children in enumerate(children):
        if node_children:
            joint_nodes[index].children = node_children

    root_nodes = [index + 1 for index in rig.root_indices]
    gltf = pygltflib.GLTF2(
        scene=0,
        scenes=[pygltflib.Scene(nodes=[0, *root_nodes])],
        nodes=[pygltflib.Node(name=name, mesh=0, skin=0), *joint_nodes],
        meshes=[
            pygltflib.Mesh(
                name=name,
                primitives=[
                    pygltflib.Primitive(
                        attributes=pygltflib.Attributes(
                            POSITION=0,
                            NORMAL=1,
                            JOINTS_0=3,
                            WEIGHTS_0=4,
                        ),
                        indices=2,
                        material=0,
                    )
                ],
                extras={
                    "topologyId": body.topology_id,
                    "topologyVersion": body.topology_version,
                },
            )
        ],
        skins=[
            pygltflib.Skin(
                name=rig.rig_id,
                inverseBindMatrices=5,
                joints=[index + 1 for index in range(rig.joint_count)],
                skeleton=root_nodes[0],
            )
        ],
        materials=[
            pygltflib.Material(
                name="skin_neutral_placeholder",
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
        asset=pygltflib.Asset(generator="Sveyra Human Engine", version="2.0"),
    )
    gltf.set_binary_blob(blob)
    gltf.save_binary(str(target))

    with target.open("rb") as stream:
        magic, version, length = struct.unpack("<III", stream.read(12))
    if magic != 0x46546C67 or version != 2 or length != target.stat().st_size:
        raise RuntimeError("exported canonical GLB failed container validation")
    return target
