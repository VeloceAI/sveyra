from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.avatar.deps import get_avatar
from app.avatar.port import AvatarPort
from app.db.session import get_db
from app.handlers.platform_handler import get_platform_readiness
from app.models.user import User
from app.schemas.platform_schema import PlatformReadinessResponse
from app.stylist.deps import get_stylist
from app.stylist.port import StylistPort
from app.vision.deps import get_vision
from app.vision.port import VisionPort

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/readiness", response_model=PlatformReadinessResponse)
def platform_readiness(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    avatar: AvatarPort = Depends(get_avatar),
    vision: VisionPort = Depends(get_vision),
    stylist: StylistPort = Depends(get_stylist),
) -> PlatformReadinessResponse:
    """Return one honest view of personal setup and system capability."""
    return get_platform_readiness(session, user, avatar, vision, stylist)
