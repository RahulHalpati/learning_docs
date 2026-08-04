"""Project & task CRUD, ownership isolation, pagination, filtering."""


async def _make_project(client, name="Website"):
    return (await client.post("/api/v1/projects",
            json={"name": name, "description": "d"})).json()


async def test_project_crud(auth_client):
    r = await auth_client.post("/api/v1/projects", json={"name": "P1", "description": "hi"})
    assert r.status_code == 201
    pid = r.json()["id"]

    assert (await auth_client.get(f"/api/v1/projects/{pid}")).status_code == 200

    r = await auth_client.patch(f"/api/v1/projects/{pid}", json={"name": "P1-renamed"})
    assert r.json()["name"] == "P1-renamed"

    assert (await auth_client.delete(f"/api/v1/projects/{pid}")).status_code == 204
    assert (await auth_client.get(f"/api/v1/projects/{pid}")).status_code == 404


async def test_pagination_envelope(auth_client):
    for i in range(3):
        await _make_project(auth_client, f"P{i}")
    r = await auth_client.get("/api/v1/projects?page=1&size=2")
    body = r.json()
    assert body["total"] == 3 and body["size"] == 2 and body["pages"] == 2
    assert len(body["items"]) == 2


async def test_task_crud_and_status_filter(auth_client):
    pid = (await _make_project(auth_client))["id"]
    await auth_client.post(f"/api/v1/projects/{pid}/tasks",
                           json={"title": "T1", "status": "todo"})
    await auth_client.post(f"/api/v1/projects/{pid}/tasks",
                           json={"title": "T2", "status": "done"})

    allt = (await auth_client.get(f"/api/v1/projects/{pid}/tasks")).json()
    assert allt["total"] == 2

    done = (await auth_client.get(f"/api/v1/projects/{pid}/tasks?status=done")).json()
    assert done["total"] == 1
    assert done["items"][0]["title"] == "T2"


async def test_ownership_isolation(client):
    # User A creates a project.
    await client.post("/api/v1/auth/register", json={
        "email": "a@x.com", "password": "password123", "full_name": "A"})
    ta = (await client.post("/api/v1/auth/login",
          data={"username": "a@x.com", "password": "password123"})).json()
    pid = (await client.post("/api/v1/projects",
           headers={"Authorization": f"Bearer {ta['access_token']}"},
           json={"name": "secret"})).json()["id"]

    # User B must NOT see or touch it.
    await client.post("/api/v1/auth/register", json={
        "email": "b@x.com", "password": "password123", "full_name": "B"})
    tb = (await client.post("/api/v1/auth/login",
          data={"username": "b@x.com", "password": "password123"})).json()
    hb = {"Authorization": f"Bearer {tb['access_token']}"}
    assert (await client.get(f"/api/v1/projects/{pid}", headers=hb)).status_code == 403
    assert (await client.get("/api/v1/projects", headers=hb)).json()["total"] == 0
