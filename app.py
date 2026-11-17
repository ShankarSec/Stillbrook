import os
import sqlite3
import time
from collections import defaultdict
from urllib.parse import unquote

from flask import abort, request

from app import create_app

app = create_app()

# ---------------------------------------------------------------------------
# reports table -- target of the blind SQLi in /api/search.
# The Flask app uses the local SQLite helper, so the "database" is the same
# users.db file the rest of the app uses. Seeded on startup and idempotent.
# ---------------------------------------------------------------------------

REPORT_SEED = [
    (
        1,
        "j.castillo",
        "Q1 2026 Budget Report -- OrionBudget",
        "OrionBudget Q1 Summary\nTotal allocation: $2.4M\n"
        "Redis cache at redis:6379 holds session tokens.",
        "2026-03-20",
    ),
    (
        2,
        "r.sharma",
        "Q1 2026 Financial Summary",
        "Q1 Financial Summary\nRevenue: $8.2M (up 12% YoY)\nOpEx: $5.1M",
        "2026-03-15",
    ),
    (
        3,
        "c.lindgren",
        "Q1 Data Export Log -- OrionBudget",
        "Export Log -- Q1 2026\nDB connection for exports: "
        "postgresql://postgres:stillbrook_prod_2026@postgres:5432/stillbrook",
        "2026-03-20",
    ),
]


def _ensure_reports_table():
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id      INTEGER PRIMARY KEY,
                owner   TEXT NOT NULL,
                title   TEXT NOT NULL,
                content TEXT,
                created TEXT
            )
            """
        )
        conn.executemany(
            "INSERT OR IGNORE INTO reports (id, owner, title, content, created) "
            "VALUES (?, ?, ?, ?, ?)",
            REPORT_SEED,
        )
        conn.commit()
    finally:
        conn.close()


_ensure_reports_table()

# ---------------------------------------------------------------------------
# WAF -- intentionally incomplete. It blocks the classic union/comment
# keywords but lets boolean operators, quotes, parentheses and time-based
# functions through so a blind SQLi remains exploitable.
# ---------------------------------------------------------------------------

WAF_BLOCKED_TOKENS = ("UNION", "SELECT", "INSERT", "DROP", "--", "/*", "#")
WAF_WINDOW_SECONDS = 60
WAF_BLOCK_THRESHOLD = 3
_waf_hits = defaultdict(list)


@app.before_request
def stillbrook_waf():
    raw_query = unquote(request.query_string.decode("utf-8", errors="ignore"))
    if not any(token in raw_query.upper() for token in WAF_BLOCKED_TOKENS):
        return None

    client = request.remote_addr or "unknown"
    now = time.time()
    recent = [t for t in _waf_hits[client] if now - t < WAF_WINDOW_SECONDS]
    recent.append(now)
    _waf_hits[client] = recent

    if len(recent) >= WAF_BLOCK_THRESHOLD:
        return "Access temporarily denied", 403
    return "Forbidden", 403


# ---------------------------------------------------------------------------
# Decoy endpoints -- always 403. These are noise for anyone scanning the
# app; the real finance export lives on the v2 API path below.
# ---------------------------------------------------------------------------


@app.route("/admin", strict_slashes=False)
def decoy_admin():
    abort(403)


@app.route("/debug", strict_slashes=False)
def decoy_debug():
    abort(403)


@app.route("/config", strict_slashes=False)
def decoy_config():
    abort(403)


@app.route("/api/v1/", strict_slashes=False)
def decoy_api_v1():
    abort(403)


@app.route("/wp-admin", strict_slashes=False)
def decoy_wp_admin():
    abort(403)


@app.route("/phpmyadmin", strict_slashes=False)
def decoy_phpmyadmin():
    abort(403)


# ---------------------------------------------------------------------------
# Blind SQLi. The user input is interpolated straight into the SQL text.
# Results are never rendered (blind), errors never leak details, and the
# WAF above filters out UNION/comment based payloads. SLEEP is registered as
# a SQLite function so time-based inference works in this lab.
# ---------------------------------------------------------------------------


@app.route("/api/search")
def api_search():
    from app.db import get_db

    q = request.args.get("q", "")
    db = get_db()

    # One-shot sleep per request: a multi-row OR payload still delays by
    # ~N seconds rather than N * rows, which keeps the oracle readable.
    slept = [False]

    def _sqlite_sleep(seconds):
        if not slept[0]:
            slept[0] = True
            try:
                time.sleep(max(0.0, min(float(seconds), 10.0)))
            except (TypeError, ValueError):
                pass
        return 0

    db.create_function("SLEEP", 1, _sqlite_sleep)

    # VULN: f-string interpolation of untrusted input into SQL. The tiny
    # builder appends the closing quote of the LIKE literal; an input that
    # already supplies a balanced function call (e.g. OR SLEEP(5)) closes
    # it itself, so no quote is appended.
    quote = "" if q.rstrip().endswith(")") else "'"
    sql = f"SELECT id, title FROM reports WHERE title LIKE '%{q}{quote}"
    try:
        db.execute(sql).fetchall()
    except sqlite3.Error:
        # No error text, no row output -- keep the injection blind.
        abort(500)

    return "Search complete.", 200


@app.errorhandler(500)
def internal_error(e):
    return "Internal Server Error", 500


@app.after_request
def add_headers(response):
    response.headers["Server"] = "Stillbrook"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Frame-Options"] = "DENY"
    return response


if __name__ == "__main__":
    # SPRINT 1 FIX: debug=True previously hardcoded, which exposes the
    # interactive Werkzeug debugger (arbitrary code execution) on
    # 0.0.0.0 to anyone who can trigger an unhandled exception. Default
    # is now OFF; set STB_DEBUG=1 explicitly for local dev only — never
    # in a build that will be network-reachable.
    debug_mode = os.environ.get("STB_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
