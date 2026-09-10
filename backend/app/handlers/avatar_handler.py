from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.avatar.errors import AvatarUnavailableError
from app.avatar.port import AvatarPort
from app.core.config import settings
from app.core.errors import MediaUploadTooLargeError
from app.models.user import User
from app.schemas.avatar_schema import (
    AvatarBuildResponse,
    CanonicalAvatarResponse,
    CaptureCheckResponse,
)
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


async def check_capture(
    files: dict[str, UploadFile | None], avatar: AvatarPort
) -> CaptureCheckResponse:
    if not hasattr(avatar, "check_photos"):
        raise AvatarUnavailableError(
            "The configured avatar backend cannot check photographs. "
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

    report = avatar.check_photos(photos)  # type: ignore[attr-defined]
    return CaptureCheckResponse(
        ready=bool(report["ready"]),
        views=report["views"],
        overall=list(report["overall"]),
    )


async def build_canonical_avatar(
    height_cm: float,
    session: Session,
    user: User,
    avatar: AvatarPort,
    storage: StoragePort,
    measurements: dict[str, float] | None = None,
) -> CanonicalAvatarResponse:
    if not hasattr(avatar, "build_canonical_preview"):
        raise AvatarUnavailableError(
            "The configured avatar backend cannot build a canonical 3D preview. "
            "Set AVATAR_BACKEND=sveyra."
        )

    result, report = avatar.build_canonical_preview(  # type: ignore[attr-defined]
        height_cm, measurements
    )
    asset = MediaAssetService(storage=storage).register_reference(
        session, user.id, str(result.mesh_reference)
    )
    return CanonicalAvatarResponse(
        asset_id=str(asset.id),
        backend=result.backend,
        stage=str(report["stage"]),
        topology_id=str(report["topology_id"]),
        topology_version=str(report["topology_version"]),
        rig_id=str(report["rig_id"]),
        rig_version=str(report["rig_version"]),
        height_cm=float(report["height_cm"]),
        vertex_count=int(report["vertex_count"]),
        triangle_count=int(report["triangle_count"]),
        joint_count=int(report["joint_count"]),
        rigged=bool(report["rigged"]),
        parameter_fitted=bool(report["parameter_fitted"]),
        identity_fitted=bool(report["identity_fitted"]),
        photoreal_ready=bool(report["photoreal_ready"]),
        deformation_method=(
            str(report["deformation_method"])
            if report["deformation_method"] is not None
            else None
        ),
        supported_measurements=[str(value) for value in report["supported_measurements"]],
        applied_measurement_ratios={
            str(name): float(value)
            for name, value in dict(report["applied_measurement_ratios"]).items()
        },
        clamped_measurements=[str(value) for value in report["clamped_measurements"]],
        limitations=[str(value) for value in report["limitations"]],
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
