from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.avatar.errors import AvatarUnavailableError
from app.avatar.port import AvatarPort
from app.core.config import settings
from app.core.errors import MediaUploadTooLargeError
from app.models.user import User
from app.schemas.avatar_schema import AvatarBuildResponse
from app.services.media_asset_service import MediaAssetService
from app.storage.port import StoragePort

_VIEWS = ("front", "side", "back")


async def build_avatar_from_photos(
    files: dict[str, UploadFile | None],
    height_cm: float,
    session: Session,
    user: User,
    avatar: AvatarPort,
    storage: StoragePort,
) -> AvatarBuildResponse:
    if not hasattr(avatar, "build_from_photos"):
        raise AvatarUnavailableError(
            "The configured avatar backend cannot build from photographs. "
            "Set AVATAR_BACKEND=sveyra."
        )

    photos: dict[str, bytes] = {}
    for view in _VIEWS:
        upload = files.get(view)
        if upload is None:
            continue
        data = await _read_bounded(upload)
        if data:
            photos[view] = data

    result, report = avatar.build_from_photos(photos, height_cm)  # type: ignore[attr-defined]

    # The GLB is already in storage; register it so the caller can fetch it
    # through the ordinary media access route rather than a bespoke one.
    asset = MediaAssetService(storage=storage).register_reference(
        session, user.id, str(result.mesh_reference)
    )
    return AvatarBuildResponse(
        asset_id=str(asset.id),
        backend=result.backend,
        source_views=int(report.get("source_views", len(photos))),
        measurements=report.get("measurements", {}),
        body_parameters=report.get("body_parameters", {}),
        confidence=report.get("confidence", {}),
        profiling_ms=report.get("profiling_ms", {}),
    )


async def _read_bounded(upload: UploadFile) -> bytes:
    """Same ceiling as ordinary media upload, enforced while streaming."""
    limit = settings.media_max_upload_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise MediaUploadTooLargeError
        chunks.append(chunk)
    return b"".join(chunks)


def _unused(_: UUID) -> None:  # pragma: no cover
    return None
