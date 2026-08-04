"""Auth flow: register, login, refresh, protected access."""


async def test_register_and_login(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "password": "password123", "full_name": "Ada"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@b.com"
    assert "hashed_password" not in r.json()          # never leak the hash

    r = await client.post("/api/v1/auth/login",
                          data={"username": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    assert {"access_token", "refresh_token"} <= r.json().keys()


async def test_duplicate_email_conflicts(client):
    body = {"email": "dup@b.com", "password": "password123", "full_name": "X"}
    await client.post("/api/v1/auth/register", json=body)
    r = await client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


async def test_wrong_password_rejected(client):
    await client.post("/api/v1/auth/register", json={
        "email": "c@b.com", "password": "password123", "full_name": "C"})
    r = await client.post("/api/v1/auth/login",
                          data={"username": "c@b.com", "password": "WRONG"})
    assert r.status_code == 401


async def test_protected_route_requires_token(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_refresh_issues_new_tokens(client):
    await client.post("/api/v1/auth/register", json={
        "email": "r@b.com", "password": "password123", "full_name": "R"})
    tokens = (await client.post("/api/v1/auth/login",
              data={"username": "r@b.com", "password": "password123"})).json()
    r = await client.post("/api/v1/auth/refresh",
                          json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert "access_token" in r.json()

    # An access token must NOT work as a refresh token.
    bad = await client.post("/api/v1/auth/refresh",
                            json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401
