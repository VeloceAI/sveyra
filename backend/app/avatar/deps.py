from fastapi import Request

from app.avatar.port import AvatarPort
from app.avatar.stub import StubAvatar
from app.core.config import settings


def build_avatar() -> AvatarPort:
    backend = settings.avatar_backend.lower()
    if backend in {"stub", "memory", "inmemory"}:
        return StubAvatar()
    raise ValueError(f"Unsupported AVATAR_BACKEND: {settings.avatar_backend}")


def get_avatar(request: Request) -> AvatarPort:
    return request.app.state.avatar
