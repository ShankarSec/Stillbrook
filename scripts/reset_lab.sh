#!/bin/bash
# Full lab reset: rebuild every container from scratch, re-seed the
# databases, re-run the one-shot vault-init (which regenerates all three
# unseal keys and re-stores the final flag), then verify the whole stack.
set -e
cd "$(dirname "$0")/.."

echo "[1/6] Stopping ALL containers + removing volumes (including orphans)..."
# -v drops pgdata / gitea_data / jumpbox_home, so every service starts
# from scratch. --remove-orphans clears stale containers from older
# Compose configs (the Gitea port leak fix).
docker compose down -v --remove-orphans --timeout 30

# Safety net for stacks created under a different project name.
for v in stillbrook_gitea_data stillbrook_pgdata stillbrook_jumpbox_home; do
  docker volume rm "$v" 2>/dev/null || true
done

echo "[2/6] Re-seeding local SQLite DBs + clearing detection logs..."
python3 seed/seed_db.py --reset
rm -f logging/auth/auth.log logging/web/web.log logging/detections/alerts.log
# vaulthost/privesc artifacts may have been modified by a player.
rm -f docker/vault/init/init.log

echo "[3/6] Starting fresh (all services)..."
# --build guarantees the stack runs the current source, not stale images
# left over from an earlier build (a common cause of false reset results).
docker compose up -d --build

echo "[4/6] Initialising Gitea repository (NTLM hash artifact)..."
./scripts/init_gitea.sh

echo "[5/6] Running vault-init (regenerates all keys + final flag)..."
INIT_STATE=""
for _ in $(seq 1 90); do
  INIT_STATE=$(docker inspect -f '{{.State.Status}}:{{.State.ExitCode}}' \
    stillbrook-vault-init 2>/dev/null || echo "missing")
  case "$INIT_STATE" in
    exited:0) break ;;
    exited:*) echo "  vault-init failed (${INIT_STATE})"; \
               docker compose logs --tail=40 vault-init; exit 1 ;;
  esac
  sleep 2
done
if [ "$INIT_STATE" != "exited:0" ]; then
  echo "  vault-init did not finish in time (${INIT_STATE})"
  docker compose logs --tail=40 vault-init
  exit 1
fi
echo "  vault-init finished -- unseal keys regenerated"

echo "[6/6] Verifying..."
PASS=0
FAIL=0
check() {
  if eval "$2" >/dev/null 2>&1; then
    echo "  ✅ $1"; PASS=$((PASS+1))
  else
    echo "  ❌ $1"; FAIL=$((FAIL+1))
  fi
}

check "all containers up" "[ \$(docker compose ps --status running -q | wc -l) -ge 9 ]"
check "web :80" "curl -sf -o /dev/null http://127.0.0.1:80/"
check "Redis" "docker compose exec -T web redis-cli -h redis ping | grep -q PONG"
check "Postgres (6 users)" "[ \"\$(docker compose exec -T postgres psql -U postgres -d stillbrook -t -A -c 'SELECT count(*) FROM users;')\" = 6 ]"
check "Gitea repo" "docker compose exec -T gitea git ls-remote http://gitea:3000/stillbrook/web.git | grep -q refs/heads"
check "ssh-jumpbox (key 3)" "docker exec stillbrook-ssh-jumpbox-1 grep -q '# unseal key 3: unseal-key-' /home/m.rivera/.bash_history"
check "vsftpd backdoor" "docker exec stillbrook-vsftpd pgrep -f vsftpd >/dev/null"
check "internal-router" "docker exec stillbrook-internal-router pgrep -f chisel >/dev/null"
check "vault unsealed" "docker exec stillbrook-vault-host vault status | grep -q 'Sealed *false'"
check "vault final flag" "docker exec stillbrook-vault-host sh -c 'export VAULT_TOKEN=\$(cat /vault/.vault_token 2>/dev/null); vault kv get -field=value secret/final_flag 2>/dev/null' | grep -q stillbrook"
check "unseal key 1 (postgres)" "docker compose exec -T postgres psql -U postgres -d stillbrook -t -A -c \"SELECT key_value FROM vault_secrets WHERE key_name = 'unseal_key_1';\" | grep -q '^unseal-key-'"
check "unseal key 2 (samba share)" "grep -q 'Vault unseal key 2: unseal-key-' docker/samba/share/recovery_checklist.txt"
check "SUID helper" "docker exec stillbrook-vault-host test -u /usr/local/bin/vault-reader"
check "immutable /etc/shadow" "docker exec stillbrook-vault-host lsattr /etc/shadow | grep -q -- '----i'"
check "world-writable cron script" "docker exec stillbrook-vault-host test \\( -w /opt/scripts/vault_rotate.sh -a ! -x /opt/scripts/vault_rotate.sh \\)"

echo ""
echo "Result: $PASS/$(($PASS+$FAIL)) passed"
echo ""
echo "Unseal keys were regenerated. Retrieve them from:"
echo "  key 1 -> postgres  : SELECT key_value FROM vault_secrets WHERE key_name = 'unseal_key_1';"
echo "  key 2 -> samba     : \\\\samba\\executive\\recovery_checklist.txt"
echo "  key 3 -> jumpbox   : cat ~/.bash_history (as m.rivera)"
echo ""
[ $FAIL -eq 0 ] && echo "Reset complete." || { echo "⚠️  $FAIL check(s) failed — investigate before use."; exit 1; }
