from fastapi import APIRouter

from app.handlers.profile_handler import get_profile_summary
from app.schemas.profile_schema import ProfileSummary

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/summary", response_model=ProfileSummary)
def profile_summary() -> ProfileSummary:
    return get_profile_summary()
