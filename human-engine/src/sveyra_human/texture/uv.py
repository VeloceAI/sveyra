"""UV coordinates.

The mesh is a stack of rings per body part, which is the easy case for
unwrapping: a ring stack is a cylinder, and a cylinder unrolls to a rectangle
with no distortion beyond the taper. Each part gets its own horizontal strip of
the atlas, so parts never bleed into one another.

The seam is the price, and it is not solved here. Rings are unwrapped with
`endpoint=False`, so the last column sits near u=0.94 and its wrap triangle
spans backwards across the whole strip. Texels past that column are never
painted directly and get filled from their neighbours instead.

Fixing it properly means duplicating the seam column with u=1.0, which changes
vertex count and so ripples into skin weights and the cage-to-mesh mapping.
Deferred deliberately rather than half-done; the gap fill hides it at the
resolutions used today. See docs/STATUS.md.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.body.cage import BodyCage


def build_uv_layout(cage: BodyCage, padding: float = 0.01) -> dict[str, tuple[float, float]]:
    """Assign each cage part a vertical slice of the atlas, sized by its area.

    Returns part name to (v_start, v_end). Parts are given room in proportion to
    their ring count, so a torso is not squeezed into the same strip as a foot.
    """
    if not cage.parts:
        raise ValueError("cage has no parts")
    weights = np.array([float(p.levels * p.segments) for p in cage.parts])
    fractions = weights / weights.sum()

    layout: dict[str, tuple[float, float]] = {}
    cursor = 0.0
    for part, fraction in zip(cage.parts, fractions, strict=True):
        height = max(fraction - padding, fraction * 0.5)
        layout[part.name] = (cursor, cursor + height)
        cursor += fraction
    return layout


def unwrap_cage(cage: BodyCage) -> np.ndarray:
    """UV per cage vertex, in the same order `cage_to_mesh` emits them.

    Rings run left to right across u; levels run bottom to top within the part's
    strip. Cap vertices, which have no ring position, land at the strip centre.
    """
    layout = build_uv_layout(cage)
    coords: list[np.ndarray] = []

    for part in cage.parts:
        v0, v1 = layout[part.name]
        levels, segments = part.levels, part.segments
        u = np.linspace(0.0, 1.0, segments, endpoint=False)
        v = np.linspace(v0, v1, levels)
        grid_u, grid_v = np.meshgrid(u, v)
        coords.append(np.stack([grid_u.ravel(), grid_v.ravel()], axis=1))

        centre = np.array([[0.5, (v0 + v1) / 2.0]])
        for closed in (part.closed_bottom, part.closed_top):
            if closed:
                coords.append(centre.copy())

    return np.vstack(coords).astype(np.float32)


def subdivide_uv(uv: np.ndarray, faces_before: np.ndarray) -> np.ndarray:
    """Carry UVs through one midpoint subdivision, matching `subdivide`.

    Must walk the faces in the same order the geometry did, or UVs and vertices
    stop corresponding.
    """
    coords = [row for row in uv]
    midpoint: dict[tuple[int, int], int] = {}

    def mid(a: int, b: int) -> int:
        key = (a, b) if a < b else (b, a)
        found = midpoint.get(key)
        if found is None:
            found = len(coords)
            coords.append((uv[a] + uv[b]) / 2.0)
            midpoint[key] = found
        return found

    for tri in faces_before:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        mid(a, b)
        mid(b, c)
        mid(c, a)

    return np.array(coords, dtype=np.float32)
