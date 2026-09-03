"""Cage rings to a triangulated surface.

V1 lofts the cage directly: each pair of adjacent rings becomes a band of
triangles, and open ends get a fan cap. Subdivision raises density without
moving the surface.

TODO (Phase 3+): replace this with a real cage deformation of a fixed canonical
base mesh - mean-value or harmonic coordinates - so topology is identical across
users and morph targets, UVs and garment fitting transfer between them.
`assets/base_mesh/` is reserved for that mesh. Until then topology is
deterministic for a given set of cage resolutions, but it is generated rather
than authored, which is not yet the consistent-topology guarantee the design
calls for.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sveyra_human.body.cage import BodyCage, CagePart


@dataclass(frozen=True)
class SurfaceMesh:
    vertices: np.ndarray  # (n, 3) float32
    faces: np.ndarray  # (m, 3) uint32

    @property
    def vertex_count(self) -> int:
        return int(self.vertices.shape[0])

    @property
    def face_count(self) -> int:
        return int(self.faces.shape[0])

    def normals(self) -> np.ndarray:
        """Area-weighted vertex normals."""
        normals = np.zeros(self.vertices.shape, dtype=np.float64)
        tris = self.vertices[self.faces]
        face_n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        for i in range(3):
            np.add.at(normals, self.faces[:, i], face_n)
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        lengths[lengths == 0.0] = 1.0
        return (normals / lengths).astype(np.float32)

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.vertices.min(axis=0), self.vertices.max(axis=0)


def _loft_part(part: CagePart, offset: int) -> tuple[np.ndarray, np.ndarray]:
    rings = part.rings
    levels, segments = part.levels, part.segments
    verts = rings.reshape(-1, 3)
    faces: list[tuple[int, int, int]] = []

    for level in range(levels - 1):
        base = offset + level * segments
        nxt = base + segments
        for s in range(segments):
            s2 = (s + 1) % segments
            faces.append((base + s, nxt + s, nxt + s2))
            faces.append((base + s, nxt + s2, base + s2))

    extra: list[np.ndarray] = []
    if part.closed_bottom:
        centre_idx = offset + levels * segments + len(extra)
        extra.append(rings[0].mean(axis=0))
        for s in range(segments):
            s2 = (s + 1) % segments
            faces.append((centre_idx, offset + s2, offset + s))
    if part.closed_top:
        centre_idx = offset + levels * segments + len(extra)
        extra.append(rings[-1].mean(axis=0))
        top = offset + (levels - 1) * segments
        for s in range(segments):
            s2 = (s + 1) % segments
            faces.append((centre_idx, top + s, top + s2))

    if extra:
        verts = np.vstack([verts, np.stack(extra)])
    return verts, np.array(faces, dtype=np.uint32)


def cage_to_mesh(cage: BodyCage, subdivisions: int = 1) -> SurfaceMesh:
    """Loft every cage part and concatenate the result into one mesh."""
    all_verts: list[np.ndarray] = []
    all_faces: list[np.ndarray] = []
    offset = 0
    for part in cage.parts:
        verts, faces = _loft_part(part, offset)
        all_verts.append(verts)
        all_faces.append(faces)
        offset += int(verts.shape[0])

    mesh = SurfaceMesh(
        vertices=np.vstack(all_verts).astype(np.float32),
        faces=np.vstack(all_faces).astype(np.uint32),
    )
    for _ in range(max(0, subdivisions)):
        mesh = subdivide(mesh)
    return mesh


def subdivide(mesh: SurfaceMesh) -> SurfaceMesh:
    """One round of midpoint (4-to-1) subdivision.

    Raises density without moving the surface, so the silhouette a Phase 3
    optimiser sees does not shift with render resolution.
    """
    verts = [v for v in mesh.vertices]
    midpoint: dict[tuple[int, int], int] = {}

    def mid(a: int, b: int) -> int:
        key = (a, b) if a < b else (b, a)
        found = midpoint.get(key)
        if found is None:
            found = len(verts)
            verts.append((mesh.vertices[a] + mesh.vertices[b]) / 2.0)
            midpoint[key] = found
        return found

    faces: list[tuple[int, int, int]] = []
    for tri in mesh.faces:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
        faces.extend([(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)])

    return SurfaceMesh(
        vertices=np.array(verts, dtype=np.float32),
        faces=np.array(faces, dtype=np.uint32),
    )
