"""JSON API (v1) — token-authenticated, separate from the session-based web UI."""
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request

from app.errors import ApiError
from app.extensions import db
from app.models import Note, User

api_bp = Blueprint("api", __name__)


# ---------------------------------------------------------------- auth helpers
def issue_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc)
              + timedelta(minutes=current_app.config["JWT_EXPIRES_MINUTES"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def token_required(view):
    """Decorator: require a valid `Authorization: Bearer <token>` header."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise ApiError("Missing or malformed Authorization header", 401)
        try:
            payload = jwt.decode(header[7:], current_app.config["JWT_SECRET"],
                                 algorithms=["HS256"])
        except jwt.PyJWTError:
            raise ApiError("Invalid or expired token", 401)
        user = db.session.get(User, int(payload["sub"]))
        if user is None:
            raise ApiError("User no longer exists", 401)
        g.current_user = user            # `g` = per-request context
        return view(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------- routes
@api_bp.post("/auth/token")
def get_token():
    data = request.get_json(silent=True) or {}
    user = db.session.scalar(db.select(User).filter_by(email=(data.get("email") or "").lower()))
    if user is None or not user.check_password(data.get("password") or ""):
        raise ApiError("Incorrect email or password", 401)
    return jsonify(access_token=issue_token(user), token_type="bearer")


@api_bp.get("/notes")
@token_required
def list_notes():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)   # bound it
    query = (db.select(Note).filter_by(user_id=g.current_user.id)
             .order_by(Note.id.desc()))
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    return jsonify(
        items=[n.to_dict() for n in pagination.items],
        total=pagination.total, page=pagination.page,
        per_page=pagination.per_page, pages=pagination.pages,
    )


@api_bp.post("/notes")
@token_required
def create_note():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        raise ApiError("`title` is required", 422)
    note = Note(title=title, body=data.get("body", ""), user_id=g.current_user.id)
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


def _owned_note(note_id: int) -> Note:
    note = db.session.get(Note, note_id)
    if note is None:
        raise ApiError("Note not found", 404)
    if note.user_id != g.current_user.id:          # don't leak other users' data
        raise ApiError("You do not have access to this note", 403)
    return note


@api_bp.get("/notes/<int:note_id>")
@token_required
def get_note(note_id: int):
    return jsonify(_owned_note(note_id).to_dict())


@api_bp.patch("/notes/<int:note_id>")
@token_required
def update_note(note_id: int):
    note = _owned_note(note_id)
    data = request.get_json(silent=True) or {}
    if "title" in data:
        if not (data["title"] or "").strip():
            raise ApiError("`title` cannot be empty", 422)
        note.title = data["title"].strip()
    if "body" in data:
        note.body = data["body"]
    db.session.commit()
    return jsonify(note.to_dict())


@api_bp.delete("/notes/<int:note_id>")
@token_required
def delete_note(note_id: int):
    db.session.delete(_owned_note(note_id))
    db.session.commit()
    return "", 204
