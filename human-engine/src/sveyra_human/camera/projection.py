"""Projecting 3D points into a view, and rasterising a silhouette.

Phase 3 fits a body by comparing the avatar's projected outline against the
outline in a photograph, so both halves of that comparison live here.

V1 is orthographic. Real photographs have perspective, and
`camera/calibration.py` will estimate it from the known height plus the head and
foot positions. Orthographic is a deliberate first approximation: it is exact
for a distant camera, it is trivially invertible, and it lets the fitting maths
be validated before lens estimation is in the way.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

VIEW_AXES: dict[str, tuple[int, int]] = {
    # view -> (horizontal source axis, vertical source axis)
    "front": (0, 1),  # X across, Y up
    "back": (0, 1),
    "side": (2, 1),  # Z across, Y up
}


@dataclass(frozen=True)
class OrthographicCamera:
    """Maps world centimetres onto pixels for one view.

    `pixels_per_cm` and `origin_px` are what a Phase 2 calibration will solve
    for from a person's known height.
    """

    view: str
    width: int
    height: int
    pixels_per_cm: float
    origin_px: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        if self.view not in VIEW_AXES:
            raise ValueError(f"unknown view: {self.view}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("camera resolution must be positive")
        if self.pixels_per_cm <= 0:
            raise ValueError("pixels_per_cm must be positive")

    def project(self, points: np.ndarray) -> np.ndarray:
        """World points (n, 3) in cm to pixel coordinates (n, 2).

        Pixel Y grows downward, which is how images are stored, so the world Y
        axis is flipped exactly once - here.
        """
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError("points must have shape (n, 3)")
        h_axis, v_axis = VIEW_AXES[self.view]
        horizontal = points[:, h_axis]
        if self.view == "back":
            horizontal = -horizontal  # seen from behind, left and right swap
        x = horizontal * self.pixels_per_cm + self.origin_px[0] + self.width / 2.0
        y = self.height - (points[:, v_axis] * self.pixels_per_cm + self.origin_px[1])
        return np.stack([x, y], axis=1)

    @classmethod
    def fit_to_height(
        cls, view: str, person_height_cm: float, width: int, height: int, margin: float = 0.08
    ) -> OrthographicCamera:
        """Frame a standing person of known height, with a margin above and below."""
        if person_height_cm <= 0:
            raise ValueError("person_height_cm must be positive")
        usable = height * (1.0 - 2.0 * margin)
        return cls(
            view=view,
            width=width,
            height=height,
            pixels_per_cm=usable / person_height_cm,
            origin_px=(0.0, height * margin),
        )


def rasterise_silhouette(
    vertices: np.ndarray, faces: np.ndarray, camera: OrthographicCamera
) -> np.ndarray:
    """Fill every projected triangle into a boolean mask.

    A scanline fill over triangle bounding boxes using barycentric coverage.
    Deterministic, dependency-free and fast enough on CPU for fitting, where the
    mask is recomputed many times per solve.
    """
    projected = camera.project(vertices)
    mask = np.zeros((camera.height, camera.width), dtype=bool)

    tris = projected[faces]
    for tri in tris:
        min_x = max(int(np.floor(tri[:, 0].min())), 0)
        max_x = min(int(np.ceil(tri[:, 0].max())), camera.width - 1)
        min_y = max(int(np.floor(tri[:, 1].min())), 0)
        max_y = min(int(np.ceil(tri[:, 1].max())), camera.height - 1)
        if min_x > max_x or min_y > max_y:
            continue

        (x0, y0), (x1, y1), (x2, y2) = tri
        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denom) < 1e-12:
            continue  # degenerate after projection

        xs = np.arange(min_x, max_x + 1) + 0.5
        ys = np.arange(min_y, max_y + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)

        a = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / denom
        b = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / denom
        c = 1.0 - a - b
        inside = (a >= 0) & (b >= 0) & (c >= 0)
        if inside.any():
            mask[min_y : max_y + 1, min_x : max_x + 1] |= inside
    return mask


def mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    """Intersection over union of two boolean masks."""
    if a.shape != b.shape:
        raise ValueError("masks must have the same shape")
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 1.0
    return float(np.logical_and(a, b).sum() / union)


def mask_width_profile(mask: np.ndarray) -> np.ndarray:
    """Filled pixel count per image row."""
    return mask.sum(axis=1).astype(np.float64)


def mask_extent_profile(mask: np.ndarray) -> np.ndarray:
    """Outer width per image row: rightmost filled pixel minus leftmost.

    This is what a silhouette actually measures - how wide the body is at each
    height - and unlike a filled count it ignores holes, so the gap between the
    legs does not read as a narrower body.
    """
    any_filled = mask.any(axis=1)
    idx = np.arange(mask.shape[1])
    # Sentinels rather than NaN: empty rows are ordinary here, not an error, and
    # nanmin on an all-empty row warns.
    left = np.where(mask, idx[None, :], mask.shape[1]).min(axis=1)
    right = np.where(mask, idx[None, :], -1).max(axis=1)
    return np.where(any_filled, right - left + 1.0, 0.0).astype(np.float64)


def projected_extent_profile(
    vertices: np.ndarray,
    faces: np.ndarray,
    camera: OrthographicCamera,
    bands: int,
    samples_per_band: int = 3,
) -> np.ndarray:
    """Body width per height band, in centimetres, without rasterising.

    The fitting loop evaluates this on every objective call, so it must be cheap.
    It measures where the surface *crosses* each band height, by interpolating
    along the mesh edges that straddle it. Binning vertices instead is faster
    still but wrong: mesh rings sit at discrete heights, so bands between rings
    come back empty and the widest point between two rings is missed entirely.

    Each band is sampled at several heights and the widest is kept. A single
    centre sample makes the profile jump wherever a thin feature like an
    outstretched arm falls between samples, which turns a smooth residual into a
    step and stalls the optimiser.

    Bands run bottom to top across the projected body.
    """
    if bands < 2:
        raise ValueError("bands must be at least 2")
    if samples_per_band < 1:
        raise ValueError("samples_per_band must be at least 1")
    projected = camera.project(vertices)
    x, y = projected[:, 0], projected[:, 1]

    top, bottom = y.min(), y.max()
    if bottom - top < 1e-9:
        return np.zeros(bands)

    edges = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    y0, y1 = y[edges[:, 0]], y[edges[:, 1]]
    x0, x1 = x[edges[:, 0]], x[edges[:, 1]]
    dy = y1 - y0

    widths = np.zeros(bands)
    # Image Y grows downward, so band 0 (the feet) sits at the largest row value.
    offsets = (np.arange(samples_per_band) + 0.5) / samples_per_band
    for b in range(bands):
        widest = 0.0
        for offset in offsets:
            yc = bottom - (b + offset) / bands * (bottom - top)
            straddles = (y0 <= yc) != (y1 <= yc)
            if not straddles.any():
                continue
            sdy = dy[straddles]
            safe = np.where(np.abs(sdy) < 1e-12, 1e-12, sdy)
            t = (yc - y0[straddles]) / safe
            crossings = x0[straddles] + t * (x1[straddles] - x0[straddles])
            widest = max(widest, float(crossings.max() - crossings.min()))
        widths[b] = widest
    return widths / camera.pixels_per_cm
