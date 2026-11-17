"""
Idempotent seeder for Stillbrook's SQLite databases.

Usage:
    python seed/seed_db.py
    python seed/seed_db.py --reset        # drop + recreate tables first

This only covers the Sprint 1 slice: users.db (users table) and
acl.db (acl_rules table). Later sprints add their own seed sections
here following the same pattern — read YAML, upsert into SQLite.
"""
import argparse
import os
import sqlite3

import yaml
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_DB = os.path.join(BASE_DIR, "database", "users.db")
ACL_DB = os.path.join(BASE_DIR, "database", "acl.db")
USERS_YAML = os.path.join(BASE_DIR, "seed", "users.yaml")
ACL_YAML = os.path.join(BASE_DIR, "seed", "acl_rules.yaml")


def seed_users(reset: bool):
    os.makedirs(os.path.dirname(USERS_DB), exist_ok=True)
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()

    if reset:
        cur.execute("DROP TABLE IF EXISTS users")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            project TEXT
        )
        """
    )
    # Sprint 2: add `project` to any pre-existing users.db from Sprint 1
    # that was created before this column existed.
    existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(users)")}
    if "project" not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN project TEXT")

    with open(USERS_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for u in data.get("users", []):
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, department, project)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                role = excluded.role,
                department = excluded.department,
                project = excluded.project
            """,
            (
                u["username"],
                generate_password_hash(u["password"]),
                u["role"],
                u["department"],
                u.get("project"),
            ),
        )

    conn.commit()
    conn.close()
    print(f"[seed] users.db seeded ({len(data.get('users', []))} users)")


def seed_acl(reset: bool):
    os.makedirs(os.path.dirname(ACL_DB), exist_ok=True)
    conn = sqlite3.connect(ACL_DB)
    cur = conn.cursor()

    if reset:
        cur.execute("DROP TABLE IF EXISTS acl_rules")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS acl_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            route TEXT NOT NULL,
            UNIQUE(role, route)
        )
        """
    )

    with open(ACL_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for r in data.get("rules", []):
        cur.execute(
            "INSERT OR IGNORE INTO acl_rules (role, route) VALUES (?, ?)",
            (r["role"], r["route"]),
        )

    conn.commit()
    conn.close()
    print(f"[seed] acl.db seeded ({len(data.get('rules', []))} rules)")


def seed_reports(reset: bool):
    """Table behind the /api/search blind-SQLi target."""
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()

    if reset:
        cur.execute("DROP TABLE IF EXISTS reports")

    cur.execute(
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
    cur.executemany(
        "INSERT OR IGNORE INTO reports (id, owner, title, content, created) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (1, "j.castillo", "Q1 2026 Budget Report -- OrionBudget",
             "OrionBudget Q1 Summary\nRedis cache at redis:6379 holds session tokens.",
             "2026-03-20"),
            (2, "r.sharma", "Q1 2026 Financial Summary",
             "Q1 Financial Summary\nRevenue: $8.2M (up 12% YoY).", "2026-03-15"),
            (3, "c.lindgren", "Q1 Data Export Log -- OrionBudget",
             "Export Log -- Q1 2026\nDB connection for exports: "
             "postgresql://postgres:stillbrook_prod_2026@postgres:5432/stillbrook",
             "2026-03-20"),
        ],
    )
    conn.commit()
    conn.close()
    print("[seed] reports.db seeded (3 reports)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop and recreate tables before seeding")
    args = parser.parse_args()

    seed_users(args.reset)
    seed_acl(args.reset)
    seed_reports(args.reset)
    print("[seed] done.")
