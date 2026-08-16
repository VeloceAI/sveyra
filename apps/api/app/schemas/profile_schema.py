from pydantic import BaseModel


class ProfileSummary(BaseModel):
    user_id: str
    style_words: list[str]
    wardrobe_items: int
    fit_profile_ready: bool
    avatar_ready: bool
