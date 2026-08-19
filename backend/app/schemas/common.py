from pydantic import BaseModel, ConfigDict, Field

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListPaginationParams(StrictRequestModel):
    limit: int = Field(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT)
    offset: int = Field(default=0, ge=0)
