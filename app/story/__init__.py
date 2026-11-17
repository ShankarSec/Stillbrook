"""
Story/recon artifact routes.
"""
import os

from flask import Blueprint, session, send_from_directory, abort

story_bp = Blueprint("story", __name__, url_prefix="/story")

STORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "story")

PUBLIC_STORY_FILES = {
    "reports/password_policy.txt",
    "emails/welcome_intern01.eml",
    "reports/company_news.txt",
}

HIDDEN_FROM_INDEX = {"private_flags", "flag_texts"}

# ═══════════════════════════════════════════════════════════
# FILE-LEVEL ACL
# Each role gets an explicit list of files they can see/read.
# "dir/*" means all files in that directory.
# Specific files are listed individually.
# ═══════════════════════════════════════════════════════════

ROLE_FILES = {
    "employee": [
        # Reports
        "reports/company_news.txt",
        "reports/password_policy.txt",
        # Emails — only their own + general
        "emails/welcome_intern01.eml",
        "emails/intern_welcome.eml",
        # Chats — only general/watercooler
        "chats/general_watercooler.txt",
        "chats/random.txt",
        "chats/hr_announcements.txt",
        # Tickets — only their own + general helpdesk
        "tickets/TCK-2026-0645.txt",
        "tickets/TCK-2026-0101.txt",
        "tickets/TCK-2026-0189.txt",
        "tickets/TCK-2026-0312.txt",
        "tickets/TCK-2026-0415.txt",
        "tickets/TCK-2026-0534.txt",
        "tickets/TCK-2026-0567.txt",
        "tickets/TCK-2026-0601.txt",
        "tickets/hd-9999.txt",
        # Noise — all (it's public)
        "noise/birthday_calendar.txt",
        "noise/cafeteria_survey.txt",
        "noise/gym_request_log.txt",
        "noise/parking_assignment.txt",
        "noise/wellness_event.txt",
        # HR — only roster (not reviews, not org chart)
        "hr/employee_roster.txt",
    ],

    "engineer": [
        # Everything employee has
        "reports/company_news.txt",
        "reports/password_policy.txt",
        "emails/welcome_intern01.eml",
        "emails/intern_welcome.eml",
        "emails/migration_status.eml",
        "emails/blackecho_migration_mrivera.eml",
        "emails/phoenix_dr_dnguyen.eml",
        "chats/general_watercooler.txt",
        "chats/random.txt",
        "chats/hr_announcements.txt",
        "chats/eng_standup.txt",
        "chats/migration-war-room.txt",
        "chats/blackecho_migration_teams.txt",
        "chats/security-alerts.txt",
        "tickets/TCK-2026-0645.txt",
        "tickets/TCK-2026-0101.txt",
        "tickets/TCK-2026-0189.txt",
        "tickets/TCK-2026-0312.txt",
        "tickets/TCK-2026-0415.txt",
        "tickets/TCK-2026-0534.txt",
        "tickets/TCK-2026-0567.txt",
        "tickets/TCK-2026-0601.txt",
        "tickets/hd-9999.txt",
        "tickets/TCK-2026-0234.txt",
        "tickets/TCK-2026-0441.txt",
        "tickets/TCK-2026-0589.txt",
        "noise/birthday_calendar.txt",
        "noise/cafeteria_survey.txt",
        "noise/gym_request_log.txt",
        "noise/parking_assignment.txt",
        "noise/wellness_event.txt",
        "hr/employee_roster.txt",
        "hr/contractor_list.txt",
        # Projects — engineering charters
        "projects/blackecho_charter.txt",
        "projects/orion_integration_charter.txt",
        "projects/spring_onboarding_charter.txt",
    ],

    "operations_lead": [
        # Everything engineer has + operations-specific
        "reports/company_news.txt",
        "reports/password_policy.txt",
        "emails/welcome_intern01.eml",
        "emails/intern_welcome.eml",
        "emails/migration_status.eml",
        "emails/blackecho_migration_mrivera.eml",
        "emails/phoenix_dr_dnguyen.eml",
        "emails/backup_validation.eml",
        "emails/dr_incident_followup.eml",
        "emails/meeting_followup.eml",
        "emails/phoenix_dr_backupadmin_provisioning.eml",
        "chats/general_watercooler.txt",
        "chats/random.txt",
        "chats/hr_announcements.txt",
        "chats/eng_standup.txt",
        "chats/migration-war-room.txt",
        "chats/blackecho_migration_teams.txt",
        "chats/security-alerts.txt",
        "chats/ops_standup.txt",
        "chats/phoenix_dr_teams.txt",
        "chats/phoenix_dr_backup_ops.txt",
        "chats/onboarding_teams.txt",
        "tickets/TCK-2026-0645.txt",
        "tickets/TCK-2026-0101.txt",
        "tickets/TCK-2026-0189.txt",
        "tickets/TCK-2026-0312.txt",
        "tickets/TCK-2026-0415.txt",
        "tickets/TCK-2026-0534.txt",
        "tickets/TCK-2026-0567.txt",
        "tickets/TCK-2026-0601.txt",
        "tickets/hd-9999.txt",
        "tickets/TCK-2026-0234.txt",
        "tickets/TCK-2026-0441.txt",
        "tickets/TCK-2026-0589.txt",
        "tickets/TCK-2026-0356.txt",
        "tickets/TCK-2026-0478.txt",
        "tickets/TCK-2026-0512.txt",
        "noise/birthday_calendar.txt",
        "noise/cafeteria_survey.txt",
        "noise/gym_request_log.txt",
        "noise/parking_assignment.txt",
        "noise/wellness_event.txt",
        "hr/employee_roster.txt",
        "hr/contractor_list.txt",
        "hr/annual_review_2026.txt",
        "hr/org_chart.txt",
        # Projects — all
        "projects/blackecho_charter.txt",
        "projects/orion_integration_charter.txt",
        "projects/spring_onboarding_charter.txt",
        "projects/phoenix_dr_charter.txt",
        "projects/orion_budget_charter.txt",
        # Shares
        "shares/operations_share.txt",
        "shares/engineering_share.txt",
    ],

    "finance_manager": [
        # Everything operations_lead has + finance-specific
        "reports/company_news.txt",
        "reports/password_policy.txt",
        "emails/welcome_intern01.eml",
        "emails/intern_welcome.eml",
        "emails/migration_status.eml",
        "emails/blackecho_migration_mrivera.eml",
        "emails/phoenix_dr_dnguyen.eml",
        "emails/backup_validation.eml",
        "emails/dr_incident_followup.eml",
        "emails/meeting_followup.eml",
        "emails/phoenix_dr_backupadmin_provisioning.eml",
        "emails/budget_approval.eml",
        "emails/orion_assignment_jcastillo.eml",
        "emails/password_reset_request.eml",
        "emails/old_password_reset.eml",
        "emails/service_provisioning.eml",
        "chats/general_watercooler.txt",
        "chats/random.txt",
        "chats/hr_announcements.txt",
        "chats/eng_standup.txt",
        "chats/migration-war-room.txt",
        "chats/blackecho_migration_teams.txt",
        "chats/security-alerts.txt",
        "chats/ops_standup.txt",
        "chats/phoenix_dr_teams.txt",
        "chats/phoenix_dr_backup_ops.txt",
        "chats/onboarding_teams.txt",
        "chats/finance_sync.txt",
        "chats/orion_budget_teams.txt",
        "chats/orion_sync_ops.txt",
        "chats/vendor-support.txt",
        "chats/it_admin.txt",
        "tickets/TCK-2026-0645.txt",
        "tickets/TCK-2026-0101.txt",
        "tickets/TCK-2026-0189.txt",
        "tickets/TCK-2026-0312.txt",
        "tickets/TCK-2026-0415.txt",
        "tickets/TCK-2026-0534.txt",
        "tickets/TCK-2026-0567.txt",
        "tickets/TCK-2026-0601.txt",
        "tickets/hd-9999.txt",
        "tickets/TCK-2026-0234.txt",
        "tickets/TCK-2026-0441.txt",
        "tickets/TCK-2026-0589.txt",
        "tickets/TCK-2026-0356.txt",
        "tickets/TCK-2026-0478.txt",
        "tickets/TCK-2026-0512.txt",
        "tickets/TCK-2026-0401.txt",
        "tickets/TCK-2026-0548.txt",
        "tickets/TCK-2026-0115.txt",
        "noise/birthday_calendar.txt",
        "noise/cafeteria_survey.txt",
        "noise/gym_request_log.txt",
        "noise/parking_assignment.txt",
        "noise/wellness_event.txt",
        "hr/employee_roster.txt",
        "hr/contractor_list.txt",
        "hr/annual_review_2026.txt",
        "hr/org_chart.txt",
        "projects/blackecho_charter.txt",
        "projects/orion_integration_charter.txt",
        "projects/spring_onboarding_charter.txt",
        "projects/phoenix_dr_charter.txt",
        "projects/orion_budget_charter.txt",
        "shares/operations_share.txt",
        "shares/engineering_share.txt",
        "shares/finance_share.txt",
    ],

    "dr_admin": [
        # dr_admin gets directory-level wildcard (sees everything)
        "reports/*",
        "emails/*",
        "chats/*",
        "tickets/*",
        "noise/*",
        "hr/*",
        "projects/*",
        "cmdb/*",
        "logs/*",
        "shares/*",
        "vault/*",
    ],

    "admin": [
        "reports/*",
        "emails/*",
        "chats/*",
        "tickets/*",
        "noise/*",
        "hr/*",
        "projects/*",
        "cmdb/*",
        "logs/*",
        "shares/*",
        "vault/*",
    ],

    "service_account": [
        "reports/password_policy.txt",
        "cmdb/service_inventory.txt",
        "cmdb/application_registry.txt",
    ],
}


def _can_access(role: str, filename: str) -> bool:
    """Check if a role can access a specific file."""
    allowed = ROLE_FILES.get(role, [])

    for entry in allowed:
        if entry.endswith("/*"):
            # Directory wildcard
            dir_name = entry[:-2]  # "reports/*" → "reports"
            if filename.startswith(dir_name + "/"):
                return True
        elif entry == filename:
            return True

    return False


def role_has_any(role: str, dir_name: str) -> bool:
    """Sprint 3: used by the dashboard to decide which widgets to show,
    WITHOUT duplicating any file content outside this module's ACL. A
    widget only appears if the viewer's role actually has at least one
    file (or a wildcard) in that directory per ROLE_FILES -- so the
    dashboard can never show a stronger signal ("you have DR access")
    than the file-level ACL already grants. Widgets link into /story/,
    they never inline the restricted content itself."""
    prefix = f"{dir_name}/"
    return any(entry.startswith(prefix) for entry in ROLE_FILES.get(role, []))


@story_bp.route("/")
def index():
    if "username" not in session:
        return """<h3>Stillbrook Internal Resources</h3>
        <p>Public documents:</p>
        <ul>
          <li><a href="/story/reports/password_policy.txt">Password Policy</a></li>
          <li><a href="/story/emails/welcome_intern01.eml">Spring Onboarding Welcome</a></li>
          <li><a href="/story/reports/company_news.txt">Company News (Q1 2026)</a></li>
        </ul>
        <p style="color:#666;font-size:0.9rem;">Additional resources available after authentication.</p>"""

    role = session.get("role", "employee")
    allowed_files = ROLE_FILES.get(role, [])

    # Build index grouped by directory, only showing allowed files
    dir_files = {}
    for entry in allowed_files:
        if entry.endswith("/*"):
            dir_name = entry[:-2]
            dir_path = os.path.join(STORY_DIR, dir_name)
            if os.path.isdir(dir_path):
                files = sorted(os.listdir(dir_path))
                dir_files.setdefault(dir_name, []).extend(
                    f"{dir_name}/{fn}" for fn in files
                )
        else:
            d = entry.split("/")[0]
            dir_files.setdefault(d, []).append(entry)

    sections = []
    for d in sorted(dir_files.keys()):
        if d in HIDDEN_FROM_INDEX:
            continue
        files = sorted(set(dir_files[d]))
        file_links = "".join(
            f'<li><a href="/story/{fn}">{fn.split("/")[-1]}</a></li>'
            for fn in files
        )
        sections.append(f"<h4>{d}</h4><ul>{file_links}</ul>")

    return f"<h3>Stillbrook Internal Resources</h3>{''.join(sections)}"


@story_bp.route("/<path:filename>")
def file(filename):
    if filename.startswith("private_flags/") or filename.startswith("flag_texts/"):
        abort(403)

    if "username" not in session:
        if filename not in PUBLIC_STORY_FILES:
            abort(403)
        return send_from_directory(STORY_DIR, filename)

    role = session.get("role", "employee")

    if not _can_access(role, filename):
        abort(403)

    return send_from_directory(STORY_DIR, filename)   
