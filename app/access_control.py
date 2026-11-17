"""
Shared access-control decorators. Every protected route in the app —
/dashboard today, finance/hr/engineering/admin in later sprints — uses
these two decorators so ACL enforcement is wired once and applied
everywhere consistently, instead of re-implemented per blueprint.
"""
from functools import wraps

from flask import session, redirect, url_for, abort

from app.db import get_acl_db


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def role_allowed(role: str, route: str) -> bool:
    db = get_acl_db()
    row = db.execute(
        "SELECT 1 FROM acl_rules WHERE role = ? AND route = ?", (role, route)
    ).fetchone()
    return row is not None


def acl_required(route: str):
    """Decorator factory: @acl_required('/dashboard') on any view.
    Checks login first, then checks the session role against acl_rules
    for the given route string (which need not match the Flask URL rule
    exactly — pass whatever logical resource name acl.db tracks)."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            role = session.get("role", "employee")
            if not role_allowed(role, route):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator
