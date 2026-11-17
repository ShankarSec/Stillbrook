"""
Finance Module -- Sprint 5
Planted vuln: IDOR on /api/v2/fin/exports/<id>.
Any authenticated user can view any report by changing the ID -- no
ownership check, no role check beyond "is logged in at all".

The finance UI no longer advertises the report endpoint: the legacy
report URL names were retired when finance migrated to the v2 API.
The export endpoint is only reachable if you know the path.

Wired to logging/detections/idor.py so this vuln is detected, not just
exploitable -- matches the project's standard (vuln + detection + test
as one unit, never a vuln shipped without its matching detection rule).
"""
from flask import Blueprint, session, render_template, abort

from app.access_control import login_required
from app.logging_utils import log_web_event
from app.detection_loader import idor_detection

finance_bp = Blueprint("finance", __name__)

# Simulated reports (in production: DB rows). These intentionally mirror
# the narrative clues from story/shares/finance_share.txt and the
# Redis/Postgres connection strings used elsewhere in the attack chain --
# an IDOR here is how a low-priv player learns those details without
# ever having finance_manager access.
REPORTS = {
    1: {
        "id": 1,
        "owner": "j.castillo",
        "title": "Q1 2026 Budget Report -- OrionBudget",
        "content": """\
OrionBudget Q1 Summary
======================
Total allocation: $2.4M
Spent: $1.1M (46%)
Remaining: $1.3M

Key items:
- sa_finance_export token rotated 2026-01-28. Next: 2026-04-28.
- Export pipeline owner: C. Lindgren
- Q2 lock date: 2026-05-15

Internal note: The Redis cache at redis:6379 holds session tokens.
If you need to debug a session issue, use:
  redis-cli -h redis -p 6379 GET session:admin_api_key

-- J. Castillo, 2026-03-20
""",
        "created": "2026-03-20",
    },
    2: {
        "id": 2,
        "owner": "r.sharma",
        "title": "Q1 2026 Financial Summary",
        "content": """\
Q1 Financial Summary
====================
Revenue: $8.2M (up 12% YoY)
OpEx: $5.1M
Net: $3.1M

Notes:
- PagerDuty renewal: $14,200/yr (renews April 30)
- Monitor batch: $42,000 (arrives May 2)
- Office supplies: $3,200

-- R. Sharma, 2026-03-15
""",
        "created": "2026-03-15",
    },
    3: {
        "id": 3,
        "owner": "c.lindgren",
        "title": "Q1 Data Export Log -- OrionBudget",
        "content": """\
Export Log -- Q1 2026
=====================
2026-01-28: sa_finance_export token rotation (OK)
2026-02-15: Full Q4 export to S3 (12 datasets)
2026-03-01: Reporting module go-live
2026-03-15: Audit integration complete
2026-03-20: BKS-004 backup validated (12/12)

DB connection for exports:
  postgresql://postgres:stillbrook_prod_2026@postgres:5432/stillbrook

-- C. Lindgren, 2026-03-20
""",
        "created": "2026-03-20",
    },
}


@finance_bp.route("/finance/")
@login_required
def index():
    role = session.get("role", "")
    username = session["username"]

    log_web_event("/finance/", "GET", username, 200)

    # finance_manager sees all, others see only their own
    if role == "finance_manager":
        visible = REPORTS
    else:
        visible = {k: v for k, v in REPORTS.items() if v["owner"] == username}

    return render_template("finance/index.html", reports=list(visible.values()), role=role)


@finance_bp.route("/api/v2/fin/exports/<int:report_id>")
@login_required
def view_report(report_id):
    """
    VULN: IDOR. No ownership check.
    Any authenticated user can view any report by ID.
    """
    username = session["username"]
    role = session.get("role", "")

    report = REPORTS.get(report_id)
    if not report:
        abort(404)

    # BUG: No check that report["owner"] == session["username"]
    # or that session["role"] == "finance_manager" -- this is the
    # planted vuln. check_idor() below logs/detects the exploitation,
    # it does not block it (the vuln stays live, per project rules).
    idor_detection.check_idor(username, role, report_id, report["owner"])
    log_web_event(f"/api/v2/fin/exports/{report_id}", "GET", username, 200)

    return render_template("finance/report.html", report=report)


@finance_bp.route("/api/v2/fin/exports/<int:report_id>/export")
@login_required
def export_report(report_id):
    """
    VULN: Same IDOR. Exports as CSV.
    """
    username = session["username"]
    role = session.get("role", "")

    report = REPORTS.get(report_id)
    if not report:
        abort(404)

    # BUG: No ownership check (same vuln as view_report, different route)
    idor_detection.check_idor(username, role, report_id, report["owner"])
    log_web_event(f"/api/v2/fin/exports/{report_id}/export", "GET", username, 200)

    csv_content = (
        "id,title,owner,created,content\n"
        f'{report["id"]},{report["title"]},{report["owner"]},{report["created"]},"{report["content"]}"\n'
    )
    return (
        csv_content,
        200,
        {
            "Content-Disposition": f"attachment; filename=report_{report_id}.csv",
            "Content-Type": "text/csv",
        },
    )
