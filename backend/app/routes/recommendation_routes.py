from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.gap_handler import analyze_gaps
from app.handlers.recommendation_handler import create_recommendations
from app.handlers.shopping_handler import recommend_shopping
from app.models.user import User
from app.schemas.gap_schema import GapRequest, GapResponse
from app.schemas.recommendation_schema import RecommendationRequest, RecommendationResponse
from app.schemas.shopping_schema import ShoppingRequest, ShoppingResponse
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


@router.post("/gaps", response_model=GapResponse)
def gaps(
    payload: GapRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GapResponse:
    return analyze_gaps(payload, session, user)


@router.post("/shopping", response_model=ShoppingResponse)
def shopping(
    payload: ShoppingRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShoppingResponse:
    return recommend_shopping(payload, session, user)
