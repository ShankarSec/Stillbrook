# Logging and Detection Model

## Format

Application events are newline-delimited JSON (one event per line), written
by `app/logging_utils.py`. Log files are generated at runtime and are
git-ignored; `scripts/reset_lab.sh` clears them on reset.

## Streams

- `logging/auth/auth.log` — login/logout/register/password-reset events.
  Fields: `timestamp, event_type, username, ip, result`.
- `logging/web/web.log` — generic route-access events.
  Fields: `timestamp, route, method, user, status`.
- `logging/detections/alerts.log` — detection alerts appended by the
  detection modules.
- nginx keeps its own access/error logs inside the web container; these are
  not written into the repository.

The dashboard's "Recent activity" widget reads `logging/auth/auth.log`
directly and filters to the authenticated user's own events.

## Detections

Detection rules live in `logging/detections/`:

- `brute_force.py` — flags 5+ failed logins for one username within 60 s
  (MITRE T1110).
- `idor.py` — flags repeated object-reference access patterns.

Each module appends alerts to `logging/detections/alerts.log`.

## Blue-team view

The dashboard reconstructs activity from the same log files; there is no
separate storage layer. `app/story` provides role-gated access to the
fictional log artefacts under `story/logs/` (auth, backup, DR and VPN logs),
which are narrative training data, not the application's live logs.

## Testing status

Earlier notes referenced `tests/test_logging.py`, `tests/test_detections.py`
and `app/operations/monitoring.py`. None of those files exist in this
repository. Verification is instead performed by the functional checks in
`scripts/reset_lab.sh` and the audit reports under `AUDIT_REPORT/`. Detection
effectiveness should be validated against representative benign and
malicious activity before being claimed.
