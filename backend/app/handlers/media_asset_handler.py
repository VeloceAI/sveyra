from uuid import UUID

from fastapi import Request, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import MediaUploadTooLargeError
from app.models.user import User
from app.schemas.media_asset_schema import (
    MediaAssetAccessResponse,
    MediaAssetCreateRequest,
    MediaAssetResponse,
)
from app.services.media_asset_service import MediaAssetService
from app.storage.port import StoragePort

_MULTIPART_OVERHEAD_BYTES = 64 * 1024
_READ_CHUNK_SIZE = 64 * 1024


def _reject_if_content_length_exceeds_limit(request: Request, max_bytes: int) -> None:
    content_length = request.headers.get("content-length")
    if content_length is None:
        return
    try:
        declared_length = int(content_length)
    except ValueError:
        return
    if declared_length > max_bytes + _MULTIPART_OVERHEAD_BYTES:
        raise MediaUploadTooLargeError


async def _read_upload_bounded(
    file: UploadFile, request: Request, max_bytes: int
) -> bytes:
    _reject_if_content_length_exceeds_limit(request, max_bytes)

    if file.size is not None and file.size > max_bytes:
        raise MediaUploadTooLargeError

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise MediaUploadTooLargeError
        chunks.append(chunk)
    return b"".join(chunks)


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


def get_media_asset_bytes(
    asset_id: UUID, session: Session, storage: StoragePort, user: User
) -> bytes:
    return MediaAssetService(storage=storage).get_asset_bytes(session, asset_id, user.id)


async def upload_media_asset(
    file: UploadFile,
    wardrobe_item_id: UUID | None,
    session: Session,
    storage: StoragePort,
    user: User,
    request: Request,
) -> MediaAssetResponse:
    data = await _read_upload_bounded(
        file, request, settings.media_max_upload_bytes
    )
    service = MediaAssetService(storage=storage)
    return service.create_asset_from_bytes(session, user.id, data, wardrobe_item_id)


def delete_media_asset(
    asset_id: UUID, session: Session, storage: StoragePort, user: User
) -> None:
    service = MediaAssetService(storage=storage)
    service.delete_asset(session, asset_id, user.id)
