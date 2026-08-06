"""Configuration classes — one per environment, selected by FLASK_ENV."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Defaults shared by every environment."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'flasknotes.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False        # off: saves memory, no benefit on
    JSON_SORT_KEYS = False

    # Uploads
    UPLOAD_FOLDER = BASE_DIR / "app" / "uploads"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024          # 2 MB cap, enforced by Flask itself
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

    # JWT (for the API)
    JWT_SECRET = os.environ.get("JWT_SECRET", SECRET_KEY)
    JWT_EXPIRES_MINUTES = int(os.environ.get("JWT_EXPIRES_MINUTES", "30"))


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"          # in-memory: fast, isolated
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        # Fail fast rather than run production on the dev secret.
        if self.SECRET_KEY == "dev-secret-change-me-in-production":
            raise RuntimeError("SECRET_KEY must be set in production")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
