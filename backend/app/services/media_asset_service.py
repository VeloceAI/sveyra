from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    EmptyMediaUploadError,
    MediaAssetNotFoundError,
    MediaDeletionIncompleteError,
    UserNotFoundError,
    WardrobeItemNotFoundError,
)
from app.models.media_asset import MediaAsset
from app.repositories.media_asset_repository import MediaAssetRepository
from app.schemas.media_asset_schema import (
    MediaAssetAccessResponse,
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

    def create_asset_from_bytes(
        self,
        session: Session,
        user_id: UUID,
        data: bytes,
        wardrobe_item_id: UUID | None = None,
    ) -> MediaAssetResponse:
        """Persist an uploaded media object and create its asset row."""
        if self.storage is None:
            raise RuntimeError("StoragePort is required to persist bytes.")

        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError

        if wardrobe_item_id is not None:
            item = self.repository.get_wardrobe_item_by_id(
                session, wardrobe_item_id
            )
            if item is None or item.user_id != user_id:
                raise WardrobeItemNotFoundError

        if not data:
            raise EmptyMediaUploadError

        # The storage layer creates the reference.
        # The client never supplies a storage reference.
        reference = self.storage.put(data)

        asset = self.repository.create_asset(
            session,
            user_id,
            reference,
            wardrobe_item_id,
        )

        session.commit()
        session.refresh(asset)

        return self._to_response(asset)

    def register_reference(
        self,
        session: Session,
        user_id: UUID,
        reference: str,
    ) -> MediaAsset:
        """Record a reference created by the server.

        Used for server-generated assets such as avatars. The reference
        does not originate from an untrusted client request.
        """
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError

        asset = self.repository.create_asset(
            session,
            user_id,
            reference,
            None,
        )

        session.commit()
        session.refresh(asset)

        return asset

    def get_asset(
        self,
        session: Session,
        asset_id: UUID,
        user_id: UUID,
    ) -> MediaAssetResponse:
        asset = self._get_owned_asset(session, asset_id, user_id)
        return self._to_response(asset)

    def get_asset_access_url(
        self,
        session: Session,
        asset_id: UUID,
        user_id: UUID,
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

    def get_asset_bytes(
        self,
        session: Session,
        asset_id: UUID,
        user_id: UUID,
    ) -> bytes:
        """Return owned media bytes for clients that need the object itself."""
        if self.storage is None:
            raise RuntimeError("StoragePort is required to read bytes.")

        asset = self._get_owned_asset(session, asset_id, user_id)

        try:
            return self.storage.get(asset.reference)
        except StorageObjectNotFoundError:
            raise StorageUnavailableError

    def delete_asset(
        self,
        session: Session,
        asset_id: UUID,
        user_id: UUID,
    ) -> None:
        if self.storage is None:
            raise RuntimeError("StoragePort is required to delete bytes.")

        asset = self._get_owned_asset(session, asset_id, user_id)

        # Storage deletion is idempotent. The database row remains until
        # the transaction succeeds, allowing a later DELETE to retry.
        self.storage.delete(asset.reference)
        self.repository.delete_asset(session, asset)

        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise MediaDeletionIncompleteError

    def _get_owned_asset(
        self,
        session: Session,
        asset_id: UUID,
        user_id: UUID,
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
        )