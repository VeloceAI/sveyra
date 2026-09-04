"""The real 3D avatar backend, behind the existing AvatarPort.

Wraps the SVEYRA Human Engine. Photographs and a height go in; a GLB lands in
StoragePort and its reference comes back. The engine itself knows nothing about
this app, storage or HTTP, which is why it can also be driven from a CLI or a
test.
"""

from __future__ import annotations

from app.avatar.errors import AvatarUnavailableError
from app.avatar.port import AvatarPort, AvatarRequest, AvatarResult
from app.storage.port import StoragePort

# Photographs below this are not worth fitting; the engine will refuse anyway,
# but failing here gives a clearer message.
MIN_VIEWS = 1


class SveyraEngineAvatar(AvatarPort):
    """3D avatar reconstruction using the local human engine."""

    def __init__(self, storage: StoragePort, quality_mode: str = "balanced") -> None:
        self._storage = storage
        self._quality = quality_mode

    def render(self, request: AvatarRequest) -> AvatarResult:
        """Parameters-only render, for callers with measurements but no photos."""
        height = _height_from(request.measurements)
        if height is None:
            raise AvatarUnavailableError

        engine, BodyParameters = _load()
        artifact = engine(self._quality).build_parametric(
            BodyParameters(**_body_kwargs(request.measurements, height))
        )
        return AvatarResult(backend="sveyra-3d", mesh_reference=self._store(artifact))

    def build_from_photos(
        self,
        photos: dict[str, bytes],
        height_cm: float,
        measurements: dict[str, object] | None = None,
    ) -> tuple[AvatarResult, dict[str, object]]:
        """Photographs to a stored GLB, plus the report the caller should show."""
        if len(photos) < MIN_VIEWS or "front" not in photos:
            raise AvatarUnavailableError

        engine, _ = _load()
        instance = engine(self._quality)
        try:
            artifact = instance.build(
                front=photos.get("front"),
                side=photos.get("side"),
                back=photos.get("back"),
                height_cm=height_cm,
            )
        except Exception as exc:
            # The engine refuses input it cannot honestly reconstruct. Translate
            # that here rather than letting an engine exception type reach the
            # API layer, which must stay importable without the engine.
            if type(exc).__name__ in {"ReconstructionError", "SveyraHumanError"}:
                raise AvatarUnavailableError(str(exc)) from exc
            raise
        result = AvatarResult(backend="sveyra-3d", mesh_reference=self._store(artifact))
        return result, {
            "measurements": artifact.measurements,
            "body_parameters": artifact.body_parameters.to_dict(),
            "confidence": artifact.quality.to_dict(),
            "profiling_ms": artifact.profiling_ms,
            "source_views": artifact.source_views,
        }

    def check_photos(self, photos: dict[str, bytes]) -> dict[str, object]:
        """Judge photographs without building anything.

        Separate from build_from_photos because a person adjusting their framing
        should not pay for a reconstruction on every attempt.
        """
        from sveyra_human.capture import guide_capture, load_image, overall_guidance
        from sveyra_human.vision import BackgroundContrastSegmenter, silhouette_from_segmentation

        segmenter = BackgroundContrastSegmenter()
        results = {}
        for view, payload in photos.items():
            image = load_image(payload)
            segmented = segmenter.segment(image)
            mask = silhouette_from_segmentation(segmented)
            results[view] = guide_capture(view, image, mask, segmented.confidence)

        return {
            "views": {view: g.to_dict() for view, g in results.items()},
            "overall": overall_guidance(results),
            "ready": all(g.usable for g in results.values()) and "front" in results,
        }

    def _store(self, artifact: object) -> str:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "avatar.glb"
            artifact.export(target)  # type: ignore[attr-defined]
            return self._storage.put(target.read_bytes())


def _load():
    """Import the engine lazily.

    Keeps the backend importable, and the rest of the API working, on a machine
    where the engine is not installed.
    """
    try:
        from sveyra_human import BodyParameters, SveyraHumanEngine
    except ImportError as exc:  # pragma: no cover - depends on the install
        raise AvatarUnavailableError(
            "The SVEYRA Human Engine is not installed. Install it with "
            "pip install -e ../human-engine, or set AVATAR_BACKEND=stub."
        ) from exc
    return SveyraHumanEngine, BodyParameters


def _height_from(measurements: dict[str, object]) -> float | None:
    value = measurements.get("height_cm") or measurements.get("height")
    try:
        height = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return height if height > 0 else None


# Measurement keys the body profile stores, mapped to engine parameter names.
_FIELD_MAP = {
    "chest_cm": "chest_width",
    "waist_cm": "waist_width",
    "hip_cm": "hip_width",
}


def _body_kwargs(measurements: dict[str, object], height: float) -> dict[str, float]:
    kwargs: dict[str, float] = {"height": height}
    for source, target in _FIELD_MAP.items():
        raw = measurements.get(source)
        if isinstance(raw, (int, float)) and raw > 0:
            # Stored measurements are girths; the engine takes widths, and a
            # superellipse girth is roughly three times its width.
            kwargs[target] = float(raw) / 3.0
    return kwargs
