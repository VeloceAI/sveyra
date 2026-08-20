from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.shopping_schema import ShoppingRequest, ShoppingResponse
from app.services.shopping_service import ShoppingService


def recommend_shopping(
    _payload: ShoppingRequest,
    session: Session,
    user: User,
) -> ShoppingResponse:
    service = ShoppingService()
    return service.recommend_shopping(session, user.id)
