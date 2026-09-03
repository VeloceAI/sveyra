from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_APP_ENVS = frozenset({"local", "dev", "development", "test"})
_DEFAULT_JWT_SECRET = "change-me"
_DEFAULT_MEDIA_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://sveyra:sveyra@localhost:5432/sveyra"
    redis_url: str = "redis://localhost:6379/0"
    model_provider: str = "openai"
    storage_backend: str = "memory"
    gcs_bucket_name: str | None = None
    gcs_object_prefix: str = ""
    media_access_url_ttl_seconds: int = Field(default=900, gt=0, le=3600)
    media_max_upload_bytes: int = Field(
        default=_DEFAULT_MEDIA_MAX_UPLOAD_BYTES,
        gt=0,
        le=100 * 1024 * 1024,
    )
    jwt_secret: str = Field(default=_DEFAULT_JWT_SECRET)
    jwt_access_ttl_seconds: int = Field(default=900, gt=0, le=3600)
    refresh_token_ttl_seconds: int = Field(default=30 * 24 * 3600, gt=0, le=365 * 24 * 3600)
    auth_rate_limit_max_requests: int = Field(default=10, gt=0, le=1000)
    auth_rate_limit_window_seconds: int = Field(default=60, gt=0, le=3600)
    avatar_backend: str = "stub"
    vision_backend: str = "stub"
    stylist_backend: str = "stub"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def require_secure_jwt_secret_outside_local(self) -> Self:
        env = self.app_env.strip().lower()
        if env in _LOCAL_APP_ENVS:
            return self
        secret = self.jwt_secret.strip()
        if not secret or secret == _DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET must be set to a non-default secret when APP_ENV is not "
                f"local/dev (current APP_ENV={self.app_env!r})."
            )
        return self


settings = Settings()
