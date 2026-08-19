from app.vision.errors import VisionUnavailableError
from app.vision.port import GarmentAnalysis, VisionPort

# Apply category/color column updates only at or above this confidence.
CATEGORY_COLOR_MIN_CONFIDENCE = 0.75


class StubVision(VisionPort):
    """Deterministic test/local vision adapter. Not a production CV provider."""

    def __init__(self, analysis: GarmentAnalysis | None = None) -> None:
        self._analysis = analysis

    def analyze_garment(self, image: bytes) -> GarmentAnalysis:
        if not image:
            raise VisionUnavailableError
        if self._analysis is not None:
            return self._analysis
        # Default high-confidence stub derived only from byte length (deterministic).
        palette = ("navy", "black", "white", "beige", "gray")
        categories = ("shirt", "trousers", "shoes", "jacket", "skirt")
        return GarmentAnalysis(
            category=categories[len(image) % len(categories)],
            color=palette[len(image) % len(palette)],
            pattern="solid",
            material="unknown",
            silhouette="regular",
            occasion_tags=["casual"],
            category_confidence=0.9,
            color_confidence=0.9,
        )
