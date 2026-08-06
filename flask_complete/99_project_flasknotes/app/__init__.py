"""Application factory — the heart of a production Flask app.

create_app() builds a fully-wired Flask instance. Because it's a function, you
can build several (dev, testing) with different config in the same process —
which is exactly what the test suite does.
"""
import logging
import os
import sys

from flask import Flask

from app.config import config_by_name
from app.errors import register_error_handlers
from app.extensions import db, login_manager, migrate


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name[config_name]())
    app.config.from_prefixed_env()          # FLASK_* env vars override (Flask 2.2+)

    _configure_logging(app)

    # Bind extensions to THIS app instance.
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Import models so Flask-Migrate/create_all can see them.
    from app import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(models.User, int(user_id))

    # Blueprints: each feature is a module registered here.
    from app.blueprints.api import api_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.web import web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    register_error_handlers(app)

    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


def _configure_logging(app: Flask) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if app.debug else logging.INFO)
