"""The HTTP layer — a minimal Flask app. Framework choice is incidental: the same
pipeline (lint → test → scan → build → deploy) applies unchanged to FastAPI/Django.
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, redirect, request

from . import __version__
from .core import generate_slug, is_valid_url, normalize_url

# in-memory store; a real app would use a database (and a migration stage in CI)
_LINKS: dict[str, str] = {}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        """Liveness probe — the deploy smoke test hits this."""
        return jsonify(status="ok", version=__version__)

    @app.post("/shorten")
    def shorten():
        data = request.get_json(silent=True) or {}
        url = normalize_url(str(data.get("url", "")))
        if not is_valid_url(url):
            return jsonify(error="invalid url; must be http(s)://…"), 400
        slug = generate_slug()
        _LINKS[slug] = url
        return jsonify(slug=slug, url=url), 201

    @app.get("/<slug>")
    def follow(slug: str):
        target = _LINKS.get(slug)
        if not target:
            return jsonify(error="not found"), 404
        return redirect(target, code=302)

    return app


app = create_app()

if __name__ == "__main__":
    # bind to all interfaces inside the container so the published port is reachable;
    # override with HOST/PORT. (A production deployment uses gunicorn, not app.run.)
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "8000")))
