from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.recommendation_handler import create_recommendations
from app.models.user import User
from app.schemas.recommendation_schema import RecommendationRequest, RecommendationResponse
from app.stylist.deps import get_stylist
from app.stylist.port import StylistPort

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def recommend(
    payload: RecommendationRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    stylist: StylistPort = Depends(get_stylist),
) -> RecommendationResponse:
    return create_recommendations(payload, session, user, stylist)
