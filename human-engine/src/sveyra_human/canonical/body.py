"""Load the reviewed fixed-topology body seed into Sveyra's geometry model."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from sveyra_human.body.mesh_deformer import SurfaceMesh
from sveyra_human.canonical.obj import ObjDocument, load_obj
from sveyra_human.canonical.topology import analyze_topology, canonical_mesh_issues

CANONICAL_TOPOLOGY_ID = "sveyra-hm08-body"
CANONICAL_TOPOLOGY_VERSION = "0.1"
CANONICAL_ASSET_SHA256 = "b013ab2867f3fd924a9edfc4a1820698250c2543642b51057491498c6fed2bc0"
OBJ_UNIT_TO_CM = 10.0


class CanonicalAssetError(ValueError):
    """Raised when the canonical seed no longer matches its reviewed contract."""


def canonical_asset_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "canonical" / "hm08_body_cc0.obj"


def _triangulate(indices: tuple[int, ...]) -> list[tuple[int, int, int]]:
    return [
        (indices[0], indices[offset], indices[offset + 1])
        for offset in range(1, len(indices) - 1)
    ]


@dataclass(frozen=True)
class CanonicalBodyMesh:
    """Editable canonical positions with fixed faces and independent OBJ UVs.

    Identity fitting deforms ``vertices_cm`` without changing ``polygons``.
    UV seams are split only when a renderer-ready ``SurfaceMesh`` is requested,
    preserving one stable anatomical vertex index for fitting and morph targets.
    """

    vertices_cm: np.ndarray
    polygons: tuple[tuple[int, ...], ...]
    texture_coordinates: np.ndarray
    polygon_texture_indices: tuple[tuple[int, ...], ...]
    topology_id: str = CANONICAL_TOPOLOGY_ID
    topology_version: str = CANONICAL_TOPOLOGY_VERSION

    @property
    def vertex_count(self) -> int:
        return int(self.vertices_cm.shape[0])

    @property
    def polygon_count(self) -> int:
        return len(self.polygons)

    @property
    def triangle_count(self) -> int:
        return sum(len(polygon) - 2 for polygon in self.polygons)

    @property
    def height_cm(self) -> float:
        return float(np.ptp(self.vertices_cm[:, 1]))

    def scaled_to_height(self, height_cm: float) -> CanonicalBodyMesh:
        """Return the neutral seed at a requested metric height, standing on Y=0."""
        if not math.isfinite(height_cm) or height_cm <= 0:
            raise ValueError("height_cm must be finite and positive")
        vertices = self.vertices_cm.astype(np.float64, copy=True)
        vertices[:, 1] -= vertices[:, 1].min()
        current_height = float(vertices[:, 1].max())
        if current_height <= 0:
            raise CanonicalAssetError("canonical body has no vertical extent")
        vertices *= height_cm / current_height
        return replace(self, vertices_cm=vertices.astype(np.float32))

    def to_surface_mesh(self, with_uv: bool = True) -> SurfaceMesh:
        """Triangulate the canonical polygons and optionally split vertices at UV seams."""
        if not with_uv:
            faces = [triangle for polygon in self.polygons for triangle in _triangulate(polygon)]
            return SurfaceMesh(
                vertices=self.vertices_cm.astype(np.float32, copy=True),
                faces=np.asarray(faces, dtype=np.uint32),
            )

        render_vertices: list[np.ndarray] = []
        render_uvs: list[np.ndarray] = []
        corner_map: dict[tuple[int, int], int] = {}
        render_faces: list[tuple[int, int, int]] = []
        for polygon, texture_polygon in zip(
            self.polygons, self.polygon_texture_indices, strict=True
        ):
            render_polygon: list[int] = []
            for vertex_index, texture_index in zip(polygon, texture_polygon, strict=True):
                key = (vertex_index, texture_index)
                render_index = corner_map.get(key)
                if render_index is None:
                    render_index = len(render_vertices)
                    corner_map[key] = render_index
                    render_vertices.append(self.vertices_cm[vertex_index])
                    render_uvs.append(self.texture_coordinates[texture_index, :2])
                render_polygon.append(render_index)
            render_faces.extend(_triangulate(tuple(render_polygon)))

        return SurfaceMesh(
            vertices=np.asarray(render_vertices, dtype=np.float32),
            faces=np.asarray(render_faces, dtype=np.uint32),
            uv=np.asarray(render_uvs, dtype=np.float32),
        )


def _from_document(document: ObjDocument) -> CanonicalBodyMesh:
    report = analyze_topology(document)
    issues = canonical_mesh_issues(report)
    if issues:
        raise CanonicalAssetError("canonical body failed validation: " + "; ".join(issues))

    polygon_texture_indices: list[tuple[int, ...]] = []
    for face in document.faces:
        if any(index is None for index in face.texture_indices):
            raise CanonicalAssetError(f"line {face.line_number}: canonical face has no UV")
        polygon_texture_indices.append(tuple(int(index) for index in face.texture_indices))

    return CanonicalBodyMesh(
        vertices_cm=np.asarray(document.vertices, dtype=np.float32) * OBJ_UNIT_TO_CM,
        polygons=tuple(face.vertex_indices for face in document.faces),
        texture_coordinates=np.asarray(document.texture_coordinates, dtype=np.float32),
        polygon_texture_indices=tuple(polygon_texture_indices),
    )


def load_canonical_body(path: str | Path | None = None) -> CanonicalBodyMesh:
    """Load and validate a canonical OBJ; the bundled seed is hash-pinned."""
    source = canonical_asset_path() if path is None else Path(path)
    if path is None:
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != CANONICAL_ASSET_SHA256:
            raise CanonicalAssetError(
                "bundled canonical asset hash changed; update it only through a reviewed migration"
            )
    return _from_document(load_obj(source))
