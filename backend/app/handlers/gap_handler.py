from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.gap_schema import GapRequest, GapResponse
from app.services.gap_service import GapService


def analyze_gaps(
    _payload: GapRequest,
    session: Session,
    user: User,
) -> GapResponse:
    service = GapService()
    return service.analyze_gaps(session, user.id)
