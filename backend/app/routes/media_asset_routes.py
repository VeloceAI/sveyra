from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.media_asset_handler import (
    create_media_asset,
    delete_media_asset,
    get_media_asset,
    get_media_asset_access,
    get_media_asset_bytes,
    upload_media_asset,
)
from app.models.user import User
from app.schemas.media_asset_schema import (
    MediaAssetAccessResponse,
    MediaAssetCreateRequest,
    MediaAssetResponse,
)
from app.storage.deps import get_storage
from app.storage.port import StoragePort

router = APIRouter(prefix="/media", tags=["media"])


@router.post("", response_model=MediaAssetResponse)
def create_asset(
    payload: MediaAssetCreateRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MediaAssetResponse:
    return create_media_asset(payload, session, user)


@router.post("/upload", response_model=MediaAssetResponse)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    wardrobe_item_id: UUID | None = Form(None),
    session: Session = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> MediaAssetResponse:
    return await upload_media_asset(file, wardrobe_item_id, session, storage, user, request)


@router.get("/{asset_id}/access", response_model=MediaAssetAccessResponse)
def read_asset_access(
    asset_id: UUID,
    session: Session = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> MediaAssetAccessResponse:
    return get_media_asset_access(asset_id, session, storage, user)


@router.get("/{asset_id}/content")
def read_asset_content(
    asset_id: UUID,
    session: Session = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> Response:
    payload = get_media_asset_bytes(asset_id, session, storage, user)
    # GLB is the only binary this serves today; anything else still downloads.
    media_type = "model/gltf-binary" if payload[:4] == b"glTF" else "application/octet-stream"
    return Response(content=payload, media_type=media_type)


@router.get("/{asset_id}", response_model=MediaAssetResponse)
def read_asset(
    asset_id: UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MediaAssetResponse:
    return get_media_asset(asset_id, session, user)


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: UUID,
    session: Session = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> None:
    delete_media_asset(asset_id, session, storage, user)
