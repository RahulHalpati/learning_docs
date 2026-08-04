"""A tiny end-to-end demo: store a link, read it back, back it up, drain events.

    AWS_ENDPOINT_URL=http://localhost:4566 python -m app.demo
"""

from __future__ import annotations

from .config import load_config
from .storage import LinkStore


def main() -> int:
    cfg = load_config()
    masked = cfg["secret_key"][:3] + "***"
    print(f"config:  secret_key={masked} (Secrets Manager)  table={cfg['links_table']} (SSM)")

    store = LinkStore()

    store.put("abc123", "https://example.com")
    print("put:     abc123 -> https://example.com")

    url = store.get("abc123")
    print(f"get:     abc123 -> {url}")

    key = store.backup("abc123", url)
    print(f"backup:  s3 key {key}")

    events = store.drain_events()
    print(f"events:  {events}")

    assert url == "https://example.com"
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
