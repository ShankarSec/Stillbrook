"""
Dashboard blueprint -- Sprint 2 rebuild.
Uses the shared access_control decorators (not a local copy) so every
future department blueprint follows the same ACL pattern.
"""
import json
import os

from flask import Blueprint, render_template, session

from app.access_control import acl_required
from app.logging_utils import log_web_event
from app.scoring.flag_service import get_flag_for_session
from app.story import role_has_any, _can_access, STORY_DIR, ROLE_FILES

dashboard_bp = Blueprint("dashboard", __name__)

# Sprint 3: Department Discovery widgets. Each maps a dashboard widget to
# the story/ directory that gates it -- the widget shows a teaser (file
# count + directory name) and a link into /story/, never the content
# itself. This way the dashboard can't accidentally grant more than the
# file-level ACL in app/story/__init__.py already allows; it can only
# ever show LESS (a widget hidden entirely) if that ACL changes.
#
# "hr" is split into two separate widgets (not one directory-level
# widget) because employee only has hr/employee_roster.txt, not
# hr/org_chart.txt -- a single "Org Chart & Directory" widget would
# overpromise what's actually behind it for that role. Each entry below
# checks its OWN specific file via _can_access, same ACL function the
# story blueprint itself uses to deny access.
WIDGETS = [
    {"key": "directory", "file": "hr/employee_roster.txt", "dir": "hr", "label": "Employee Directory"},
    {"key": "org_chart", "file": "hr/org_chart.txt", "dir": "hr", "label": "Org Chart"},
    {"key": "cmdb", "file": None, "dir": "cmdb", "label": "Systems Inventory (CMDB)"},
    {"key": "dr_status", "file": None, "dir": "logs", "label": "DR / Backup Status"},
    {"key": "shares", "file": None, "dir": "shares", "label": "Department Shares"},
    {"key": "vault", "file": None, "dir": "vault", "label": "Executive Vault"},
]


def _visible_widgets(role: str) -> list[dict]:
    visible = []
    for widget in WIDGETS:
        if widget["file"] is not None:
            # file-specific widget: only show if the role can access
            # exactly this file (not just "something" in the directory)
            if not _can_access(role, widget["file"]):
                continue
            file_count = 1
        else:
            # directory-level widget: show if the role has any file (or
            # a wildcard) in this directory at all
            if not role_has_any(role, widget["dir"]):
                continue
            dir_path = os.path.join(STORY_DIR, widget["dir"])
            file_count = len(os.listdir(dir_path)) if os.path.isdir(dir_path) else 0
        visible.append({**widget, "file_count": file_count})
    return visible

AUTH_LOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "logging", "auth", "auth.log"
)


def _recent_activity_for(username: str, limit: int = 5) -> list[dict]:
    """Read the authenticated user's own recent auth events for the
    dashboard's activity log widget. Read-only, tail-only -- fine at
    this log size; revisit if logs grow large enough to need indexing."""
    if not os.path.exists(AUTH_LOG_PATH):
        return []

    events = []
    with open(AUTH_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if event.get("username") == username:
                events.append(event)

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events[:limit]


@dashboard_bp.route("/dashboard")
@acl_required("/dashboard")
def index():
    username = session.get("username", "unknown")
    role = session.get("role", "employee")
    department = session.get("department")
    project = session.get("project")

    log_web_event("/dashboard", "GET", username, 200)

    activity = _recent_activity_for(username)
    flag = get_flag_for_session()
    widgets = _visible_widgets(role)

    return render_template(
        "dashboard/dashboard.html",
        username=username,
        role=role,
        department=department,
        project=project,
        activity=activity,
        flag=flag,
        widgets=widgets,
    )
