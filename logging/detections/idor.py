"""
Detection rule: IDOR on Finance module.
Triggers when a user accesses 2+ reports they don't own.

NOTE: this module must only ever be imported via app/detection_loader.py
(importlib by file path), never as `from logging.detections.idor import
...` from inside application code -- that import shadows Python's
stdlib `logging` module process-wide. See app/detection_loader.py's
docstring for the full explanation. A standalone test file importing
this directly is lower-risk (short-lived process, not the live app),
but app/detection_loader.py is still the safe path even there.
"""
import time
from collections import defaultdict

# Track: username -> set of report_ids accessed
_idor_events = defaultdict(set)
_idor_threshold = 2  # Alert after accessing 2+ non-owned reports

HERE = __file__


def check_idor(username: str, role: str, report_id: int, report_owner: str) -> bool:
    """Returns True if this access should trigger an IDOR alert."""
    # finance_manager can view all -- no alert
    if role == "finance_manager":
        return False

    # If the report belongs to the user -- no alert
    if report_owner == username:
        return False

    # Track non-owned accesses
    _idor_events[username].add(report_id)

    if len(_idor_events[username]) >= _idor_threshold:
        _log_alert(username, report_id, report_owner)
        return True

    return False


def _log_alert(username: str, report_id: int, report_owner: str):
    """Write to detection log."""
    import os
    import json

    log_dir = os.path.dirname(os.path.abspath(HERE))
    os.makedirs(log_dir, exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rule": "IDOR_FINANCE_REPORT",
        "severity": "HIGH",
        "mitre_technique": "T1213",  # Data from Information Repositories
        "username": username,
        "accessed_report": report_id,
        "report_owner": report_owner,
        "total_non_owned_accesses": len(_idor_events[username]),
    }
    with open(os.path.join(log_dir, "idor.log"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def reset():
    """Reset detection state (for testing)."""
    _idor_events.clear()
