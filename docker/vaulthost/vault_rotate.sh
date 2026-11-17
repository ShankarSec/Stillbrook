#!/bin/sh
# =====================================================================
# Stillbrook -- vault key rotation (runs as root every 5 minutes)
#
# The script is deliberately world writable (0666): it is one of the
# escalation paths a player is expected to abuse to reach /root.
# =====================================================================
set -u

DATA_DIR=/vault/data
KEYS="${DATA_DIR}/keys.env"

# cron does not hand the daemon environment down to the job, so the
# client side defaults are repeated here.
export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_TOKEN="$(cat /vault/.vault_token)"

mkdir -p "${DATA_DIR}" 2>/dev/null || true

# keep a timestamped copy of the last rotation
date -u '+%Y-%m-%dT%H:%M:%SZ' > "${DATA_DIR}/last_rotate.txt" 2>/dev/null || true

# snapshot the current key material
if [ -r "${KEYS}" ]; then
    cp "${KEYS}" "${DATA_DIR}/keys.env.bak" 2>/dev/null || true
    chmod 0600 "${DATA_DIR}/keys.env.bak" 2>/dev/null || true
    cp /vault/data/keys.env /tmp/keys_backup.env 2>/dev/null || true
fi

# record the seal status of the dev server
/usr/local/bin/vault status > "${DATA_DIR}/vault_status.txt" 2>&1 || true

# NOTE: no "exit 0" at the end -- anything a player appends to this
# world writable script has to run when cron picks it up.
