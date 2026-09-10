from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import WardrobeEmptyError, WardrobeItemNotFoundError
from app.repositories.body_profile_repository import BodyProfileRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.wardrobe_repository import WardrobeRepository
from app.schemas.recommendation_schema import (
    RecommendationCandidate,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.recommendation_engine import RankingContext, WardrobeItemSignal
from app.stylist.port import StylistPort
from app.stylist.stub import StubStylist


class RecommendationService:
    """Orchestrates occasion recommendations via StylistPort (deterministic by default)."""

    def __init__(
        self,
        wardrobe_repository: WardrobeRepository | None = None,
        profile_repository: ProfileRepository | None = None,
        body_profile_repository: BodyProfileRepository | None = None,
        stylist: StylistPort | None = None,
    ) -> None:
        self.wardrobe_repository = wardrobe_repository or WardrobeRepository()
        self.profile_repository = profile_repository or ProfileRepository()
        self.body_profile_repository = body_profile_repository or BodyProfileRepository()
        self.stylist = stylist or StubStylist()

    def recommend(
        self, session: Session, user_id: UUID, payload: RecommendationRequest
    ) -> RecommendationResponse:
        items = self.wardrobe_repository.list_all_items_by_user_id(session, user_id)
        if not items:
            raise WardrobeEmptyError

        owned_ids = {item.id for item in items if item.user_id == user_id}
        constrained_ids = {
            *payload.required_item_ids,
            *payload.excluded_item_ids,
        }
        if payload.replacement_item_id is not None:
            constrained_ids.add(payload.replacement_item_id)
        if not constrained_ids.issubset(owned_ids):
            # Use the same response for missing and foreign IDs so this endpoint
            # never reveals whether another user's wardrobe item exists.
            raise WardrobeItemNotFoundError

        replacement_item = next(
            (item for item in items if item.id == payload.replacement_item_id),
            None,
        )

        signals = [
            WardrobeItemSignal(
                id=item.id,
                category=item.category,
                color=item.color,
                brand=item.brand,
                attributes=dict(item.attributes or {}),
            )
            for item in items
            if item.user_id == user_id
        ]

        preferences: dict[str, object] = {}
        dislikes: dict[str, object] = {}
        budget: dict[str, object] = {}
        style_profile = self.profile_repository.get_style_profile_by_user_id(session, user_id)
        if style_profile is not None:
            if isinstance(style_profile.preferences, dict):
                preferences = dict(style_profile.preferences)
            if isinstance(style_profile.dislikes, dict):
                dislikes = dict(style_profile.dislikes)
            if isinstance(style_profile.budget, dict):
                budget = dict(style_profile.budget)

        fit_preferences: dict[str, object] = {}
        body_profile = self.body_profile_repository.get_latest_body_profile_by_user_id(
            session, user_id
        )
        if body_profile is not None and isinstance(body_profile.fit_preferences, dict):
            fit_preferences = dict(body_profile.fit_preferences)

        context = RankingContext(
            occasion=payload.occasion,
            items=signals,
            preferences=preferences,
            dislikes=dislikes,
            budget=budget,
            fit_preferences=fit_preferences,
            required_item_ids=frozenset(payload.required_item_ids),
            excluded_item_ids=frozenset(
                [
                    *payload.excluded_item_ids,
                    *(
                        [payload.replacement_item_id]
                        if payload.replacement_item_id is not None
                        else []
                    ),
                ]
            ),
            replacement_category=(
                replacement_item.category if replacement_item is not None else None
            ),
        )
        ranked = self.stylist.recommend(context)
        return RecommendationResponse(
            occasion=payload.occasion,
            recommendations=[
                RecommendationCandidate(item_ids=entry.item_ids, rationale=entry.rationale)
                for entry in ranked
            ],
        )
