import sqlite3

from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

from app.auth import auth_bp
from app.db import get_db
from app.logging_utils import log_auth_event


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth/register.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    department = request.form.get("department", "general").strip()
    ip = request.remote_addr or "unknown"

    if not username or not password:
        flash("Username and password are required.")
        return render_template("auth/register.html"), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash, role, department) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), "employee", department),
        )
        db.commit()
    except sqlite3.IntegrityError:
        log_auth_event("register", username, ip, "failure")
        flash("That username is already taken.")
        return render_template("auth/register.html"), 409

    log_auth_event("register", username, ip, "success")
    flash("Account created. You can log in now.")
    return redirect(url_for("auth.login"))
