"""Small, strict Wavefront OBJ reader for canonical-mesh ingestion.

This is intentionally an original, dependency-free parser.  It implements the
geometry subset Sveyra needs and preserves group membership and independent OBJ
index streams so imported assets can be audited before they enter the engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


class ObjParseError(ValueError):
    """Raised when an OBJ cannot be interpreted without guessing."""


@dataclass(frozen=True)
class ObjFace:
    vertex_indices: tuple[int, ...]
    texture_indices: tuple[int | None, ...]
    normal_indices: tuple[int | None, ...]
    groups: tuple[str, ...]
    line_number: int


@dataclass(frozen=True)
class ObjDocument:
    vertices: tuple[tuple[float, float, float], ...]
    texture_coordinates: tuple[tuple[float, ...], ...]
    normals: tuple[tuple[float, float, float], ...]
    faces: tuple[ObjFace, ...]
    groups: tuple[str, ...]

    @property
    def texture_coordinate_count(self) -> int:
        return len(self.texture_coordinates)

    @property
    def normal_count(self) -> int:
        return len(self.normals)

    def faces_in_group(self, group: str | None = None) -> tuple[ObjFace, ...]:
        if group is None:
            return self.faces
        return tuple(face for face in self.faces if group in face.groups)


def _parse_index(token: str, count: int, kind: str, line_number: int) -> int:
    try:
        raw = int(token)
    except ValueError as exc:
        raise ObjParseError(f"line {line_number}: invalid {kind} index {token!r}") from exc
    if raw == 0:
        raise ObjParseError(f"line {line_number}: OBJ {kind} indices cannot be zero")
    resolved = raw - 1 if raw > 0 else count + raw
    if resolved < 0:
        raise ObjParseError(f"line {line_number}: {kind} index {raw} is out of range")
    return resolved


def _parse_face_corner(
    token: str,
    vertex_count: int,
    texture_count: int,
    normal_count: int,
    line_number: int,
) -> tuple[int, int | None, int | None]:
    parts = token.split("/")
    if not parts[0] or len(parts) > 3:
        raise ObjParseError(f"line {line_number}: invalid face corner {token!r}")

    vertex = _parse_index(parts[0], vertex_count, "vertex", line_number)
    texture = None
    normal = None
    if len(parts) >= 2 and parts[1]:
        texture = _parse_index(parts[1], texture_count, "texture", line_number)
    if len(parts) == 3 and parts[2]:
        normal = _parse_index(parts[2], normal_count, "normal", line_number)
    return vertex, texture, normal


def _load_obj_stream(stream: TextIO) -> ObjDocument:
    vertices: list[tuple[float, float, float]] = []
    texture_coordinates: list[tuple[float, ...]] = []
    normals: list[tuple[float, float, float]] = []
    faces: list[ObjFace] = []
    active_groups: tuple[str, ...] = ("default",)
    encountered_groups: list[str] = []

    for line_number, raw_line in enumerate(stream, start=1):
        content = raw_line.partition("#")[0].strip()
        if not content:
            continue
        fields = content.split()
        record, values = fields[0], fields[1:]

        if record == "v":
            if len(values) < 3:
                raise ObjParseError(f"line {line_number}: vertex needs three coordinates")
            try:
                vertex = (float(values[0]), float(values[1]), float(values[2]))
            except ValueError as exc:
                raise ObjParseError(f"line {line_number}: invalid vertex coordinates") from exc
            if not all(math.isfinite(value) for value in vertex):
                raise ObjParseError(f"line {line_number}: vertex coordinates must be finite")
            vertices.append(vertex)
        elif record == "vt":
            if len(values) < 2:
                raise ObjParseError(f"line {line_number}: texture coordinate needs two values")
            try:
                texture = tuple(float(value) for value in values[:3])
            except ValueError as exc:
                raise ObjParseError(
                    f"line {line_number}: invalid texture coordinates"
                ) from exc
            if not all(math.isfinite(value) for value in texture):
                raise ObjParseError(f"line {line_number}: texture coordinates must be finite")
            texture_coordinates.append(texture)
        elif record == "vn":
            if len(values) < 3:
                raise ObjParseError(f"line {line_number}: normal needs three coordinates")
            try:
                normal = (float(values[0]), float(values[1]), float(values[2]))
            except ValueError as exc:
                raise ObjParseError(f"line {line_number}: invalid normal coordinates") from exc
            if not all(math.isfinite(value) for value in normal):
                raise ObjParseError(f"line {line_number}: normal coordinates must be finite")
            normals.append(normal)
        elif record == "g":
            active_groups = tuple(values) if values else ("default",)
            for group in active_groups:
                if group not in encountered_groups:
                    encountered_groups.append(group)
        elif record == "f":
            if len(values) < 3:
                raise ObjParseError(f"line {line_number}: face needs at least three corners")
            corners = [
                _parse_face_corner(
                    value,
                    len(vertices),
                    len(texture_coordinates),
                    len(normals),
                    line_number,
                )
                for value in values
            ]
            faces.append(
                ObjFace(
                    vertex_indices=tuple(corner[0] for corner in corners),
                    texture_indices=tuple(corner[1] for corner in corners),
                    normal_indices=tuple(corner[2] for corner in corners),
                    groups=active_groups,
                    line_number=line_number,
                )
            )

    for face in faces:
        for index in face.vertex_indices:
            if index >= len(vertices):
                raise ObjParseError(
                    f"line {face.line_number}: vertex index {index + 1} is out of range"
                )
        for index in face.texture_indices:
            if index is not None and index >= len(texture_coordinates):
                raise ObjParseError(
                    f"line {face.line_number}: texture index {index + 1} is out of range"
                )
        for index in face.normal_indices:
            if index is not None and index >= len(normals):
                raise ObjParseError(
                    f"line {face.line_number}: normal index {index + 1} is out of range"
                )

    return ObjDocument(
        vertices=tuple(vertices),
        texture_coordinates=tuple(texture_coordinates),
        normals=tuple(normals),
        faces=tuple(faces),
        groups=tuple(encountered_groups),
    )


def load_obj(path: str | Path) -> ObjDocument:
    """Load the auditable geometry subset of a Wavefront OBJ file."""
    with Path(path).open(encoding="utf-8-sig") as stream:
        return _load_obj_stream(stream)


def _format_number(value: float) -> str:
    return format(value, ".10g")


def write_obj_group(
    document: ObjDocument,
    path: str | Path,
    group: str,
    comments: tuple[str, ...] = (),
) -> None:
    """Write one group as a compact OBJ with deterministic, remapped indices."""
    faces = document.faces_in_group(group)
    if not faces:
        raise ValueError(f"OBJ group {group!r} has no faces")

    used_vertices = sorted({index for face in faces for index in face.vertex_indices})
    used_textures = sorted(
        {index for face in faces for index in face.texture_indices if index is not None}
    )
    used_normals = sorted(
        {index for face in faces for index in face.normal_indices if index is not None}
    )
    vertex_map = {source: output + 1 for output, source in enumerate(used_vertices)}
    texture_map = {source: output + 1 for output, source in enumerate(used_textures)}
    normal_map = {source: output + 1 for output, source in enumerate(used_normals)}

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as stream:
        for comment in comments:
            stream.write(f"# {comment}\n")
        for index in used_vertices:
            values = " ".join(_format_number(value) for value in document.vertices[index])
            stream.write(f"v {values}\n")
        for index in used_textures:
            values = " ".join(
                _format_number(value) for value in document.texture_coordinates[index]
            )
            stream.write(f"vt {values}\n")
        for index in used_normals:
            values = " ".join(_format_number(value) for value in document.normals[index])
            stream.write(f"vn {values}\n")
        stream.write(f"g {group}\n")
        for face in faces:
            corners: list[str] = []
            for vertex, texture, normal in zip(
                face.vertex_indices,
                face.texture_indices,
                face.normal_indices,
                strict=True,
            ):
                vertex_value = vertex_map[vertex]
                texture_value = texture_map[texture] if texture is not None else ""
                if normal is not None:
                    corners.append(f"{vertex_value}/{texture_value}/{normal_map[normal]}")
                elif texture is not None:
                    corners.append(f"{vertex_value}/{texture_value}")
                else:
                    corners.append(str(vertex_value))
            stream.write(f"f {' '.join(corners)}\n")
