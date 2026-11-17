from flask import session, redirect, url_for, request

from app.auth import auth_bp
from app.logging_utils import log_auth_event


@auth_bp.route("/logout", methods=["POST"])
def logout():
    username = session.get("username", "anonymous")
    ip = request.remote_addr or "unknown"
    session.clear()
    log_auth_event("logout", username, ip, "success")
    return redirect(url_for("auth.login"))
