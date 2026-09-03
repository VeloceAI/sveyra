from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.media_asset import MediaAsset
from app.models.user import User
from app.models.wardrobe_item import WardrobeItem


class MediaAssetRepository:
    def get_user_by_id(self, session: Session, user_id: UUID) -> User | None:
        return session.get(User, user_id)

    def get_wardrobe_item_by_id(self, session: Session, item_id: UUID) -> WardrobeItem | None:
        return session.get(WardrobeItem, item_id)

    def create_asset(
        self,
        session: Session,
        user_id: UUID,
        reference: str,
        wardrobe_item_id: UUID | None,
    ) -> MediaAsset:
        asset = MediaAsset(
            id=uuid4(),
            user_id=user_id,
            reference=reference,
            wardrobe_item_id=wardrobe_item_id,
        )
        session.add(asset)
        return asset

    def get_asset_by_reference(self, session: Session, reference: str) -> MediaAsset | None:
        return session.scalars(
            select(MediaAsset).where(MediaAsset.reference == reference)
        ).first()

    def get_asset_by_id(self, session: Session, asset_id: UUID) -> MediaAsset | None:
        return session.get(MediaAsset, asset_id)

    def get_asset_by_wardrobe_item_id(
        self, session: Session, wardrobe_item_id: UUID
    ) -> MediaAsset | None:
        return session.scalars(
            select(MediaAsset).where(MediaAsset.wardrobe_item_id == wardrobe_item_id)
        ).first()

    def list_assets_by_wardrobe_item_id(
        self, session: Session, wardrobe_item_id: UUID
    ) -> list[MediaAsset]:
        return list(
            session.scalars(
                select(MediaAsset).where(MediaAsset.wardrobe_item_id == wardrobe_item_id)
            ).all()
        )

    def delete_asset(self, session: Session, asset: MediaAsset) -> None:
        session.delete(asset)
