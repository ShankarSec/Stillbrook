from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

from app.auth import login, logout, register, password_reset  # noqa: E402,F401
