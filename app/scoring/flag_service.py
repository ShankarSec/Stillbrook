"""
Flag delivery: plain read of story/private_flags/<username>.txt,
returned ONLY for the currently authenticated session's own username.

This intentionally does not take a username parameter from the caller --
get_flag_for_session() always resolves the flag for session['username'],
so there is no way to pass someone else's username in and get their flag
back. The story blueprint independently blocks private_flags/ at the
route level too (belt-and-suspenders), so even a direct path guess
against /story/private_flags/<user>.txt is refused regardless of this
module.

NOTE: this directory was renamed from flag_texts/ to private_flags/ in
a later content pass. If you rename it again, grep for both this
constant AND app/story/__init__.py's HIDDEN_FROM_INDEX / file() guard --
they must always point at the same directory name, or flag delivery
silently breaks with no error (os.path.exists just returns False and
the dashboard shows no flag, no exception raised).

Sprint 10 upgrades this to HMAC-SHA256 per-player tokens wrapped in
AES-encrypted narrative artifacts, keyed to stage-specific discovered
facts. This module's call signature (get_flag_for_session) stays the
same so callers don't need to change when that lands.
"""
import os

from flask import session

STORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "story")
FLAG_TEXTS_DIR = os.path.join(STORY_DIR, "private_flags")


def get_flag_for_session() -> str | None:
    username = session.get("username")
    if not username:
        return None

    # username comes from the authenticated session (set at login from the
    # users table), never from user-supplied input, so no path traversal
    # risk here -- but we still normalize defensively.
    safe_name = os.path.basename(username)
    flag_path = os.path.join(FLAG_TEXTS_DIR, f"{safe_name}.txt")

    if not os.path.exists(flag_path):
        return None

    with open(flag_path, "r", encoding="utf-8") as f:
        return f.read().strip()
