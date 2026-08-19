from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.media_asset_schema import (
    MediaAssetAccessResponse,
    MediaAssetCreateRequest,
    MediaAssetResponse,
)
from app.services.media_asset_service import MediaAssetService
from app.storage.port import StoragePort


def create_media_asset(
    payload: MediaAssetCreateRequest, session: Session, user: User
) -> MediaAssetResponse:
    service = MediaAssetService()
    return service.create_asset(session, user.id, payload)


def get_media_asset(asset_id: UUID, session: Session, user: User) -> MediaAssetResponse:
    service = MediaAssetService()
    return service.get_asset(session, asset_id, user.id)


def get_media_asset_access(
    asset_id: UUID, session: Session, storage: StoragePort, user: User
) -> MediaAssetAccessResponse:
    service = MediaAssetService(storage=storage)
    return service.get_asset_access_url(session, asset_id, user.id)


async def upload_media_asset(
    file: UploadFile,
    wardrobe_item_id: UUID | None,
    session: Session,
    storage: StoragePort,
    user: User,
) -> MediaAssetResponse:
    data = await file.read()
    service = MediaAssetService(storage=storage)
    return service.create_asset_from_bytes(session, user.id, data, wardrobe_item_id)


def delete_media_asset(
    asset_id: UUID, session: Session, storage: StoragePort, user: User
) -> None:
    service = MediaAssetService(storage=storage)
    service.delete_asset(session, asset_id, user.id)
