import secrets
import time

from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

from app.auth import auth_bp
from app.db import get_db
from app.logging_utils import log_auth_event

# In-memory token store for Sprint 1. Fine for a single-process dev server;
# swap for a reset_tokens table if this needs to survive restarts.
_RESET_TOKENS = {}
_TOKEN_TTL_SECONDS = 900


@auth_bp.route("/password-reset", methods=["GET", "POST"])
def password_reset_request():
    if request.method == "GET":
        return render_template("auth/password_reset.html")

    username = request.form.get("username", "").strip()
    ip = request.remote_addr or "unknown"

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if user is not None:
        token = secrets.token_urlsafe(32)  # cryptographically random, not timestamp-based
        _RESET_TOKENS[token] = {"user_id": user["id"], "expires": time.time() + _TOKEN_TTL_SECONDS}
        log_auth_event("password_reset", username, ip, "token_issued")
        # Dev convenience only — a real deployment would email this, never return it.
        flash(f"Reset link: /auth/password-reset/{token}")
    else:
        log_auth_event("password_reset", username, ip, "unknown_user")
        flash("If that account exists, a reset link has been issued.")

    return redirect(url_for("auth.login"))


@auth_bp.route("/password-reset/<token>", methods=["GET", "POST"])
def password_reset_confirm(token):
    entry = _RESET_TOKENS.get(token)
    if entry is None or entry["expires"] < time.time():
        flash("That reset link is invalid or has expired.")
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        return render_template("auth/password_reset_confirm.html", token=token)

    new_password = request.form.get("password", "")
    if not new_password:
        flash("Password is required.")
        return render_template("auth/password_reset_confirm.html", token=token), 400

    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), entry["user_id"]),
    )
    db.commit()
    del _RESET_TOKENS[token]

    flash("Password updated. Please log in.")
    return redirect(url_for("auth.login"))
