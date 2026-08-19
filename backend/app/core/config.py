from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://sveyra:sveyra@localhost:5432/sveyra"
    redis_url: str = "redis://localhost:6379/0"
    model_provider: str = "openai"
    storage_backend: str = "memory"
    gcs_bucket_name: str | None = None
    gcs_object_prefix: str = ""
    media_access_url_ttl_seconds: int = Field(default=900, gt=0, le=3600)
    jwt_secret: str = Field(default="change-me")
    jwt_access_ttl_seconds: int = Field(default=900, gt=0, le=3600)
    vision_backend: str = "stub"
    stylist_backend: str = "stub"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
