from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import (
    MediaDeletionIncompleteError,
    UserNotFoundError,
    WardrobeItemNotFoundError,
)
from app.models.wardrobe_item import WardrobeItem
from app.repositories.media_asset_repository import MediaAssetRepository
from app.repositories.wardrobe_repository import WardrobeRepository
from app.schemas.wardrobe_schema import (
    WardrobeItemCreateRequest,
    WardrobeItemListResponse,
    WardrobeItemResponse,
    WardrobeItemUpdateRequest,
)
from app.services.media_asset_service import MediaAssetService
from app.storage.port import StoragePort


class WardrobeService:
    def __init__(
        self,
        repository: WardrobeRepository | None = None,
        media_repository: MediaAssetRepository | None = None,
        storage: StoragePort | None = None,
    ) -> None:
        self.repository = repository or WardrobeRepository()
        self.media_repository = media_repository or MediaAssetRepository()
        self.storage = storage

    def create_item(
        self, session: Session, user_id: UUID, payload: WardrobeItemCreateRequest
    ) -> WardrobeItemResponse:
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError
        item = self.repository.create_item(
            session,
            user_id,
            payload.category,
            payload.color,
            payload.brand,
            payload.attributes,
        )
        session.commit()
        session.refresh(item)
        return self._to_response(item)

    def get_item(self, session: Session, item_id: UUID, user_id: UUID) -> WardrobeItemResponse:
        item = self.repository.get_item_by_id(session, item_id)
        if item is None or item.user_id != user_id:
            raise WardrobeItemNotFoundError
        return self._to_response(item)

    def list_items(
        self, session: Session, user_id: UUID, *, limit: int, offset: int
    ) -> WardrobeItemListResponse:
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError
        items, total = self.repository.list_items_by_user_id(
            session, user_id, limit=limit, offset=offset
        )
        return WardrobeItemListResponse(
            wardrobe_items=[self._to_response(item) for item in items],
            limit=limit,
            offset=offset,
            total=total,
        )

    def update_item(
        self,
        session: Session,
        item_id: UUID,
        user_id: UUID,
        payload: WardrobeItemUpdateRequest,
    ) -> WardrobeItemResponse:
        item = self.repository.get_item_by_id(session, item_id)
        if item is None or item.user_id != user_id:
            raise WardrobeItemNotFoundError
        updated = self.repository.update_item_fields(
            session,
            item,
            category=payload.category,
            color=payload.color,
            brand=payload.brand,
            attributes=payload.attributes,
        )
        session.commit()
        session.refresh(updated)
        return self._to_response(updated)

    def delete_item(self, session: Session, item_id: UUID, user_id: UUID) -> None:
        if self.storage is None:
            raise RuntimeError("StoragePort is required to delete linked media.")
        item = self.repository.get_item_by_id(session, item_id)
        if item is None or item.user_id != user_id:
            raise WardrobeItemNotFoundError

        # Cascade linked media with M14 semantics (storage first, then metadata).
        media_service = MediaAssetService(
            repository=self.media_repository,
            storage=self.storage,
        )
        linked = self.media_repository.list_assets_by_wardrobe_item_id(session, item.id)
        for asset in linked:
            if asset.user_id != user_id:
                continue
            media_service.delete_asset(session, asset.id, user_id)

        self.repository.delete_item(session, item)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise MediaDeletionIncompleteError

    def _to_response(self, item: WardrobeItem) -> WardrobeItemResponse:
        return WardrobeItemResponse(
            id=item.id,
            user_id=item.user_id,
            category=item.category,
            color=item.color,
            brand=item.brand,
            attributes=item.attributes,
        )
