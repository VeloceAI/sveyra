from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.profile_repository import ProfileRepository
from app.schemas.shopping_schema import ShoppingResponse
from app.services.gap_service import GapService
from app.shopping.port import ShoppingPort
from app.shopping.stub import StubShopping


class ShoppingService:
    """Orchestrates shopping recommendations based on wardrobe gaps and user budget."""

    def __init__(
        self,
        gap_service: GapService | None = None,
        profile_repository: ProfileRepository | None = None,
        shopping_port: ShoppingPort | None = None,
    ) -> None:
        self.gap_service = gap_service or GapService()
        self.profile_repository = profile_repository or ProfileRepository()
        self.shopping_port = shopping_port or StubShopping()

    def recommend_shopping(self, session: Session, user_id: UUID) -> ShoppingResponse:
        # 1. Get wardrobe gaps using GapService
        gap_response = self.gap_service.analyze_gaps(session, user_id)
        gap_categories = [gap.category for gap in gap_response.gaps]

        # 2. Get user budget constraints from style profile, defaulting to empty dict
        budget: dict[str, object] = {}
        style_profile = self.profile_repository.get_style_profile_by_user_id(session, user_id)
        if style_profile is not None and isinstance(style_profile.budget, dict):
            budget = dict(style_profile.budget)

        # 3. Retrieve matching products from ShoppingPort
        products = self.shopping_port.get_recommendations_for_categories(gap_categories, budget)

        return ShoppingResponse(products=products)
