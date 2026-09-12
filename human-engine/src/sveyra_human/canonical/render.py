"""Turning the canonical mesh into something a renderer can draw.

Kept unsplit. `to_surface_mesh` splits vertices at UV seams, which breaks the
one-to-one correspondence with the skin weight table and with anything else
indexed by canonical vertex. There are no textures yet to justify paying that,
and the viewer and the reconstruction server both need the same vertex count or
they cannot exchange a body.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.canonical.body import CanonicalBodyMesh


def triangulate(polygons: tuple[tuple[int, ...], ...]) -> np.ndarray:
    """Fan triangulation, exact for the quads this mesh is made of."""
    out: list[tuple[int, int, int]] = []
    for polygon in polygons:
        for i in range(1, len(polygon) - 1):
            out.append((polygon[0], polygon[i], polygon[i + 1]))
    return np.asarray(out, dtype=np.uint32).reshape(-1)


def vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Area-weighted normals, which is what accumulating face normals gives."""
    normals = np.zeros_like(vertices, dtype=np.float64)
    tri = faces.reshape(-1, 3)
    a, b, c = vertices[tri[:, 0]], vertices[tri[:, 1]], vertices[tri[:, 2]]
    face = np.cross(b - a, c - a)
    for column in range(3):
        np.add.at(normals, tri[:, column], face)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.where(lengths < 1e-12, 1.0, lengths)


def drawable(body: CanonicalBodyMesh) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Positions in metres, triangle indices, and normals, all unsplit."""
    vertices = (body.vertices_cm * 0.01).astype(np.float32)
    faces = triangulate(body.polygons)
    normals = vertex_normals(vertices.astype(np.float64), faces).astype(np.float32)
    return vertices, faces, normals
