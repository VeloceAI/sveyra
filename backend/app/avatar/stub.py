from app.avatar.errors import AvatarUnavailableError
from app.avatar.port import AvatarPort, AvatarRequest, AvatarResult


class StubAvatar(AvatarPort):
    """Deterministic placeholder. Renders nothing; holds the seam until a real backend lands."""

    def render(self, request: AvatarRequest) -> AvatarResult:
        if not request.measurements:
            raise AvatarUnavailableError
        return AvatarResult(backend="stub", image_reference=f"avatar_stub_{request.user_id}")
