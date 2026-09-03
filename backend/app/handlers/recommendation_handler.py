from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.recommendation_schema import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import RecommendationService
from app.stylist.port import StylistPort


def create_recommendations(
    payload: RecommendationRequest,
    session: Session,
    user: User,
    stylist: StylistPort,
) -> RecommendationResponse:
    service = RecommendationService(stylist=stylist)
    return service.recommend(session, user.id, payload)
