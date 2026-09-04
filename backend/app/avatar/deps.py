from fastapi import Request

from app.avatar.port import AvatarPort
from app.avatar.stub import StubAvatar
from app.core.config import settings
from app.storage.port import StoragePort


def build_avatar(storage: StoragePort | None = None) -> AvatarPort:
    backend = settings.avatar_backend.lower()
    if backend in {"stub", "memory", "inmemory"}:
        return StubAvatar()
    if backend in {"sveyra", "sveyra3d", "engine"}:
        if storage is None:
            raise ValueError("AVATAR_BACKEND=sveyra needs a StoragePort")
        from app.avatar.sveyra_engine import SveyraEngineAvatar

        return SveyraEngineAvatar(storage=storage)
    raise ValueError(f"Unsupported AVATAR_BACKEND: {settings.avatar_backend}")


def get_avatar(request: Request) -> AvatarPort:
    return request.app.state.avatar
