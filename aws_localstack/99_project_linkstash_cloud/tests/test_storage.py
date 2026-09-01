"""Integration tests against Floci.

These require Floci running and the infra applied (`make up && make apply`),
with AWS_ENDPOINT_URL=http://localhost:4566 in the environment. They exercise real
boto3 calls — the same code path as production, just pointed at Floci.
"""

import os

import pytest

from app.storage import LinkStore

pytestmark = pytest.mark.skipif(
    not os.environ.get("AWS_ENDPOINT_URL"),
    reason="set AWS_ENDPOINT_URL=http://localhost:4566 and apply infra first",
)


@pytest.fixture()
def store():
    return LinkStore()


def test_put_and_get(store):
    store.put("t-get", "https://example.org")
    assert store.get("t-get") == "https://example.org"


def test_missing_slug_returns_none(store):
    assert store.get("does-not-exist") is None


def test_backup_writes_to_s3(store):
    key = store.backup("t-bak", "https://example.org")
    assert key == "links/t-bak.txt"


def test_put_emits_event(store):
    store.drain_events()                 # clear anything pending
    store.put("t-evt", "https://example.net")
    events = store.drain_events()
    assert any("created:t-evt" in e for e in events)
