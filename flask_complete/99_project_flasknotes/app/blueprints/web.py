"""The HTML side: list/create notes with Jinja2 templates and file uploads."""
import uuid
from pathlib import Path

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, send_from_directory, url_for)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Note

web_bp = Blueprint("web", __name__)


def _allowed(filename: str) -> bool:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_upload(file_storage) -> str | None:
    """Validate and store an uploaded image; return the stored filename."""
    if not file_storage or not file_storage.filename:
        return None
    if not _allowed(file_storage.filename):
        raise ValueError("Only png/jpg/jpeg/gif images are allowed.")
    # secure_filename strips paths; the uuid prevents collisions & guessing.
    safe = secure_filename(file_storage.filename)
    stored = f"{uuid.uuid4().hex}{Path(safe).suffix.lower()}"
    file_storage.save(current_app.config["UPLOAD_FOLDER"] / stored)
    return stored


@web_bp.get("/")
def index():
    notes = []
    if current_user.is_authenticated:
        notes = db.session.scalars(
            db.select(Note).filter_by(user_id=current_user.id).order_by(Note.id.desc())
        ).all()
    return render_template("index.html", notes=notes)


@web_bp.route("/notes/new", methods=["GET", "POST"])
@login_required
def new_note():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        if not title:
            flash("Title is required.", "error")
            return render_template("new_note.html"), 400
        try:
            stored = save_upload(request.files.get("image"))
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("new_note.html"), 415

        note = Note(title=title, body=request.form.get("body", ""),
                    image=stored, user_id=current_user.id)
        db.session.add(note)
        db.session.commit()
        return redirect(url_for("web.index"))
    return render_template("new_note.html")


@web_bp.get("/uploads/<path:filename>")
def uploaded_file(filename: str):
    """Serve an uploaded image back."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
