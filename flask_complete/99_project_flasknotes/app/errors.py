"""Central error handling: JSON for /api/*, HTML pages for the web UI."""
import logging

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Raise from API code: ApiError('Not found', 404)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def _wants_json() -> bool:
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        return jsonify(error={"message": exc.message, "status": exc.status}), exc.status

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        if _wants_json():
            return jsonify(error={"message": exc.description, "status": exc.code}), exc.code
        if exc.code == 404:
            return render_template("404.html"), 404
        return render_template("error.html", error=exc), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        # Log the real cause for us; show the client nothing sensitive.
        logger.exception("Unhandled exception: %s", exc)
        if _wants_json():
            return jsonify(error={"message": "Internal server error", "status": 500}), 500
        return render_template("error.html", error=None), 500
