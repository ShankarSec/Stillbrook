"""Tiny SQLite helper shared across app modules. No ORM — kept deliberately
simple so later stages can introduce intentional query-building bugs
(e.g. SQLi) without fighting an ORM abstraction."""
import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def get_acl_db():
    if "acl_db" not in g:
        g.acl_db = sqlite3.connect(current_app.config["ACL_DB_PATH"])
        g.acl_db.row_factory = sqlite3.Row
    return g.acl_db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
    acl_db = g.pop("acl_db", None)
    if acl_db is not None:
        acl_db.close()
