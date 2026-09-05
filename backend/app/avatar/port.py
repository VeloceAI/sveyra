from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class AvatarRequest:
    user_id: UUID
    measurements: dict[str, object] = field(default_factory=dict)
    garment_references: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AvatarResult:
    """One rendered avatar.

    `image_reference` is set by 2D backends, `mesh_reference` by 3D ones. Both are
    StoragePort references, never URLs, so the storage adapter stays swappable.
    """

    backend: str
    image_reference: str | None = None
    mesh_reference: str | None = None


class AvatarPort:
    """Provider-neutral avatar rendering contract.

    Lets the 2D hosted backend and a later 3D pipeline swap by config, the same
    way STORAGE_BACKEND does.
    """

    def render(self, request: AvatarRequest) -> AvatarResult:
        raise NotImplementedError
