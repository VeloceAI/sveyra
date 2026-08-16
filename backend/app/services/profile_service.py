from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile_schema import ProfileSummary


class ProfileService:
    def __init__(self, repository: ProfileRepository | None = None) -> None:
        self.repository = repository or ProfileRepository()

    def get_summary(self) -> ProfileSummary:
        profile = self.repository.get_demo_profile()
        return ProfileSummary(**profile)
