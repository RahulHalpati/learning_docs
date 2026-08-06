"""Extensions created bare here, bound to an app in the factory via init_app().

This split is what makes the app factory work: the objects exist at import time
(so models/blueprints can import them) but aren't tied to any one app until
create_app() calls init_app(). One codebase, many app instances (dev, test).
"""
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"         # where @login_required redirects
                                                # (blueprint name + view name)
login_manager.login_message_category = "warning"
