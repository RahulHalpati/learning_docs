"""Web UI: templates render, auth flow, protected pages, file upload, errors."""
import io


def test_index_renders_for_anonymous(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Please" in r.data                 # the "log in" prompt


def test_register_then_see_empty_notes(client):
    r = client.post("/register", data={"email": "new@example.com",
                                       "password": "password123"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b"No notes yet" in r.data


def test_duplicate_email_is_409(client, user):
    r = client.post("/register", data={"email": "ada@example.com",
                                       "password": "password123"})
    assert r.status_code == 409


def test_login_wrong_password_is_401(client, user):
    r = client.post("/login", data={"email": "ada@example.com", "password": "nope"})
    assert r.status_code == 401
    assert b"Incorrect email or password" in r.data


def test_new_note_requires_login(client):
    r = client.get("/notes/new")
    assert r.status_code == 302                 # redirected to the login page
    assert "/login" in r.headers["Location"]


def test_create_note_with_image_upload(auth_client):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    r = auth_client.post("/notes/new", data={
        "title": "With picture",
        "body": "see attached",
        "image": (io.BytesIO(png), "photo.png"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert r.status_code == 200
    assert b"With picture" in r.data
    assert b"<img" in r.data                    # the template rendered the image


def test_rejects_disallowed_file_type(auth_client):
    r = auth_client.post("/notes/new", data={
        "title": "Bad file",
        "image": (io.BytesIO(b"hi"), "notes.txt"),
    }, content_type="multipart/form-data")
    assert r.status_code == 415


def test_missing_title_is_400(auth_client):
    assert auth_client.post("/notes/new", data={"title": ""}).status_code == 400


def test_404_page(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404
    assert b"404" in r.data


def test_api_404_returns_json_not_html(client):
    r = client.get("/api/v1/no-such-endpoint")
    assert r.status_code == 404
    assert r.is_json                            # content negotiation by path


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}
