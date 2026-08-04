"""Integration tests via Flask's test client — no server needed."""

import pytest

from app.main import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_shorten_and_follow(client):
    resp = client.post("/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 201
    slug = resp.get_json()["slug"]

    follow = client.get(f"/{slug}")
    assert follow.status_code == 302
    assert follow.headers["Location"] == "https://example.com"


def test_shorten_rejects_bad_url(client):
    resp = client.post("/shorten", json={"url": "ftp://nope"})
    assert resp.status_code == 400


def test_missing_slug_is_404(client):
    assert client.get("/doesnotexist").status_code == 404
