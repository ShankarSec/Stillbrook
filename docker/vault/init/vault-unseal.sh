#!/bin/sh
# =====================================================================
# Stillbrook -- vault-unseal helper (installed into the vault container)
#
# The three keys the player collects (Postgres / SMB share / SSH jumpbox)
# are lab-format handles:
#
#     unseal-key-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
#
# The real Shamir shares they stand for live inside the vault container in
# /vault/keys/lab_keys.env, so this helper can translate a handle into the
# share Vault actually expects and complete the unseal ceremony.
#
# Usage:
#   docker exec stillbrook-vault-host vault-unseal <lab-key> [<lab-key> ...]
#   docker exec stillbrook-vault-host vault-unseal unseal-key-.... unseal-key-....
# =====================================================================
set -eu

MAP="${VAULT_KEY_MAP:-/vault/data/keys.env}"
if [ ! -f "$MAP" ] && [ -f /vault/keys/lab_keys.env ]; then
    MAP=/vault/keys/lab_keys.env
fi
export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

if [ ! -f "$MAP" ]; then
    echo "vault-unseal: no key map at ${MAP}" >&2
    echo "vault-unseal: run the vault-init service first" >&2
    exit 1
fi

if [ "$#" -eq 0 ]; then
    echo "usage: vault-unseal <unseal-key-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX> [...]" >&2
    exit 2
fi

shares=""
for key in "$@"; do
    share=$(awk -F'|' -v want="$key" '
        { gsub(/^[ \t]+|[ \t]+$/, "", $2); gsub(/^[ \t]+|[ \t]+$/, "", $3) }
        $2 == want { print $3; exit }
    ' "$MAP")
    if [ -z "$share" ]; then
        echo "vault-unseal: unknown key: ${key}" >&2
        exit 3
    fi
    shares="${shares} ${share}"
done

for share in ${shares}; do
    vault operator unseal "$share" || true
done

vault status
