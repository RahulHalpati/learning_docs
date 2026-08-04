"""Application settings — loaded from environment / .env (12-factor)."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TaskFlow"
    environment: str = "development"          # development | staging | production
    debug: bool = False

    # Database — SQLite by default (offline, zero-setup); Postgres in production:
    #   postgresql+asyncpg://user:pass@localhost:5432/taskflow
    database_url: str = "sqlite+aiosqlite:///./taskflow.db"

    # Auth. OVERRIDE jwt_secret in production (a long random string; ≥32 bytes).
    #   generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    jwt_secret: str = "dev-secret-change-me-in-production-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Integrations
    redis_url: str = "redis://localhost:6379"
    rate_limit: int = 100
    rate_window: int = 60

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so settings are parsed once per process."""
    return Settings()


settings = get_settings()
