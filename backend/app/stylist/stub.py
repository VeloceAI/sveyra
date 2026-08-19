from app.services.recommendation_engine import RankedOutfit, RankingContext, rank_outfits_from_context
from app.stylist.port import StylistPort


class StubStylist(StylistPort):
    """Deterministic default stylist. Not an LLM provider."""

    def recommend(self, context: RankingContext) -> list[RankedOutfit]:
        return rank_outfits_from_context(context)
