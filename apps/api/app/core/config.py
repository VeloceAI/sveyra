from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://sveyra:sveyra@localhost:5432/sveyra"
    redis_url: str = "redis://localhost:6379/0"
    model_provider: str = "openai"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
