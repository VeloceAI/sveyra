"""Solving for a body from silhouettes.

Front silhouettes constrain width, side silhouettes constrain depth. The solver
moves a handful of named parameters, rebuilds the body through the ordinary
forward model, and compares the projected width profile against the observed
one. It never touches a mesh vertex directly.

Two stages, because a good starting point is worth more than a clever solver:
the widths are first read straight off the observed profiles at the landmark
heights, then refined with least squares under the priors.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

from sveyra_human.api.errors import ReconstructionError
from sveyra_human.body.cage import build_cage
from sveyra_human.body.mesh_deformer import cage_to_mesh
from sveyra_human.body.parameters import BodyParameters, landmark_levels
from sveyra_human.camera.projection import OrthographicCamera
from sveyra_human.optimization.objective import ObjectiveTerm, default_terms, prior_residuals
from sveyra_human.optimization.silhouette_loss import (
    mask_to_band_profile,
    model_profile,
    torso_band_slice,
)
from sveyra_human.skeleton.model import build_skeleton

# Solved from the silhouettes. Everything else follows from height, because
# nothing in a front or side view constrains it.
SOLVED_FIELDS = (
    "chest_width",
    "chest_depth",
    "waist_width",
    "waist_depth",
    "hip_width",
    "hip_depth",
)

# 64 rather than 40: bands take the widest row they contain, so a narrow waist
# borrows the wider chest or hip beside it and reads too broad. Finer bands cut
# that smearing; below ~56 the waist is over-estimated by around 10 percent.
DEFAULT_BANDS = 64

# Multiples of the neutral value. Wide enough for real human variation, tight
# enough that the solver cannot wander into nonsense.
BOUND_SCALE = (0.45, 2.2)


@dataclass
class FitResult:
    parameters: BodyParameters
    residual_cm: float
    iterations: int
    converged: bool
    per_view_residual_cm: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "residual_cm": round(self.residual_cm, 4),
            "iterations": self.iterations,
            "converged": self.converged,
            "per_view_residual_cm": {
                k: round(v, 4) for k, v in self.per_view_residual_cm.items()
            },
        }


def _build_mesh(params: BodyParameters):
    skeleton = build_skeleton(params)
    return cage_to_mesh(build_cage(params, skeleton.positions), subdivisions=0)


def _initial_guess(
    targets: dict[str, np.ndarray], height_cm: float, bands: int
) -> BodyParameters:
    """Read widths and depths straight off the observed profiles.

    An analytic starting point costs one profile lookup and saves the solver
    most of its iterations.
    """
    levels = landmark_levels()
    guess: dict[str, float] = {}
    for landmark, width_field, depth_field in (
        ("hip", "hip_width", "hip_depth"),
        ("waist", "waist_width", "waist_depth"),
        ("chest", "chest_width", "chest_depth"),
    ):
        band = int(np.clip(levels[landmark] * bands, 0, bands - 1))
        for view, field_name in (("front", width_field), ("side", depth_field)):
            profile = targets.get(view)
            if profile is None:
                continue
            observed = float(profile[band])
            if observed > 1.0:
                guess[field_name] = observed
    return BodyParameters(height=height_cm, **guess)


def fit_body_parameters(
    views: dict[str, np.ndarray],
    height_cm: float,
    *,
    bands: int = DEFAULT_BANDS,
    terms: list[ObjectiveTerm] | None = None,
    max_iterations: int = 60,
    return_details: bool = False,
) -> BodyParameters | FitResult:
    """Recover body parameters from silhouette masks.

    `views` maps "front" / "side" / "back" to boolean masks. Front and side
    carry the information; a back view is accepted and used alongside the front.
    """
    if height_cm <= 0:
        raise ValueError("height_cm must be positive")
    usable = {k: v for k, v in views.items() if k in ("front", "side", "back") and v is not None}
    if "front" not in usable:
        raise ReconstructionError("a front view is required to fit a body")

    cameras = {
        view: OrthographicCamera.fit_to_height(view, height_cm, mask.shape[1], mask.shape[0])
        for view, mask in usable.items()
    }
    targets = {
        view: mask_to_band_profile(mask, cameras[view], bands) for view, mask in usable.items()
    }
    band_slice = torso_band_slice(bands)
    active_terms = default_terms() if terms is None else terms

    start = _initial_guess(targets, height_cm, bands)
    neutral = BodyParameters(height=height_cm)
    x0 = np.array([float(getattr(start, f)) for f in SOLVED_FIELDS])
    reference = np.array([float(getattr(neutral, f)) for f in SOLVED_FIELDS])
    lower = reference * BOUND_SCALE[0]
    upper = reference * BOUND_SCALE[1]
    x0 = np.clip(x0, lower + 1e-6, upper - 1e-6)

    def candidate(x: np.ndarray) -> BodyParameters:
        return BodyParameters(
            height=height_cm, **{f: float(v) for f, v in zip(SOLVED_FIELDS, x, strict=True)}
        )

    def residuals(x: np.ndarray) -> np.ndarray:
        params = candidate(x)
        mesh = _build_mesh(params)
        parts = [
            model_profile(mesh.vertices, mesh.faces, cameras[view], bands)[band_slice]
            - targets[view][band_slice]
            for view in usable
        ]
        return np.concatenate(parts + [prior_residuals(params, active_terms)])

    solution = least_squares(
        residuals,
        x0,
        bounds=(lower, upper),
        max_nfev=max_iterations * (len(SOLVED_FIELDS) + 1),
        xtol=1e-8,
        ftol=1e-8,
    )

    fitted = candidate(solution.x)
    if not return_details:
        return fitted

    mesh = _build_mesh(fitted)
    per_view = {
        view: float(
            np.abs(
                model_profile(mesh.vertices, mesh.faces, cameras[view], bands)[band_slice]
                - targets[view][band_slice]
            ).mean()
        )
        for view in usable
    }
    silhouette_only = np.concatenate(
        [
            model_profile(mesh.vertices, mesh.faces, cameras[view], bands)[band_slice]
            - targets[view][band_slice]
            for view in usable
        ]
    )
    return FitResult(
        parameters=fitted,
        residual_cm=float(np.abs(silhouette_only).mean()),
        iterations=int(solution.nfev),
        converged=bool(solution.success),
        per_view_residual_cm=per_view,
    )
