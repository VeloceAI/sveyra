from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.media_asset_handler import (
    delete_media_asset,
    get_media_asset,
    get_media_asset_access,
    upload_media_asset,
)
from app.models.user import User
from app.schemas.media_asset_schema import (
    MediaAssetAccessResponse,
    MediaAssetResponse,
)
from app.storage.deps import get_storage
from app.storage.port import StoragePort

router = APIRouter(prefix="/media", tags=["media"])


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
