import pytest
from fastapi.testclient import TestClient
from bookshelf.main import app, get_repo
from bookshelf.repository import BookRepository

# fresh repository per test via dependency override -> isolated tests
@pytest.fixture
def client():
    repo = BookRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()

VALID = {"title": "Dune", "author": "Herbert", "isbn": "9780441013593", "year": 1965}

def test_create_and_get(client):
    r = client.post("/books", json=VALID)
    assert r.status_code == 201
    book = r.json()
    assert book["id"] == 1 and book["title"] == "Dune"
    r2 = client.get(f"/books/{book['id']}")
    assert r2.status_code == 200 and r2.json()["author"] == "Herbert"

def test_list(client):
    client.post("/books", json=VALID)
    client.post("/books", json={**VALID, "isbn": "9780000000001", "title": "Other"})
    r = client.get("/books")
    assert r.status_code == 200 and len(r.json()) == 2

def test_not_found(client):
    r = client.get("/books/999")
    assert r.status_code == 404
    assert r.json() == {"error": "BookNotFoundError", "detail": "no book with id 999"}

def test_duplicate_isbn(client):
    client.post("/books", json=VALID)
    r = client.post("/books", json={**VALID, "title": "Dupe"})
    assert r.status_code == 409
    assert r.json()["error"] == "DuplicateISBNError"

def test_validation(client):
    r = client.post("/books", json={**VALID, "year": 1000})  # before 1450
    assert r.status_code == 422

def test_delete(client):
    client.post("/books", json=VALID)
    assert client.delete("/books/1").status_code == 204
    assert client.get("/books/1").status_code == 404
