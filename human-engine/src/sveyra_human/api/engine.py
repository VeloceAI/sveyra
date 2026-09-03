"""The engine facade.

Layers are assembled here and nowhere else. Each stage is also exposed on its
own so a caller can drive the pipeline step by step, and so a later
implementation can be swapped in without touching this file's callers.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

import numpy as np

from sveyra_human.api.errors import NotImplementedYetError, ReconstructionError
from sveyra_human.api.models import SUBDIVISIONS, AvatarArtifact, AvatarBuildRequest, QualityReport
from sveyra_human.body.anatomy import measurements
from sveyra_human.body.cage import BodyCage, build_cage
from sveyra_human.body.mesh_deformer import SurfaceMesh, cage_to_mesh
from sveyra_human.body.parameters import BodyParameters
from sveyra_human.skeleton.model import Skeleton, build_skeleton
from sveyra_human.vision.port import PersonSegmenter
from sveyra_human.vision.segmentation import BackgroundContrastSegmenter
from sveyra_human.vision.silhouette import silhouette_from_segmentation

if TYPE_CHECKING:
    from sveyra_human.capture.validator import CaptureReport


class SveyraHumanEngine:
    """Builds a human from numbers today, from photographs from Phase 3 on."""

    def __init__(
        self,
        quality_mode: str = "balanced",
        segmenter: PersonSegmenter | None = None,
    ) -> None:
        if quality_mode not in SUBDIVISIONS:
            raise ValueError(f"unknown quality_mode: {quality_mode}")
        self.quality_mode = quality_mode
        # Injected rather than constructed inside, so a caller can supply
        # MediaPipe or anything else without the engine knowing.
        self._segmenter = segmenter or BackgroundContrastSegmenter()
        self._timings: dict[str, float] = {}
        self._view_confidence: dict[str, float] = {}

    @contextmanager
    def _timed(self, stage: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self._timings[f"{stage}_ms"] = round((time.perf_counter() - start) * 1000.0, 3)

    # -- stages ---------------------------------------------------------

    def fit_skeleton(self, params: BodyParameters) -> Skeleton:
        with self._timed("skeleton"):
            return build_skeleton(params)

    def fit_body(self, params: BodyParameters, skeleton: Skeleton) -> BodyCage:
        with self._timed("cage"):
            return build_cage(params, skeleton.positions)

    def build_surface(self, cage: BodyCage, quality_mode: str | None = None) -> SurfaceMesh:
        mode = quality_mode or self.quality_mode
        with self._timed("mesh"):
            return cage_to_mesh(cage, subdivisions=SUBDIVISIONS[mode])

    def fit_from_silhouettes(
        self, views: dict[str, object], height_cm: float
    ) -> "BodyParameters":
        """Recover body parameters from silhouette masks.

        Takes masks rather than photographs: producing a mask from a photo is
        Phase 2, and keeping that boundary explicit means the fitting can be
        driven from synthetic data or from any segmenter.
        """
        from sveyra_human.optimization import fit_body_parameters

        with self._timed("fitting"):
            return fit_body_parameters(views, height_cm=height_cm)  # type: ignore[arg-type]

    def build_from_silhouettes(
        self, views: dict[str, object], height_cm: float, quality_mode: str | None = None
    ) -> AvatarArtifact:
        """Silhouettes to a finished avatar."""
        self._timings = {}
        params = self.fit_from_silhouettes(views, height_cm)
        # build_parametric resets the timing dict, so carry the fit across it.
        fitting_ms = self._timings.get("fitting_ms", 0.0)
        artifact = self.build_parametric(params, quality_mode)
        artifact.profiling_ms["fitting_ms"] = fitting_ms
        artifact.profiling_ms["total_ms"] = round(
            artifact.profiling_ms.get("total_ms", 0.0) + fitting_ms, 3
        )
        artifact.source_views = len(views)
        artifact.quality = QualityReport(
            overall=0.7,
            views={str(name): 0.7 for name in views},
            warnings=[
                "Body fitted from silhouettes only. Depth is constrained by the "
                "side view alone, and loose clothing is not separated from the "
                "body, so girths may read large."
            ],
        )
        return artifact

    def analyze_images(
        self, request: AvatarBuildRequest
    ) -> tuple[dict[str, object], "CaptureReport"]:
        """Photographs to silhouettes, with a report on what was usable."""
        from sveyra_human.capture.image_normalizer import load_image
        from sveyra_human.capture.validator import CaptureReport, validate_view

        report = CaptureReport()
        masks: dict[str, object] = {}
        sources = {
            "front": request.front_image,
            "side": request.side_image,
            "back": request.back_image,
        }
        with self._timed("vision"):
            for view, source in sources.items():
                if source is None:
                    continue
                image = load_image(source)
                result = self._segmenter.segment(image)
                mask = silhouette_from_segmentation(result)
                issues = validate_view(view, image, mask, result.confidence)
                report.issues.extend(issues)
                if not any(i.fatal for i in issues):
                    masks[view] = mask
                    self._view_confidence[view] = result.confidence
        return masks, report

    def fit_face(self, *_args: object, **_kwargs: object) -> None:
        raise NotImplementedYetError("Face fitting lands in Phase 4.")

    def generate_texture(self, *_args: object, **_kwargs: object) -> None:
        raise NotImplementedYetError("Projective texturing lands in Phase 5.")

    def build_hair(self, *_args: object, **_kwargs: object) -> None:
        raise NotImplementedYetError("Hair volumes land in Phase 6.")

    # -- entry points ---------------------------------------------------

    def build_parametric(
        self, params: BodyParameters, quality_mode: str | None = None
    ) -> AvatarArtifact:
        """Numbers to avatar. No photographs involved."""
        self._timings = {}
        started = time.perf_counter()

        skeleton = self.fit_skeleton(params)
        cage = self.fit_body(params, skeleton)
        mesh = self.build_surface(cage, quality_mode)

        with self._timed("measurements"):
            derived = measurements(params)

        self._timings["total_ms"] = round((time.perf_counter() - started) * 1000.0, 3)

        return AvatarArtifact(
            body_parameters=params,
            measurements=derived,
            skeleton=skeleton.to_dict(),
            quality=QualityReport(
                overall=1.0,
                views={},
                warnings=[
                    "Built from parameters only. No photograph informed this body, "
                    "so it is a proportional model of the given measurements, not a "
                    "reconstruction of a specific person."
                ],
            ),
            profiling_ms=dict(self._timings),
            source_views=0,
            _mesh=mesh,
        )

    def build(
        self,
        front: object = None,
        side: object = None,
        back: object = None,
        face: object = None,
        height_cm: float | None = None,
        **extra: object,
    ) -> AvatarArtifact:
        """Photographs to an avatar.

        Refuses rather than guessing: without a usable front view there is
        nothing to fit, and a caller who supplied photographs must not receive a
        neutral body that ignored them.
        """
        if height_cm is None:
            raise ValueError("height_cm is required: it is what sets the scale")

        request = AvatarBuildRequest(
            height_cm=height_cm,
            front_image=front,
            side_image=side,
            back_image=back,
            face_image=face,
            quality_mode=str(extra.get("quality_mode", self.quality_mode)),
        )
        self._timings = {}
        self._view_confidence = {}

        masks, report = self.analyze_images(request)
        if "front" not in masks:
            raise ReconstructionError(
                "no usable front view. " + "; ".join(report.errors() or ["segmentation failed"])
            )

        vision_ms = self._timings.get("vision_ms", 0.0)
        params = self.fit_from_silhouettes(masks, height_cm)
        fitting_ms = self._timings.get("fitting_ms", 0.0)

        artifact = self.build_parametric(params, request.quality_mode)
        artifact.profiling_ms["vision_ms"] = vision_ms
        artifact.profiling_ms["fitting_ms"] = fitting_ms
        artifact.profiling_ms["total_ms"] = round(
            artifact.profiling_ms.get("total_ms", 0.0) + vision_ms + fitting_ms, 3
        )
        artifact.source_views = len(masks)
        artifact.quality = self._photo_quality(masks, report)
        return artifact

    def _photo_quality(self, masks: dict[str, object], report: "CaptureReport") -> QualityReport:
        views = {v: round(self._view_confidence.get(v, 0.5), 4) for v in masks}
        warnings = list(report.warnings())
        warnings.append(
            "Body fitted from silhouettes. Clothing is not separated from the "
            "body, so loose garments read as a larger waist."
        )
        if "side" not in masks:
            warnings.append(
                "No usable side view, so depth is inferred from proportion "
                "rather than measured."
            )
        overall = float(np.mean(list(views.values()))) if views else 0.0
        return QualityReport(overall=round(overall * 0.85, 4), views=views, warnings=warnings)
