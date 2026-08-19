from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import WardrobeItemNotFoundError, WardrobeMediaMissingError
from app.repositories.media_asset_repository import MediaAssetRepository
from app.repositories.wardrobe_repository import WardrobeRepository
from app.schemas.wardrobe_schema import WardrobeItemResponse
from app.storage.errors import StorageObjectNotFoundError, StorageUnavailableError
from app.storage.port import StoragePort
from app.vision.errors import VisionUnavailableError
from app.vision.port import GarmentAnalysis, VisionPort
from app.vision.stub import CATEGORY_COLOR_MIN_CONFIDENCE


def _looks_like_url_or_bytes_ref(value: object) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("gs://")
        or lowered.startswith("memory://")
        or "://" in lowered
    )


def _safe_secondary(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or _looks_like_url_or_bytes_ref(cleaned):
        return None
    return cleaned[:100]


def apply_garment_analysis(
    *,
    current_category: str,
    current_color: str,
    current_attributes: dict[str, object],
    analysis: GarmentAnalysis,
) -> tuple[str, str, dict[str, object]]:
    """Merge vision output into wardrobe metadata using confidence policy."""
    category = current_category
    color = current_color
    attributes = dict(current_attributes or {})

    applied_category = False
    applied_color = False
    if (
        analysis.category
        and analysis.category_confidence >= CATEGORY_COLOR_MIN_CONFIDENCE
        and not _looks_like_url_or_bytes_ref(analysis.category)
    ):
        category = analysis.category.strip()[:100]
        applied_category = True
    if (
        analysis.color
        and analysis.color_confidence >= CATEGORY_COLOR_MIN_CONFIDENCE
        and not _looks_like_url_or_bytes_ref(analysis.color)
    ):
        color = analysis.color.strip()[:100]
        applied_color = True

    secondary: dict[str, object] = {}
    pattern = _safe_secondary(analysis.pattern)
    material = _safe_secondary(analysis.material)
    silhouette = _safe_secondary(analysis.silhouette)
    if pattern:
        secondary["pattern"] = pattern
    if material:
        secondary["material"] = material
    if silhouette:
        secondary["silhouette"] = silhouette
    tags = [
        tag.strip()[:100]
        for tag in analysis.occasion_tags
        if isinstance(tag, str) and tag.strip() and not _looks_like_url_or_bytes_ref(tag)
    ]
    if tags:
        secondary["occasion_tags"] = tags

    attributes["cv"] = {
        "suggested_category": _safe_secondary(analysis.category),
        "suggested_color": _safe_secondary(analysis.color),
        "category_confidence": analysis.category_confidence,
        "color_confidence": analysis.color_confidence,
        "applied_category": applied_category,
        "applied_color": applied_color,
        **secondary,
    }
    return category, color, attributes


class GarmentEnrichmentService:
    def __init__(
        self,
        wardrobe_repository: WardrobeRepository | None = None,
        media_repository: MediaAssetRepository | None = None,
        storage: StoragePort | None = None,
        vision: VisionPort | None = None,
    ) -> None:
        self.wardrobe_repository = wardrobe_repository or WardrobeRepository()
        self.media_repository = media_repository or MediaAssetRepository()
        self.storage = storage
        self.vision = vision

    def enrich_item(
        self, session: Session, user_id: UUID, item_id: UUID
    ) -> WardrobeItemResponse:
        if self.storage is None or self.vision is None:
            raise RuntimeError("StoragePort and VisionPort are required for enrichment.")

        item = self.wardrobe_repository.get_item_by_id(session, item_id)
        if item is None or item.user_id != user_id:
            raise WardrobeItemNotFoundError

        asset = self.media_repository.get_asset_by_wardrobe_item_id(session, item.id)
        if asset is None or asset.user_id != user_id:
            raise WardrobeMediaMissingError

        try:
            image = self.storage.get(asset.reference)
        except StorageObjectNotFoundError:
            raise WardrobeMediaMissingError
        except StorageUnavailableError:
            raise

        try:
            analysis = self.vision.analyze_garment(image)
        except VisionUnavailableError:
            raise
        except Exception:
            raise VisionUnavailableError

        category, color, attributes = apply_garment_analysis(
            current_category=item.category,
            current_color=item.color,
            current_attributes=dict(item.attributes or {}),
            analysis=analysis,
        )
        updated = self.wardrobe_repository.update_item_metadata(
            session,
            item,
            category=category,
            color=color,
            attributes=attributes,
        )
        session.commit()
        session.refresh(updated)
        return WardrobeItemResponse(
            id=updated.id,
            user_id=updated.user_id,
            category=updated.category,
            color=updated.color,
            brand=updated.brand,
            attributes=updated.attributes,
        )
