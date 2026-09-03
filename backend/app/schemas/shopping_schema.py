from pydantic import BaseModel, ConfigDict

from app.schemas.common import StrictRequestModel
from app.shopping.port import ShoppingProduct


class ShoppingRequest(StrictRequestModel):
    pass


class ShoppingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    products: list[ShoppingProduct]
