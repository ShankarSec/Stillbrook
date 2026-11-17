#!/bin/sh
# =====================================================================
# Stillbrook -- Vault initialisation (Sprint 7, Stage 8)
#
# One-shot container. It waits for the lab services, then:
#
#   1. generates the three vault unseal keys,
#   2. scatters them across the lab:
#        key 1 -> PostgreSQL  (vault_secrets.key_name = 'unseal_key_1')
#        key 2 -> SMB share   (\\samba\executive\recovery_checklist.txt)
#        key 3 -> SSH jumpbox (~/.bash_history of m.rivera)
#   3. seals the vault and unseals it again with all three keys,
#   4. stores the final flag at secret/data/final_flag.
#
# Vault itself runs inside the stillbrook-vault-host container; this
# service only drives its HTTP API and copies the unseal helper into it.
#
# Every action is appended to /vault-init/init.log.
# =====================================================================
set -eu

LOG="${LOG:-/vault-init/init.log}"
VAULT_ADDR="${VAULT_ADDR:-http://vault-host:8200}"
# VAULT_TOKEN is deliberately not inherited from Compose: vault-host
# generates its root token at runtime. It is read from that container
# after the wait_for_vault section below.
VAULT_CONTAINER="${VAULT_CONTAINER:-stillbrook-vault-host}"
JUMPBOX_CONTAINER="${JUMPBOX_CONTAINER:-stillbrook-ssh-jumpbox-1}"
SHARE_NAME="${SAMBA_SHARE_NAME:-executive}"
SHARE_DIR="${SHARE_DIR:-/volume/samba/executive}"
CHECKLIST="${CHECKLIST:-${SHARE_DIR}/recovery_checklist.txt}"
FLAG_FILE="${FLAG_FILE:-/vault-flag/final_flag.txt}"
KEY_MAP="/vault/data/keys.env"
PSQL_HOST="${PSQL_HOST:-postgres}"
PSQL_DB="${PSQL_DB:-stillbrook}"
PSQL_USER="${PSQL_USER:-postgres}"
SAMBA_SHARED_USER="${SAMBA_SHARED_USER:-admin}"
SAMBA_SHARED_PASSWORD="${SAMBA_SHARED_PASSWORD:-admin123}"

export VAULT_ADDR
export PGPASSWORD="${PGPASSWORD:-stillbrook_prod_2026}"

# --- helpers ---------------------------------------------------------------

log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "$LOG"
}

fail() {
    log "ERROR: $*"
    exit 1
}

vault_api() {   # method path [json-body]
    _m="$1"; _p="$2"; _b="${3:-}"
    if [ -n "$_b" ]; then
        curl -sS -X "$_m" \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            -H 'Content-Type: application/json' \
            --data-binary "$_b" \
            "${VAULT_ADDR}/v1/${_p}"
    else
        curl -sS -X "$_m" \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            "${VAULT_ADDR}/v1/${_p}"
    fi
}

seal_status() {
    curl -sS "${VAULT_ADDR}/v1/sys/seal-status"
}

psql_q() {   # sql
    psql -h "$PSQL_HOST" -U "$PSQL_USER" -d "$PSQL_DB" \
        -v ON_ERROR_STOP=1 -t -A -c "$1"
}

gen_key() {  # -> unseal-key-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    _h=$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')
    printf 'unseal-key-%s-%s-%s-%s-%s-%s\n' \
        "$(printf '%s' "$_h" | cut -c1-4)"  "$(printf '%s' "$_h" | cut -c5-8)" \
        "$(printf '%s' "$_h" | cut -c9-12)" "$(printf '%s' "$_h" | cut -c13-16)" \
        "$(printf '%s' "$_h" | cut -c17-20)" "$(printf '%s' "$_h" | cut -c21-24)"
}

wait_for_vault() {
    _i=0
    while [ "$_i" -lt 60 ]; do
        if curl -sS -o /dev/null "${VAULT_ADDR}/v1/sys/health" 2>/dev/null; then
            return 0
        fi
        _i=$((_i + 1))
        sleep 2
    done
    return 1
}

wait_for_postgres() {
    _i=0
    while [ "$_i" -lt 60 ]; do
        if pg_isready -h "$PSQL_HOST" -U "$PSQL_USER" >/dev/null 2>&1; then
            return 0
        fi
        _i=$((_i + 1))
        sleep 2
    done
    return 1
}

resolve_container() {   # preferred-name name-filter
    if docker inspect "$1" >/dev/null 2>&1; then
        printf '%s\n' "$1"
        return 0
    fi
    docker ps -a --filter "name=$2" --format '{{.Names}}' | head -1
}

# --- start -----------------------------------------------------------------

log "======================================================================"
log "Stillbrook vault-init starting (pid $$)"
log "vault=${VAULT_ADDR} vault_container=${VAULT_CONTAINER} jumpbox=${JUMPBOX_CONTAINER}"

[ -f "$FLAG_FILE" ] || fail "final flag file ${FLAG_FILE} is missing"

# --- 1. wait for the lab ---------------------------------------------------

log "waiting for vault ..."
wait_for_vault || fail "vault did not become reachable at ${VAULT_ADDR}"
log "waiting for postgres ..."
wait_for_postgres || fail "postgres did not become reachable at ${PSQL_HOST}"

VAULT_CONTAINER=$(resolve_container "$VAULT_CONTAINER" stillbrook-vault-host)
JUMPBOX_CONTAINER=$(resolve_container "$JUMPBOX_CONTAINER" ssh-jumpbox)
[ -n "$VAULT_CONTAINER" ] || fail "vault container not found"
[ -n "$JUMPBOX_CONTAINER" ] || fail "ssh-jumpbox container not found"
log "containers: vault=${VAULT_CONTAINER} jumpbox=${JUMPBOX_CONTAINER}"

# vault-init is a separate container: read the token that vault-host
# generated at runtime rather than expecting it in our own environment.
VAULT_TOKEN=$(docker exec "$VAULT_CONTAINER" printenv VAULT_TOKEN 2>/dev/null || true)
if [ -z "$VAULT_TOKEN" ]; then
    # `docker exec` uses the container's original config env, not the
    # variables exported by its entrypoint shell. The entrypoint also
    # writes the token to this root-only file for exactly this case.
    VAULT_TOKEN=$(docker exec "$VAULT_CONTAINER" cat /vault/.vault_token 2>/dev/null || true)
fi
[ -n "$VAULT_TOKEN" ] || fail "could not read VAULT_TOKEN from ${VAULT_CONTAINER}"
export VAULT_TOKEN
log "vault token read from ${VAULT_CONTAINER}"

# --- 2. generate the three unseal keys -------------------------------------

KEY1=$(gen_key)
KEY2=$(gen_key)
KEY3=$(gen_key)
log "generated 3 unseal keys (values written to their artifact locations only)"

# --- 3. work out which shares the vault currently accepts ------------------

STATUS=$(seal_status)
SHARES_TOTAL=$(printf '%s' "$STATUS" | jq -r '.n')
THRESHOLD=$(printf '%s' "$STATUS" | jq -r '.t')
log "vault seal status: ${SHARES_TOTAL} shares, threshold ${THRESHOLD}"

CURRENT_SHARES=""
if [ "$THRESHOLD" = "1" ]; then
    # Fresh dev-mode server: the boot share is printed once in the
    # root-only startup file (never in `docker logs`).
    DEV_SHARE=$(docker exec "$VAULT_CONTAINER" \
        sh -c 'grep -m1 "^Unseal Key:" /vault/dev-bootstrap.log 2>/dev/null' \
        2>/dev/null | awk '{print $3}')
    [ -n "$DEV_SHARE" ] || fail "could not read the dev-mode unseal key from ${VAULT_CONTAINER}"
    CURRENT_SHARES="$DEV_SHARE"
    log "using the dev-mode boot share to authorise the rekey"
else
    # Already rekeyed by an earlier run: reuse the shares stashed in the
    # vault container.
    MAP=$(docker exec "$VAULT_CONTAINER" cat "$KEY_MAP" 2>/dev/null || true)
    if [ -n "$MAP" ]; then
        CURRENT_SHARES=$(printf '%s\n' "$MAP" | awk -F'|' \
            '{ gsub(/^[ \t]+|[ \t]+$/, "", $3); print $3 }')
    fi
    [ -n "$CURRENT_SHARES" ] || fail "vault already uses ${THRESHOLD} shares but no key map was found in ${VAULT_CONTAINER}"
    log "using the shares stashed by a previous run to authorise the rekey"
fi

# --- 4. rekey the vault to a real 3-of-3 Shamir quorum ---------------------

log "rekeying vault to 3 shares / threshold 3 ..."
NONCE=$(vault_api POST sys/rekey/init '{"secret_shares":3,"secret_threshold":3}' \
    | jq -r '.nonce // empty')
[ -n "$NONCE" ] || fail "could not start the rekey"

REKEY_OUT=""
for share in $CURRENT_SHARES; do
    BODY=$(jq -nc --arg n "$NONCE" --arg k "$share" '{nonce:$n,key:$k}')
    REKEY_OUT=$(vault_api PUT sys/rekey/update "$BODY")
    if printf '%s' "$REKEY_OUT" | jq -e '.errors' >/dev/null 2>&1; then
        vault_api POST sys/rekey/cancel "{\"nonce\":\"${NONCE}\"}" >/dev/null 2>&1 || true
        fail "rekey failed: $(printf '%s' "$REKEY_OUT" | jq -c '.errors')"
    fi
    if printf '%s' "$REKEY_OUT" | jq -e '.complete == true' >/dev/null 2>&1; then
        break
    fi
done

NEW_SHARES=$(printf '%s' "$REKEY_OUT" | jq -r '.keys_base64[]?')
COUNT=$(printf '%s\n' "$NEW_SHARES" | grep -c '.')
[ "$COUNT" = "3" ] || fail "rekey returned ${COUNT} shares, expected 3"

set -- $NEW_SHARES
S1="$1"; S2="$2"; S3="$3"
log "vault now uses a 3-of-3 Shamir quorum"

# --- 5. install the key map + the vault-unseal helper -----------------------

log "installing the key map and vault-unseal helper into ${VAULT_CONTAINER} ..."
docker exec "$VAULT_CONTAINER" mkdir -p "$(dirname "${KEY_MAP}")"
{
    printf 'unseal_key_1 | %s | %s\n' "$KEY1" "$S1"
    printf 'unseal_key_2 | %s | %s\n' "$KEY2" "$S2"
    printf 'unseal_key_3 | %s | %s\n' "$KEY3" "$S3"
} > /tmp/lab_keys.env
docker cp /tmp/lab_keys.env "${VAULT_CONTAINER}:${KEY_MAP}"
docker exec "$VAULT_CONTAINER" chmod 0600 "${KEY_MAP}"
docker cp /vault-init/vault-unseal.sh "${VAULT_CONTAINER}:/usr/local/bin/vault-unseal"
docker exec "$VAULT_CONTAINER" chmod 0755 /usr/local/bin/vault-unseal
log "key map installed at ${KEY_MAP} (container-local, not published)"

# --- 6. scatter the keys ---------------------------------------------------

# key 1 -> PostgreSQL
log "storing unseal key 1 in postgres (vault_secrets.key_name='unseal_key_1') ..."
psql_q "ALTER TABLE vault_secrets ADD COLUMN IF NOT EXISTS key_name TEXT;" >/dev/null
psql_q "ALTER TABLE vault_secrets ADD COLUMN IF NOT EXISTS key_value TEXT;" >/dev/null
psql_q "DELETE FROM vault_secrets WHERE key_name = 'unseal_key_1';" >/dev/null
psql_q "INSERT INTO vault_secrets (key_name, key_value) VALUES ('unseal_key_1', '${KEY1}');" >/dev/null
# keep the rows seeded by docker/db/init.sql consistent with the real keys
psql_q "UPDATE vault_secrets SET unseal_key = '${KEY1}', location_hint = 'Found in PostgreSQL vault_secrets table' WHERE secret_name = 'vault_unseal_key_1';" >/dev/null
psql_q "UPDATE vault_secrets SET unseal_key = NULL WHERE secret_name IN ('vault_unseal_key_2', 'vault_unseal_key_3');" >/dev/null
# the token the player needs to read the flag
psql_q "INSERT INTO service_config (key, value) VALUES ('vault_token', '${VAULT_TOKEN}') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;" >/dev/null
log "unseal key 1 stored in postgres"

# key 2 -> executive SMB share
log "writing unseal key 2 into the executive SMB share ..."
if [ ! -f "$CHECKLIST" ]; then
    # The live checklist is generated at runtime from the tracked template
    # and is intentionally NOT part of the public repository.
    if [ -f "${CHECKLIST}.example" ]; then
        cp "${CHECKLIST}.example" "$CHECKLIST"
    else
        printf '  Vault unseal key 2: __UNSEAL_KEY_2__\n' > "$CHECKLIST"
    fi
fi
if grep -q '__UNSEAL_KEY_2__' "$CHECKLIST"; then
    sed -i "s|__UNSEAL_KEY_2__|${KEY2}|g" "$CHECKLIST"
elif grep -qi 'vault unseal key 2:' "$CHECKLIST"; then
    sed -i "s|^\(.*[Vv]ault unseal key 2:\).*|\1 ${KEY2}|" "$CHECKLIST"
else
    printf '  Vault unseal key 2: %s\n' "$KEY2" >> "$CHECKLIST"
fi
log "unseal key 2 written to ${CHECKLIST}"

# key 3 -> SSH jumpbox shell history
log "appending unseal key 3 to ${JUMPBOX_CONTAINER}:/home/m.rivera/.bash_history ..."
docker exec "$JUMPBOX_CONTAINER" sh -c \
    "sed -i '/^# unseal key 3:/d' /home/m.rivera/.bash_history" >/dev/null 2>&1 || true
docker exec "$JUMPBOX_CONTAINER" sh -c \
    "echo '# unseal key 3: ${KEY3}' >> /home/m.rivera/.bash_history"
log "unseal key 3 appended to the jumpbox history"

# --- 7. seal + unseal ceremony ---------------------------------------------

log "sealing the vault ..."
vault_api POST sys/seal >/dev/null 2>&1 || true
sleep 2
log "vault sealed: $(seal_status | jq -r '.sealed')"

log "unsealing with all 3 keys ..."
for share in "$S1" "$S2" "$S3"; do
    vault operator unseal "$share" >/dev/null 2>&1 || true
done
SEALED=$(seal_status | jq -r '.sealed')
[ "$SEALED" = "false" ] || fail "vault is still sealed after the unseal ceremony"
log "vault unsealed (sealed=${SEALED})"

# --- 8. the final flag -----------------------------------------------------

log "enabling the kv-v2 secrets engine at secret/ ..."
vault secrets disable secret/ >/dev/null 2>&1 || true
vault secrets enable -path=secret kv-v2 >/dev/null

log "storing the final flag at secret/data/final_flag ..."
vault kv put secret/final_flag value="@${FLAG_FILE}" >/dev/null

READBACK=$(vault kv get -field=value secret/final_flag 2>/dev/null || true)
printf '%s' "$READBACK" | grep -q 'stillbrook{' \
    || fail "could not read the flag back from secret/data/final_flag"
log "final flag stored and verified in secret/data/final_flag"

# --- 9. sanity checks ------------------------------------------------------

if command -v smbclient >/dev/null 2>&1; then
    _i=0
    while [ "$_i" -lt 10 ]; do
        if smbclient "//samba/${SHARE_NAME}" \
            -U "${SAMBA_SHARED_USER}%${SAMBA_SHARED_PASSWORD}" \
            -c "get recovery_checklist.txt /tmp/rc.txt" >/dev/null 2>&1; then
            break
        fi
        _i=$((_i + 1))
        sleep 2
    done
    if [ "$_i" -lt 10 ]; then
        if grep -q 'Vault unseal key 2:' /tmp/rc.txt 2>/dev/null; then
            log "SMB share reachable over the network, recovery_checklist.txt serves unseal key 2"
        else
            log "WARNING: SMB share reachable but the checklist does not carry unseal key 2"
        fi
    else
        log "WARNING: could not reach //samba/${SHARE_NAME} over SMB"
    fi
fi

log "======================================================================"
log "Stillbrook vault-init finished successfully"
exit 0
