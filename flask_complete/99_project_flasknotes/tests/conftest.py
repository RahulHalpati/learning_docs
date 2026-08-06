"""Test fixtures. Each test gets a fresh app + in-memory database.

This is the app factory paying off: `create_app("testing")` builds an isolated
instance per test, so nothing leaks between them.
"""
import pytest

from app import create_app
from app.extensions import db as _db
from app.models import User


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(email="ada@example.com")
    u.set_password("password123")
    _db.session.add(u)
    _db.session.commit()
    return u


@pytest.fixture
def auth_client(client, user):
    """A web client with a logged-in session."""
    client.post("/login", data={"email": "ada@example.com", "password": "password123"})
    return client


@pytest.fixture
def token(client, user):
    """A JWT for the JSON API."""
    r = client.post("/api/v1/auth/token",
                    json={"email": "ada@example.com", "password": "password123"})
    return r.get_json()["access_token"]


@pytest.fixture
def api_client(client, token):
    """A client that sends the bearer token on every request."""
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client
