import time

from flask import render_template, request, session, redirect, url_for, flash
from werkzeug.security import check_password_hash

from app.auth import auth_bp
from app.db import get_db
from app.logging_utils import log_auth_event

# In-memory lockout tracker, keyed by username. Fine for a single-process
# dev/demo server; move to a table if this needs to survive restarts or
# run behind multiple workers.
#   {username: {"failures": int, "locked_until": float | None}}
_LOGIN_ATTEMPTS = {}

LOCKOUT_THRESHOLD = 5
LOCKOUT_SECONDS = 15 * 60


def _get_tracker(username: str) -> dict:
    return _LOGIN_ATTEMPTS.setdefault(username, {"failures": 0, "locked_until": None})


def _is_locked(tracker: dict) -> bool:
    locked_until = tracker.get("locked_until")
    if locked_until is None:
        return False
    if time.time() >= locked_until:
        # cooldown expired - clear lock and reset the strike count
        tracker["locked_until"] = None
        tracker["failures"] = 0
        return False
    return True


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    ip = request.remote_addr or "unknown"

    tracker = _get_tracker(username)

    if _is_locked(tracker):
        remaining = int(tracker["locked_until"] - time.time())
        log_auth_event("login", username, ip, "locked")
        flash(f"Account temporarily locked. Try again in {max(remaining, 1)} seconds.")
        return render_template("auth/login.html"), 423  # 423 Locked

    db = get_db()
    user = db.execute(
        "SELECT id, username, password_hash, role, department, project FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        tracker["failures"] += 1
        log_auth_event("login", username, ip, "failure")

        if tracker["failures"] >= LOCKOUT_THRESHOLD:
            tracker["locked_until"] = time.time() + LOCKOUT_SECONDS
            log_auth_event("login", username, ip, "lockout_triggered")
            flash(f"Too many failed attempts. Account locked for {LOCKOUT_SECONDS // 60} minutes.")
            return render_template("auth/login.html"), 423

        flash("Invalid username or password.")
        return render_template("auth/login.html"), 401

    # successful login clears any accumulated strikes
    tracker["failures"] = 0
    tracker["locked_until"] = None

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["department"] = user["department"]
    session["project"] = user["project"] if "project" in user.keys() else None

    log_auth_event("login", username, ip, "success")
    return redirect(url_for("dashboard.index"))
