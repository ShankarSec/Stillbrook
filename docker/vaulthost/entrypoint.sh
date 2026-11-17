#!/bin/bash
set -e

# --- runtime SSH keys ---------------------------------------------------
# Generate the router<->vault-host keypair on every fresh run into the
# shared volume. The router entrypoint copies the private key from there.
# Also generate a fresh SSH host key so no private key is ever committed.
mkdir -p /shared
if [ ! -s /shared/id_rsa ]; then
    rm -f /shared/id_rsa /shared/id_rsa.pub
    ssh-keygen -t rsa -b 2048 -f /shared/id_rsa -N "" \
        -C "internal-router -> vault-host" >/dev/null 2>&1
fi
chmod 0600 /shared/id_rsa
chmod 0644 /shared/id_rsa.pub 2>/dev/null || true
cp /shared/id_rsa.pub /home/vault_svc/.ssh/authorized_keys
chown vault_svc:vault_svc /home/vault_svc/.ssh/authorized_keys
chmod 0600 /home/vault_svc/.ssh/authorized_keys

rm -f /etc/ssh/ssh_host_ed25519_key /etc/ssh/ssh_host_ed25519_key.pub
ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N "" \
    -C "vault-host host key" >/dev/null 2>&1
chown root:root /etc/ssh/ssh_host_ed25519_key
chmod 0600 /etc/ssh/ssh_host_ed25519_key

# The Vault root token is generated fresh on every container start.
TOKEN=$(cat /proc/sys/kernel/random/uuid | tr -d "-" | head -c 24)
export VAULT_DEV_ROOT_TOKEN_ID="$TOKEN"
export VAULT_TOKEN="$TOKEN"
export VAULT_ADDR="http://127.0.0.1:8200"

# cron and separate `docker exec` sessions do not inherit this shell's
# environment, so publish the token as a root-only file as well.
echo "$TOKEN" > /vault/.vault_token
chmod 0600 /vault/.vault_token

# --- faked /proc/version -------------------------------------------------
# /etc/rc.local writes the string the lab wants to see, the wrapper in
# /usr/local/bin/proc-version is what surfaces it (a bind mount over
# /proc/version is attempted first and only works with extra privileges).
sh /etc/rc.local || true
if [ -s /var/run/proc-version ]; then
    mount --bind /var/run/proc-version /proc/version 2>/dev/null || true
fi

# --- vector B: /etc/shadow is immutable -------------------------------
# The container is started with CAP_LINUX_IMMUTABLE (see docker-compose),
# so the flag actually sticks. This has to happen at runtime: the build
# sandbox cannot set file attributes on its overlayfs.
chattr +i /etc/shadow 2>/dev/null || true

# --- cron: rotates the vault material every 5 minutes as root ---------
cron

# --- sshd (port 2224) ---------------------------------------------------
mkdir -p /run/sshd
/usr/sbin/sshd

# --- vault dev server (port 8200) --------------------------------------
# Dev mode prints the bootstrap unseal key and root token to stdout. Keep
# those out of `docker logs` by writing the startup banner to a root-only
# file; the one-shot vault-init service reads the bootstrap share from
# there via `docker exec` instead of from the public container log.
BOOTSTRAP_LOG=/vault/dev-bootstrap.log
: > "$BOOTSTRAP_LOG"
chmod 0600 "$BOOTSTRAP_LOG"
vault server -dev -dev-listen-address=0.0.0.0:8200 > "$BOOTSTRAP_LOG" 2>&1 &
VAULT_PID=$!

# Wait for the API to answer, but never block longer than 30 seconds.
for _ in $(seq 1 30); do
    if curl -sS -o /dev/null "${VAULT_ADDR}/v1/sys/health" 2>/dev/null; then
        break
    fi
    sleep 1
done

# Dev mode drops the root token in /root/.vault-token. Remove it so a
# plain `docker exec ... vault read` cannot read secrets without first
# supplying the token (which lives in Postgres / /vault/.vault_token).
rm -f /root/.vault-token

wait $VAULT_PID
