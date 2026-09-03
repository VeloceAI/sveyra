from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    EmptyMediaUploadError,
    MediaAssetNotFoundError,
    MediaDeletionIncompleteError,
    MediaReferenceAlreadyClaimedError,
    UserNotFoundError,
    WardrobeItemNotFoundError,
)
from app.models.media_asset import MediaAsset
from app.repositories.media_asset_repository import MediaAssetRepository
from app.schemas.media_asset_schema import (
    MediaAssetAccessResponse,
    MediaAssetCreateRequest,
    MediaAssetResponse,
)
from app.storage.errors import StorageObjectNotFoundError, StorageUnavailableError
from app.storage.port import StoragePort


class MediaAssetService:
    def __init__(
        self,
        repository: MediaAssetRepository | None = None,
        storage: StoragePort | None = None,
    ) -> None:
        self.repository = repository or MediaAssetRepository()
        self.storage = storage

    def create_asset(
        self, session: Session, user_id: UUID, payload: MediaAssetCreateRequest
    ) -> MediaAssetResponse:
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError
        if payload.wardrobe_item_id is not None:
            item = self.repository.get_wardrobe_item_by_id(session, payload.wardrobe_item_id)
            if item is None or item.user_id != user_id:
                raise WardrobeItemNotFoundError
        # Without this a caller could register someone else's storage reference and
        # then read or delete the bytes behind it through their own asset row.
        if self.repository.get_asset_by_reference(session, payload.reference) is not None:
            raise MediaReferenceAlreadyClaimedError
        asset = self.repository.create_asset(
            session,
            user_id,
            payload.reference,
            payload.wardrobe_item_id,
        )
        session.commit()
        session.refresh(asset)
        return self._to_response(asset)

    def create_asset_from_bytes(
        self,
        session: Session,
        user_id: UUID,
        data: bytes,
        wardrobe_item_id: UUID | None = None,
    ) -> MediaAssetResponse:
        # Bytes ingestion used by POST /v1/media/upload. Not a download API.
        if self.storage is None:
            raise RuntimeError("StoragePort is required to persist bytes.")
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError
        if wardrobe_item_id is not None:
            item = self.repository.get_wardrobe_item_by_id(session, wardrobe_item_id)
            if item is None or item.user_id != user_id:
                raise WardrobeItemNotFoundError
        if not data:
            raise EmptyMediaUploadError
        reference = self.storage.put(data)
        asset = self.repository.create_asset(session, user_id, reference, wardrobe_item_id)
        session.commit()
        session.refresh(asset)
        return self._to_response(asset)

    def get_asset(
        self, session: Session, asset_id: UUID, user_id: UUID
    ) -> MediaAssetResponse:
        asset = self._get_owned_asset(session, asset_id, user_id)
        return self._to_response(asset)

    def get_asset_access_url(
        self, session: Session, asset_id: UUID, user_id: UUID
    ) -> MediaAssetAccessResponse:
        if self.storage is None:
            raise RuntimeError("StoragePort is required to create access URLs.")
        asset = self._get_owned_asset(session, asset_id, user_id)
        try:
            url = self.storage.create_access_url(
                asset.reference,
                settings.media_access_url_ttl_seconds,
            )
        except StorageObjectNotFoundError:
            raise StorageUnavailableError
        return MediaAssetAccessResponse(url=url)

    def delete_asset(self, session: Session, asset_id: UUID, user_id: UUID) -> None:
        if self.storage is None:
            raise RuntimeError("StoragePort is required to delete bytes.")
        asset = self._get_owned_asset(session, asset_id, user_id)
        # Storage delete is idempotent. The media_assets row is the durable
        # retry record: a later DELETE with the same asset_id recovers a
        # partial failure without workers or extra schema.
        self.storage.delete(asset.reference)
        self.repository.delete_asset(session, asset)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise MediaDeletionIncompleteError

    def _get_owned_asset(
        self, session: Session, asset_id: UUID, user_id: UUID
    ) -> MediaAsset:
        asset = self.repository.get_asset_by_id(session, asset_id)
        if asset is None or asset.user_id != user_id:
            raise MediaAssetNotFoundError
        return asset

    def _to_response(self, asset: MediaAsset) -> MediaAssetResponse:
        return MediaAssetResponse(
            id=asset.id,
            user_id=asset.user_id,
            wardrobe_item_id=asset.wardrobe_item_id,
            reference=asset.reference,
        )
