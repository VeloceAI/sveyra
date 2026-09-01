from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.errors import (
    BodyProfileNotFoundError,
    EmailAlreadyRegisteredError,
    EmptyMediaUploadError,
    InvalidCredentialsError,
    InvalidTokenError,
    MediaAssetNotFoundError,
    MediaDeletionIncompleteError,
    MediaUploadTooLargeError,
    OutfitNotFoundError,
    ProfileNotFoundError,
    UnauthorizedError,
    UserNotFoundError,
    WardrobeEmptyError,
    WardrobeItemNotFoundError,
    WardrobeMediaMissingError,
    body_profile_not_found_handler,
    email_already_registered_handler,
    empty_media_upload_handler,
    invalid_credentials_handler,
    invalid_token_handler,
    media_asset_not_found_handler,
    media_deletion_incomplete_handler,
    media_upload_too_large_handler,
    not_found_handler,
    outfit_not_found_handler,
    profile_not_found_handler,
    request_validation_handler,
    storage_unavailable_handler,
    unauthorized_handler,
    user_not_found_handler,
    vision_unavailable_handler,
    wardrobe_empty_handler,
    wardrobe_item_not_found_handler,
    wardrobe_media_missing_handler,
)
from app.routes.auth_routes import router as auth_router
from app.routes.body_profile_routes import router as body_profile_router
from app.routes.health_routes import router as health_router
from app.routes.media_asset_routes import router as media_asset_router
from app.routes.outfit_routes import router as outfit_router
from app.routes.profile_routes import router as profile_router
from app.routes.recommendation_routes import router as recommendation_router
from app.routes.wardrobe_routes import router as wardrobe_router
from app.storage.deps import build_storage
from app.storage.errors import StorageUnavailableError
from app.storage.port import StoragePort
from app.stylist.deps import build_stylist
from app.stylist.port import StylistPort
from app.vision.deps import build_vision
from app.vision.errors import VisionUnavailableError
from app.vision.port import VisionPort


def create_app(
    storage: StoragePort | None = None,
    vision: VisionPort | None = None,
    stylist: StylistPort | None = None,
) -> FastAPI:
    app = FastAPI(title="SVEYRA API", version="0.1.0")
    # Attach Settings for request/app access without opening DB, Redis, or model clients.
    app.state.settings = settings
    app.state.storage = storage if storage is not None else build_storage()
    app.state.vision = vision if vision is not None else build_vision()
    app.state.stylist = stylist if stylist is not None else build_stylist()
    app.add_exception_handler(404, not_found_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(ProfileNotFoundError, profile_not_found_handler)
    app.add_exception_handler(UserNotFoundError, user_not_found_handler)
    app.add_exception_handler(BodyProfileNotFoundError, body_profile_not_found_handler)
    app.add_exception_handler(WardrobeItemNotFoundError, wardrobe_item_not_found_handler)
    app.add_exception_handler(MediaAssetNotFoundError, media_asset_not_found_handler)
    app.add_exception_handler(OutfitNotFoundError, outfit_not_found_handler)
    app.add_exception_handler(EmptyMediaUploadError, empty_media_upload_handler)
    app.add_exception_handler(MediaUploadTooLargeError, media_upload_too_large_handler)
    app.add_exception_handler(StorageUnavailableError, storage_unavailable_handler)
    app.add_exception_handler(MediaDeletionIncompleteError, media_deletion_incomplete_handler)
    app.add_exception_handler(UnauthorizedError, unauthorized_handler)
    app.add_exception_handler(InvalidTokenError, invalid_token_handler)
    app.add_exception_handler(InvalidCredentialsError, invalid_credentials_handler)
    app.add_exception_handler(EmailAlreadyRegisteredError, email_already_registered_handler)
    app.add_exception_handler(WardrobeEmptyError, wardrobe_empty_handler)
    app.add_exception_handler(WardrobeMediaMissingError, wardrobe_media_missing_handler)
    app.add_exception_handler(VisionUnavailableError, vision_unavailable_handler)
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/v1")
    app.include_router(profile_router, prefix="/v1")
    app.include_router(body_profile_router, prefix="/v1")
    app.include_router(wardrobe_router, prefix="/v1")
    app.include_router(media_asset_router, prefix="/v1")
    app.include_router(outfit_router, prefix="/v1")
    app.include_router(recommendation_router, prefix="/v1")
    return app


app = create_app()
