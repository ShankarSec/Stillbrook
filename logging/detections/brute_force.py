"""
Sprint 1 detection: brute_force
Rule: 5+ failed logins from the same username within a 60-second window
      -> write an alert to logging/detections/alerts.log

Run standalone (python logging/detections/brute_force.py) or import
run_detection() from tests.
"""
import json
import os
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
AUTH_LOG = os.path.join(HERE, "..", "auth", "auth.log")
ALERTS_LOG = os.path.join(HERE, "alerts.log")

WINDOW_SECONDS = 60
THRESHOLD = 5


def _read_events(path):
    if not os.path.exists(path):
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def run_detection():
    events = _read_events(AUTH_LOG)
    failures = [e for e in events if e.get("event_type") == "login" and e.get("result") == "failure"]

    by_user = defaultdict(list)
    for e in failures:
        by_user[e["username"]].append(e["timestamp"])

    alerts = []
    for username, timestamps in by_user.items():
        timestamps.sort()
        for i in range(len(timestamps) - THRESHOLD + 1):
            window = timestamps[i : i + THRESHOLD]
            if window[-1] - window[0] <= WINDOW_SECONDS:
                alerts.append(
                    {
                        "timestamp": time.time(),
                        "rule": "brute_force",
                        "username": username,
                        "failed_attempts": THRESHOLD,
                        "window_seconds": WINDOW_SECONDS,
                        "mitre_technique": "T1110",
                    }
                )
                break  # one alert per user per run is enough

    if alerts:
        os.makedirs(HERE, exist_ok=True)
        with open(ALERTS_LOG, "a", encoding="utf-8") as f:
            for alert in alerts:
                f.write(json.dumps(alert) + "\n")

    return alerts


if __name__ == "__main__":
    fired = run_detection()
    print(f"[detections] brute_force: {len(fired)} alert(s) written")
