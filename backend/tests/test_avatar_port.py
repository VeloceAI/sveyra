from uuid import uuid4

import pytest

from app.avatar import AvatarPort, AvatarRequest, AvatarUnavailableError, StubAvatar
from app.avatar.deps import build_avatar
from app.avatar.sveyra_engine import SveyraEngineAvatar
from app.core.config import settings
from app.storage.memory import InMemoryStorage


def test_stub_avatar_renders_from_measurements() -> None:
    user_id = uuid4()
    result = StubAvatar().render(AvatarRequest(user_id=user_id, measurements={"height_cm": 170}))
    assert result.backend == "stub"
    assert result.image_reference == f"avatar_stub_{user_id}"
    assert result.mesh_reference is None


def test_stub_avatar_rejects_an_empty_body_profile() -> None:
    with pytest.raises(AvatarUnavailableError):
        StubAvatar().render(AvatarRequest(user_id=uuid4()))


def test_build_avatar_returns_the_configured_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "avatar_backend", "stub")
    assert isinstance(build_avatar(), StubAvatar)


def test_build_avatar_uses_the_local_engine_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "avatar_backend", "sveyra")
    assert isinstance(build_avatar(InMemoryStorage()), SveyraEngineAvatar)


def test_build_avatar_rejects_an_unknown_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "avatar_backend", "midjourney")
    with pytest.raises(ValueError, match="Unsupported AVATAR_BACKEND"):
        build_avatar()


def test_avatar_port_contract_is_not_implemented_by_default() -> None:
    with pytest.raises(NotImplementedError):
        AvatarPort().render(AvatarRequest(user_id=uuid4()))
