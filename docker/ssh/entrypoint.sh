#!/bin/sh
# =====================================================================
# Stillbrook -- SSH jumpbox entrypoint
#
#   sshd   -> port 2222 (m.rivera / backupadmin)
#   dante  -> port 1080 (SOCKS5, lab clients -> internal network)
#   :8082  -> decommissioned chisel tunnel decoy (30s timeout)
# =====================================================================
set -e

# /etc/hosts is managed by Docker, so the router alias has to be added
# at runtime rather than baked into the image.
if ! grep -qs '^172\.28\.0\.10[[:space:]]\+internal-router' /etc/hosts; then
    printf '172.28.0.10 internal-router\n' >> /etc/hosts
fi

# SOCKS5 proxy for the internal network (Alpine's sockd stays in the
# foreground, so background it explicitly).
sockd -f /etc/dante/dante.conf >/dev/null 2>&1 &

# "Decommissioned" chisel tunnel: the port still answers, but every
# connection hangs for 30s and then drops, just like a dead relay.
socat TCP-LISTEN:8082,reuseaddr,fork EXEC:"sleep 30" >/dev/null 2>&1 &

mkdir -p /run/sshd
exec /usr/sbin/sshd -D -p 2222
