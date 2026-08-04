"""Health probes."""


async def test_liveness(client):
    r = await client.get("/api/v1/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


async def test_readiness_checks_db(client):
    r = await client.get("/api/v1/readyz")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"
