"""JSON API: auth, CRUD, validation, pagination, ownership isolation."""
import pytest

from app.extensions import db
from app.models import User


def test_token_requires_correct_password(client, user):
    r = client.post("/api/v1/auth/token",
                    json={"email": "ada@example.com", "password": "WRONG"})
    assert r.status_code == 401
    assert r.get_json()["error"]["status"] == 401


def test_notes_require_a_token(client):
    assert client.get("/api/v1/notes").status_code == 401


def test_create_and_get_note(api_client):
    r = api_client.post("/api/v1/notes", json={"title": "Shopping", "body": "milk"})
    assert r.status_code == 201
    note = r.get_json()
    assert note["title"] == "Shopping"

    got = api_client.get(f"/api/v1/notes/{note['id']}")
    assert got.status_code == 200 and got.get_json()["body"] == "milk"


@pytest.mark.parametrize("payload,expected", [
    ({"title": ""}, 422),
    ({}, 422),
    ({"title": "Valid"}, 201),
])
def test_create_validation(api_client, payload, expected):
    assert api_client.post("/api/v1/notes", json=payload).status_code == expected


def test_pagination_envelope(api_client):
    for i in range(3):
        api_client.post("/api/v1/notes", json={"title": f"n{i}"})
    body = api_client.get("/api/v1/notes?page=1&per_page=2").get_json()
    assert body["total"] == 3 and body["pages"] == 2 and len(body["items"]) == 2


def test_patch_and_delete(api_client):
    nid = api_client.post("/api/v1/notes", json={"title": "Draft"}).get_json()["id"]
    r = api_client.patch(f"/api/v1/notes/{nid}", json={"title": "Final"})
    assert r.get_json()["title"] == "Final"
    assert api_client.delete(f"/api/v1/notes/{nid}").status_code == 204
    assert api_client.get(f"/api/v1/notes/{nid}").status_code == 404


def test_ownership_isolation(client, api_client):
    nid = api_client.post("/api/v1/notes", json={"title": "Secret"}).get_json()["id"]

    other = User(email="bob@example.com")
    other.set_password("password123")
    db.session.add(other)
    db.session.commit()
    tok = client.post("/api/v1/auth/token",
                      json={"email": "bob@example.com", "password": "password123"}
                      ).get_json()["access_token"]

    r = client.get(f"/api/v1/notes/{nid}", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403                       # knows who you are, still says no
    listed = client.get("/api/v1/notes", headers={"Authorization": f"Bearer {tok}"})
    assert listed.get_json()["total"] == 0            # sees none of Ada's notes
