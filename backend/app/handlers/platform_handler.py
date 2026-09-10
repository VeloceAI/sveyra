from sqlalchemy.orm import Session

from app.avatar.port import AvatarPort
from app.models.user import User
from app.schemas.platform_schema import PlatformReadinessResponse
from app.services.platform_service import PlatformService
from app.stylist.port import StylistPort
from app.vision.port import VisionPort


def get_platform_readiness(
    session: Session,
    user: User,
    avatar: AvatarPort,
    vision: VisionPort,
    stylist: StylistPort,
) -> PlatformReadinessResponse:
    return PlatformService().readiness(
        session,
        user.id,
        avatar,
        vision,
        stylist,
    )
