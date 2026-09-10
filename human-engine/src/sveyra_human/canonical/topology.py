"""Topology evidence and acceptance rules for a canonical human body mesh."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass

from sveyra_human.canonical.obj import ObjDocument, ObjFace


@dataclass(frozen=True)
class TopologyReport:
    source_vertex_count: int
    referenced_vertex_count: int
    polygon_count: int
    triangle_count: int
    corner_count: int
    textured_corner_count: int
    normal_corner_count: int
    component_count: int
    boundary_edge_count: int
    non_manifold_edge_count: int
    inconsistent_winding_edge_count: int
    degenerate_face_count: int
    polygon_size_counts: dict[int, int]
    bounds_min: tuple[float, float, float] | None
    bounds_max: tuple[float, float, float] | None
    groups: tuple[str, ...]

    @property
    def is_watertight(self) -> bool:
        return (
            self.polygon_count > 0
            and self.boundary_edge_count == 0
            and self.non_manifold_edge_count == 0
        )

    @property
    def has_complete_uvs(self) -> bool:
        return self.corner_count > 0 and self.textured_corner_count == self.corner_count

    @property
    def extents(self) -> tuple[float, float, float] | None:
        if self.bounds_min is None or self.bounds_max is None:
            return None
        return tuple(high - low for low, high in zip(self.bounds_min, self.bounds_max, strict=True))

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["is_watertight"] = self.is_watertight
        data["has_complete_uvs"] = self.has_complete_uvs
        data["extents"] = self.extents
        return data


@dataclass(frozen=True)
class CanonicalMeshPolicy:
    minimum_vertices: int = 5_000
    maximum_vertices: int = 200_000
    require_single_component: bool = True
    require_watertight: bool = True
    require_consistent_winding: bool = True
    require_complete_uvs: bool = True
    allowed_polygon_sizes: tuple[int, ...] = (3, 4)


class _DisjointSet:
    def __init__(self, vertices: set[int]) -> None:
        self.parent = {vertex: vertex for vertex in vertices}

    def find(self, vertex: int) -> int:
        root = vertex
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[vertex] != vertex:
            parent = self.parent[vertex]
            self.parent[vertex] = root
            vertex = parent
        return root

    def union(self, first: int, second: int) -> None:
        first_root, second_root = self.find(first), self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


def _face_is_degenerate(face: ObjFace, document: ObjDocument) -> bool:
    indices = face.vertex_indices
    if len(set(indices)) != len(indices):
        return True

    origin = document.vertices[indices[0]]
    area_twice = [0.0, 0.0, 0.0]
    for offset in range(1, len(indices) - 1):
        first = document.vertices[indices[offset]]
        second = document.vertices[indices[offset + 1]]
        a = tuple(value - base for value, base in zip(first, origin, strict=True))
        b = tuple(value - base for value, base in zip(second, origin, strict=True))
        area_twice[0] += a[1] * b[2] - a[2] * b[1]
        area_twice[1] += a[2] * b[0] - a[0] * b[2]
        area_twice[2] += a[0] * b[1] - a[1] * b[0]
    return math.sqrt(sum(value * value for value in area_twice)) <= 1e-12


def analyze_topology(document: ObjDocument, group: str | None = None) -> TopologyReport:
    faces = document.faces_in_group(group)
    used_vertices = {index for face in faces for index in face.vertex_indices}
    directed_edges: Counter[tuple[int, int]] = Counter()
    undirected_edges: Counter[tuple[int, int]] = Counter()
    groups: list[str] = []

    disjoint = _DisjointSet(used_vertices)
    for face in faces:
        for face_group in face.groups:
            if face_group not in groups:
                groups.append(face_group)
        for position, start in enumerate(face.vertex_indices):
            end = face.vertex_indices[(position + 1) % len(face.vertex_indices)]
            directed_edges[(start, end)] += 1
            key = (start, end) if start < end else (end, start)
            undirected_edges[key] += 1
            disjoint.union(start, end)

    component_count = len({disjoint.find(vertex) for vertex in used_vertices})
    boundary_edges = sum(count == 1 for count in undirected_edges.values())
    non_manifold_edges = sum(count > 2 for count in undirected_edges.values())
    inconsistent_winding = sum(
        count == 2
        and (directed_edges[(first, second)] == 2 or directed_edges[(second, first)] == 2)
        for (first, second), count in undirected_edges.items()
    )

    selected_vertices = [document.vertices[index] for index in used_vertices]
    bounds_min = None
    bounds_max = None
    if selected_vertices:
        bounds_min = tuple(min(vertex[axis] for vertex in selected_vertices) for axis in range(3))
        bounds_max = tuple(max(vertex[axis] for vertex in selected_vertices) for axis in range(3))

    polygon_sizes = Counter(len(face.vertex_indices) for face in faces)
    return TopologyReport(
        source_vertex_count=len(document.vertices),
        referenced_vertex_count=len(used_vertices),
        polygon_count=len(faces),
        triangle_count=sum(max(0, len(face.vertex_indices) - 2) for face in faces),
        corner_count=sum(len(face.vertex_indices) for face in faces),
        textured_corner_count=sum(
            index is not None for face in faces for index in face.texture_indices
        ),
        normal_corner_count=sum(
            index is not None for face in faces for index in face.normal_indices
        ),
        component_count=component_count,
        boundary_edge_count=boundary_edges,
        non_manifold_edge_count=non_manifold_edges,
        inconsistent_winding_edge_count=inconsistent_winding,
        degenerate_face_count=sum(_face_is_degenerate(face, document) for face in faces),
        polygon_size_counts=dict(sorted(polygon_sizes.items())),
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        groups=tuple(groups),
    )


def canonical_mesh_issues(
    report: TopologyReport,
    policy: CanonicalMeshPolicy | None = None,
) -> list[str]:
    policy = policy or CanonicalMeshPolicy()
    issues: list[str] = []
    if report.polygon_count == 0:
        return ["mesh has no faces"]
    if report.referenced_vertex_count < policy.minimum_vertices:
        issues.append(
            f"mesh needs at least {policy.minimum_vertices} referenced vertices "
            f"(found {report.referenced_vertex_count})"
        )
    if report.referenced_vertex_count > policy.maximum_vertices:
        issues.append(
            f"mesh exceeds {policy.maximum_vertices} referenced vertices "
            f"(found {report.referenced_vertex_count})"
        )
    if policy.require_single_component and report.component_count != 1:
        issues.append(
            f"body surface must be one connected component (found {report.component_count})"
        )
    if policy.require_watertight and not report.is_watertight:
        issues.append(
            "body surface must be watertight "
            f"({report.boundary_edge_count} boundary, "
            f"{report.non_manifold_edge_count} non-manifold edges)"
        )
    if policy.require_consistent_winding and report.inconsistent_winding_edge_count:
        issues.append(
            "body surface has "
            f"{report.inconsistent_winding_edge_count} inconsistently wound shared edges"
        )
    if report.degenerate_face_count:
        issues.append(f"body surface has {report.degenerate_face_count} degenerate faces")
    unsupported = sorted(set(report.polygon_size_counts) - set(policy.allowed_polygon_sizes))
    if unsupported:
        issues.append(f"body surface has unsupported polygon sizes: {unsupported}")
    if policy.require_complete_uvs and not report.has_complete_uvs:
        issues.append(
            f"every face corner needs a UV ({report.textured_corner_count}/{report.corner_count})"
        )
    return issues
