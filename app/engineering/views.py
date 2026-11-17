"""
Engineering Module -- Sprint 6
Planted vuln: information disclosure of an internal Gitea repository
URL. A player who gets this URL can clone the repo (via the internal
network, post-SSH-pivot in Sprint 7) and find a leaked .env in the
commit history.

Access is role-gated to "engineer" -- the real seeded engineer account
is m.rivera (seed/users.yaml), NOT d.nguyen (who is operations_lead).
"""
from flask import Blueprint, session, render_template, jsonify

from app.access_control import login_required
from app.logging_utils import log_web_event

engineering_bp = Blueprint("engineering", __name__, url_prefix="/engineering")

# The git repo URL (leaked via these endpoints)
GIT_REPO_URL = "http://gitea:3000/stillbrook/web.git"
GIT_REPO_BARE = "git://gitea:9418/stillbrook/web.git"

ALLOWED_ROLES = ("engineer", "dr_admin", "admin")


def _role_denied():
    from flask import abort
    role = session.get("role", "")
    if role not in ALLOWED_ROLES:
        abort(403)


@engineering_bp.route("/")
@login_required
def index():
    _role_denied()
    log_web_event("/engineering/", "GET", session["username"], 200)
    return render_template("engineering/index.html", git_url=GIT_REPO_URL)


@engineering_bp.route("/source")
@login_required
def source_info():
    """
    VULN: Information disclosure.
    Reveals the internal Git repository URL. A player who knows this
    URL can clone the repo and find .env in the commit history.
    """
    _role_denied()
    log_web_event("/engineering/source", "GET", session["username"], 200)
    return jsonify(
        {
            "repository": GIT_REPO_URL,
            "bare_protocol": GIT_REPO_BARE,
            "branch": "main",
            "last_commit": "4a7f2e1",
            "note": "Clone and review for configuration issues.",
        }
    )


@engineering_bp.route("/pipeline")
@login_required
def pipeline_status():
    """Shows CI/CD pipeline status. References sa_eng_pipeline and sa_eng_ci."""
    _role_denied()
    log_web_event("/engineering/pipeline", "GET", session["username"], 200)
    return jsonify(
        {
            "pipeline": "BlackEchoMigrationPipeline",
            "status": "green",
            "last_run": "2026-03-28 14:22:00",
            "service_accounts": ["sa_eng_pipeline", "sa_eng_ci"],
            "repo": GIT_REPO_URL,
            "note": "If pipeline fails, check .env for DB connection string.",
        }
    )
