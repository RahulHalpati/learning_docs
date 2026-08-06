"""Session-based auth for the web UI (register, login, logout)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if not email or len(password) < 8:
            flash("Email required and password must be 8+ characters.", "error")
            return render_template("register.html"), 400
        if db.session.scalar(db.select(User).filter_by(email=email)):
            flash("That email is already registered.", "error")
            return render_template("register.html"), 409

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("web.index"))
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = db.session.scalar(db.select(User).filter_by(email=email))
        # Same message either way — don't reveal which emails exist.
        if user is None or not user.check_password(password):
            flash("Incorrect email or password.", "error")
            return render_template("login.html"), 401
        login_user(user)
        return redirect(url_for("web.index"))
    return render_template("login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
