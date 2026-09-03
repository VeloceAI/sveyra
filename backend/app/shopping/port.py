from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ShoppingProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    brand: str
    price: float
    url: str
    category: Literal["top", "bottom", "shoes"]
    image_url: str | None = None


class ShoppingPort(ABC):
    """Provider-neutral commerce/shopping recommendation contract."""

    @abstractmethod
    def get_recommendations_for_categories(
        self,
        categories: list[Literal["top", "bottom", "shoes"]],
        budget: dict[str, object],
    ) -> list[ShoppingProduct]:
        """Fetch shoppable products for the given categories.

        Honours optional budget constraints.
        """
        pass
