from dataclasses import dataclass, field


@dataclass(frozen=True)
class GarmentAnalysis:
    category: str | None = None
    color: str | None = None
    pattern: str | None = None
    material: str | None = None
    silhouette: str | None = None
    occasion_tags: list[str] = field(default_factory=list)
    category_confidence: float = 0.0
    color_confidence: float = 0.0


class VisionPort:
    def analyze_garment(self, image: bytes) -> GarmentAnalysis:
        """Inspect garment image bytes and return structured analysis."""
        raise NotImplementedError
