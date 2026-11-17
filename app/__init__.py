"""
Stillbrook Corporation -- vulnerable-by-design training application.
Sprint 1+2 combined slice:
- Authentication (+ lockout)
- Roles + cross-route ACL enforcement
- Sessions
- Logging
- Basic Detection
- Story/recon blueprint
- Flag delivery
"""

import os
import secrets

from flask import Flask, render_template


def create_app(config_name: str = "default") -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates"
        ),
    )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    # New random key every restart → all old session cookies become invalid.
    # This is the lab reset mechanism: restart the app = fresh sessions.
    app.config["SECRET_KEY"] = secrets.token_hex(32)

    app.config["DATABASE_PATH"] = os.environ.get(
        "STILLBROOK_DB",
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "database",
            "users.db",
        ),
    )

    app.config["ACL_DB_PATH"] = os.environ.get(
        "STILLBROOK_ACL_DB",
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "database",
            "acl.db",
        ),
    )

    # ------------------------------------------------------------------
    # Blueprints
    # ------------------------------------------------------------------

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.story import story_bp
    app.register_blueprint(story_bp)

    # Sprint 5
    from app.finance import finance_bp
    app.register_blueprint(finance_bp)

    # Sprint 6
    from app.engineering import engineering_bp
    app.register_blueprint(engineering_bp)

    # ------------------------------------------------------------------
    # Root Route
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        # Serve the login page here directly so the portal root is the
        # Flask-rendered login screen (proxied by nginx on port 80).
        return render_template("auth/login.html")

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    @app.route("/health")
    def health():
        return {
            "application": "Stillbrook",
            "status": "healthy",
            "version": "1.3"
        }, 200

    # ------------------------------------------------------------------
    # Error Handlers
    # ------------------------------------------------------------------
    # SPRINT 4 FIX: abort(403) in app/story/__init__.py (and anywhere else
    # in the app) previously rendered Werkzeug's bare default error page
    # instead of the project's own forbidden.html -- inconsistent UX and,
    # with STB_DEBUG=1, would leak a full traceback on every denied file
    # request. One handler covers every 403 in the app from here on.

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("dashboard/forbidden.html"), 403

    return app
