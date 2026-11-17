"""
Structured, append-only logging into the logging/ tree.
One JSON line per event — this is what tests/test_logging.py and the
detection scripts in logging/detections/ both read.
"""
import json
import os
import time

LOG_ROOT = os.path.join(os.path.dirname(__file__), "..", "logging")


def _write(stream: str, event: dict):
    stream_dir = os.path.join(LOG_ROOT, stream)
    os.makedirs(stream_dir, exist_ok=True)
    log_path = os.path.join(stream_dir, f"{stream}.log")
    event = {"timestamp": time.time(), **event}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def log_auth_event(
    event_type: str,
    username: str,
    ip: str,
    result: str,
    user_agent: str = ""
):
    """event_type: login | logout | register | password_reset
    result: success | failure"""
    _write(
        "auth",
{
    "event_id": f"AUTH_{event_type.upper()}",
    "event_type": event_type,
    "username": username,
    "ip": ip,
    "user_agent": user_agent,
    "result": result,
}
    )

def log_web_event(
    route: str,
    method: str,
    user: str,
    status: int,
    ip: str = "",
):
    _write(
        "web",
{
    "event_id": "WEB_REQUEST",
    "route": route,
    "method": method,
    "user": user,
    "ip": ip,
    "status": status,
},
    )
