from app.services.recommendation_engine import RankedOutfit, RankingContext


class StylistPort:
    """Provider-neutral stylist ranking/refinement contract."""

    def recommend(self, context: RankingContext) -> list[RankedOutfit]:
        raise NotImplementedError
