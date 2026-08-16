from app.schemas.profile_schema import ProfileSummary
from app.services.profile_service import ProfileService


def get_profile_summary() -> ProfileSummary:
    service = ProfileService()
    return service.get_summary()
