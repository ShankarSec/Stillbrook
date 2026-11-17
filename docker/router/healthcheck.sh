#!/bin/sh
# Stillbrook -- internal router health probe.
#
# Deliberately world writable (0666): the lab expects a player to be
# able to tamper with it.  Cron runs it every 5 minutes as root.
echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] internal-router uptime: $(uptime -p 2>/dev/null || uptime)" \
    >> /var/log/healthcheck.log 2>/dev/null || true
