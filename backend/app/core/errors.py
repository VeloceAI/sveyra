from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.storage.errors import StorageUnavailableError
from app.vision.errors import VisionUnavailableError


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Request validation failed."
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    detail = first.get("msg", "Invalid value")
    if location:
        return f"{location}: {detail}"
    return str(detail)


class ProfileNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class BodyProfileNotFoundError(Exception):
    pass


class WardrobeItemNotFoundError(Exception):
    pass


class MediaAssetNotFoundError(Exception):
    pass


class OutfitNotFoundError(Exception):
    pass


class EmptyMediaUploadError(Exception):
    pass


class MediaUploadTooLargeError(Exception):
    pass


class MediaDeletionIncompleteError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


class WardrobeEmptyError(Exception):
    pass


class WardrobeMediaMissingError(Exception):
    pass


class AuthRateLimitExceededError(Exception):
    pass


async def not_found_handler(_request: Request, _exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("not_found", "The requested resource was not found."),
    )


async def profile_not_found_handler(
    _request: Request, _exc: ProfileNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("profile_not_found", "Profile was not found."),
    )


async def user_not_found_handler(_request: Request, _exc: UserNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("user_not_found", "User was not found."),
    )


async def body_profile_not_found_handler(
    _request: Request, _exc: BodyProfileNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("body_profile_not_found", "Body profile was not found."),
    )


async def wardrobe_item_not_found_handler(
    _request: Request, _exc: WardrobeItemNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("wardrobe_item_not_found", "Wardrobe item was not found."),
    )


async def media_asset_not_found_handler(
    _request: Request, _exc: MediaAssetNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("media_asset_not_found", "Media asset was not found."),
    )


async def outfit_not_found_handler(
    _request: Request, _exc: OutfitNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("outfit_not_found", "Outfit was not found."),
    )


async def empty_media_upload_handler(
    _request: Request, _exc: EmptyMediaUploadError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("empty_upload", "Uploaded file was empty."),
    )


async def media_upload_too_large_handler(
    _request: Request, _exc: MediaUploadTooLargeError
) -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content=error_body(
            "upload_too_large",
            "Uploaded file exceeds the maximum allowed size.",
        ),
    )


async def storage_unavailable_handler(
    _request: Request, _exc: StorageUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=error_body(
            "storage_unavailable",
            "Media storage is temporarily unavailable.",
        ),
    )


async def media_deletion_incomplete_handler(
    _request: Request, _exc: MediaDeletionIncompleteError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=error_body(
            "media_deletion_incomplete",
            "Media deletion could not be completed. Retry the same request.",
        ),
    )


async def unauthorized_handler(_request: Request, _exc: UnauthorizedError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_body("unauthorized", "Authentication is required."),
    )


async def invalid_token_handler(_request: Request, _exc: InvalidTokenError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_body("invalid_token", "The access token is invalid."),
    )


async def invalid_credentials_handler(
    _request: Request, _exc: InvalidCredentialsError
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_body("invalid_credentials", "Email or password is incorrect."),
    )


async def email_already_registered_handler(
    _request: Request, _exc: EmailAlreadyRegisteredError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=error_body("email_already_registered", "Email is already registered."),
    )


async def auth_rate_limit_exceeded_handler(
    _request: Request, _exc: AuthRateLimitExceededError
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=error_body(
            "rate_limit_exceeded",
            "Too many authentication attempts. Please try again later.",
        ),
    )


async def request_validation_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body("validation_error", _validation_message(exc)),
    )


async def wardrobe_empty_handler(
    _request: Request, _exc: WardrobeEmptyError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body(
            "wardrobe_empty",
            "No wardrobe items are available for recommendations.",
        ),
    )


async def wardrobe_media_missing_handler(
    _request: Request, _exc: WardrobeMediaMissingError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body(
            "wardrobe_media_missing",
            "No media asset is linked to this wardrobe item.",
        ),
    )


async def vision_unavailable_handler(
    _request: Request, _exc: VisionUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=error_body(
            "vision_unavailable",
            "Garment vision analysis is temporarily unavailable.",
        ),
    )
