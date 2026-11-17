#!/bin/sh
# =====================================================================
# Stillbrook -- internal router entrypoint
#
#   sshd    -> port 2223 (svc_router / Phoenix_DR#2026)
#   chisel  -> port 8081 (tunnel server, auth svc_router:Phoenix_DR#2026)
#   cron    -> runs /opt/scripts/healthcheck.sh every 5 minutes
# =====================================================================
set -e

# The vault host lives on the same internal network. /etc/hosts is a
# bind mount at runtime, so the mapping is (re)written here instead of
# being baked into the image.
if ! grep -qs '^172\.28\.0\.20[[:space:]]\+vault-host' /etc/hosts; then
    printf '172.28.0.20 vault-host\n' >> /etc/hosts
fi

# Pick up the router->vault-host SSH key generated at runtime by the
# vault-host entrypoint into the shared volume. The vault host and this
# container start concurrently, so wait briefly for the key to appear.
_i=0
while [ ! -s /shared/id_rsa ] && [ "$_i" -lt 60 ]; do
    sleep 1
    _i=$((_i + 1))
done
if [ -s /shared/id_rsa ]; then
    cp /shared/id_rsa /home/svc_router/.ssh/id_rsa
    chown svc_router:svc_router /home/svc_router/.ssh/id_rsa
    chmod 0600 /home/svc_router/.ssh/id_rsa
else
    echo "router-entrypoint: WARNING - /shared/id_rsa not available; vault-host hop will fail" >&2
fi

# cron: the healthcheck probe runs every 5 minutes as root
cron

# sshd (port 2223)
mkdir -p /run/sshd
/usr/sbin/sshd

# chisel tunnel server (port 8081) -- runs unprivileged as svc_router.
# The authfile pins the account to a single permitted remote target:
# vault-host:2224. Other forwards are refused by chisel itself.
exec su -s /bin/sh svc_router -c \
    "exec chisel server --host 0.0.0.0 --port 8081 --reverse --authfile /home/svc_router/users.json"
