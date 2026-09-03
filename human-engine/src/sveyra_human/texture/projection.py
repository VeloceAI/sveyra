"""Painting the person's own photographs onto the mesh.

Identity lives mostly in texture, not in geometry. Two people with the same
measurements are told apart by skin tone, hair, and the shape of a face in
pixels, so the surest way to make an avatar look like someone is to use their
own photograph rather than to invent detail.

Each view is projected onto the surface and the results are blended by how
squarely each camera faced the triangle it landed on. Nothing is hallucinated:
where no camera saw the surface, the gap is filled from neighbouring texels and
marked in the coverage mask so a caller knows it was inferred.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from sveyra_human.body.mesh_deformer import SurfaceMesh
from sveyra_human.camera.projection import VIEW_AXES, OrthographicCamera

# Surface normals pointing away from a camera by more than this contribute
# nothing: a glancing view smears pixels along the surface.
MIN_FACING = 0.15


@dataclass
class TextureSet:
    albedo: np.ndarray
    coverage: np.ndarray
    resolution: int
    contributing_views: list[str] = field(default_factory=list)

    def covered_fraction(self) -> float:
        return float(self.coverage.mean())


def _view_direction(view: str) -> np.ndarray:
    """The direction a camera looks along, in world space."""
    return {
        "front": np.array([0.0, 0.0, 1.0]),
        "back": np.array([0.0, 0.0, -1.0]),
        "side": np.array([1.0, 0.0, 0.0]),
    }[view]


def project_views_to_texture(
    mesh: SurfaceMesh,
    uv: np.ndarray,
    views: dict[str, np.ndarray],
    cameras: dict[str, OrthographicCamera],
    resolution: int = 1024,
) -> TextureSet:
    """Build an albedo atlas from the supplied photographs."""
    if uv.shape[0] != mesh.vertex_count:
        raise ValueError("one UV coordinate is required per vertex")
    if not views:
        raise ValueError("at least one view is required")

    accumulated = np.zeros((resolution, resolution, 3), dtype=np.float64)
    weight_total = np.zeros((resolution, resolution), dtype=np.float64)
    normals = mesh.normals()
    used: list[str] = []

    for view, image in views.items():
        camera = cameras.get(view)
        if camera is None:
            continue
        used.append(view)
        direction = _view_direction(view)
        # A surface facing the camera has a normal opposing its view direction.
        facing = -(normals @ direction)
        projected = camera.project(mesh.vertices)

        for tri in mesh.faces:
            weight = float(facing[tri].mean())
            if weight <= MIN_FACING:
                continue
            _accumulate_triangle(
                accumulated,
                weight_total,
                uv[tri],
                projected[tri],
                image,
                weight,
                resolution,
            )

    covered = weight_total > 0
    albedo = np.zeros_like(accumulated)
    albedo[covered] = accumulated[covered] / weight_total[covered][:, None]
    albedo = _fill_gaps(albedo, covered)
    return TextureSet(
        albedo=np.clip(albedo, 0, 255).astype(np.uint8),
        coverage=covered,
        resolution=resolution,
        contributing_views=used,
    )


def _accumulate_triangle(
    accumulated: np.ndarray,
    weight_total: np.ndarray,
    tri_uv: np.ndarray,
    tri_xy: np.ndarray,
    image: np.ndarray,
    weight: float,
    resolution: int,
) -> None:
    """Rasterise one triangle in UV space, sampling the photo per texel."""
    px = tri_uv[:, 0] * (resolution - 1)
    py = (1.0 - tri_uv[:, 1]) * (resolution - 1)

    min_x = max(int(np.floor(px.min())), 0)
    max_x = min(int(np.ceil(px.max())), resolution - 1)
    min_y = max(int(np.floor(py.min())), 0)
    max_y = min(int(np.ceil(py.max())), resolution - 1)
    if min_x > max_x or min_y > max_y:
        return

    denom = (py[1] - py[2]) * (px[0] - px[2]) + (px[2] - px[1]) * (py[0] - py[2])
    if abs(denom) < 1e-12:
        return

    xs = np.arange(min_x, max_x + 1) + 0.5
    ys = np.arange(min_y, max_y + 1) + 0.5
    gx, gy = np.meshgrid(xs, ys)

    a = ((py[1] - py[2]) * (gx - px[2]) + (px[2] - px[1]) * (gy - py[2])) / denom
    b = ((py[2] - py[0]) * (gx - px[2]) + (px[0] - px[2]) * (gy - py[2])) / denom
    c = 1.0 - a - b
    inside = (a >= 0) & (b >= 0) & (c >= 0)
    if not inside.any():
        return

    # Barycentric coordinates carry straight over to the photograph.
    sx = a * tri_xy[0, 0] + b * tri_xy[1, 0] + c * tri_xy[2, 0]
    sy = a * tri_xy[0, 1] + b * tri_xy[1, 1] + c * tri_xy[2, 1]
    sx = np.clip(sx.astype(np.int64), 0, image.shape[1] - 1)
    sy = np.clip(sy.astype(np.int64), 0, image.shape[0] - 1)

    sampled = image[sy, sx][..., :3].astype(np.float64)
    region = (slice(min_y, max_y + 1), slice(min_x, max_x + 1))
    accumulated[region] += np.where(inside[:, :, None], sampled * weight, 0.0)
    weight_total[region] += np.where(inside, weight, 0.0)


def _fill_gaps(albedo: np.ndarray, covered: np.ndarray) -> np.ndarray:
    """Grow covered texels outward into the gaps.

    Uncovered texels are surfaces no camera saw - under the arms, the inside of
    a thigh. Leaving them black would read as holes, so the nearest observed
    colour is spread into them. It is inference, and `coverage` records where.
    """
    if covered.all() or not covered.any():
        return albedo
    _, indices = ndimage.distance_transform_edt(~covered, return_indices=True)
    return albedo[indices[0], indices[1]]


def cameras_for_views(
    views: dict[str, np.ndarray], height_cm: float
) -> dict[str, OrthographicCamera]:
    return {
        view: OrthographicCamera.fit_to_height(view, height_cm, image.shape[1], image.shape[0])
        for view, image in views.items()
        if view in VIEW_AXES
    }
