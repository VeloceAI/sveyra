from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.avatar.deps import get_avatar
from app.avatar.port import AvatarPort
from app.db.session import get_db
from app.handlers.avatar_handler import build_avatar_from_photos, check_capture
from app.models.user import User
from app.schemas.avatar_schema import AvatarBuildResponse, CaptureCheckResponse
from app.storage.deps import get_storage
from app.storage.port import StoragePort

router = APIRouter(prefix="/avatar", tags=["avatar"])


@router.post("/build", response_model=AvatarBuildResponse)
async def build(
    height_cm: float = Form(...),
    front: UploadFile = File(...),
    side: UploadFile | None = File(None),
    back: UploadFile | None = File(None),
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    avatar: AvatarPort = Depends(get_avatar),
    storage: StoragePort = Depends(get_storage),
) -> AvatarBuildResponse:
    return await build_avatar_from_photos(
        {"front": front, "side": side, "back": back},
        height_cm,
        session,
        user,
        avatar,
        storage,
    )


@router.post("/check", response_model=CaptureCheckResponse)
async def check(
    front: UploadFile = File(...),
    side: UploadFile | None = File(None),
    back: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    avatar: AvatarPort = Depends(get_avatar),
) -> CaptureCheckResponse:
    """Tell someone what to fix before they pay for a reconstruction."""
    return await check_capture({"front": front, "side": side, "back": back}, avatar)
