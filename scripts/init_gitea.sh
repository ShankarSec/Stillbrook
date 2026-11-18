#!/bin/bash
# Seed the Gitea organisation/repository and push the synthetic challenge
# repo whose history contains the planted NetNTLMv2 artifact and leaked .env.
set -e
cd "$(dirname "$0")/.."

# Prefer the value from .env (docker compose does not export it into this
# host-side script). Fall back to the documented example value.
GITEA_PASS="${GITEA_PASS:-CHANGE_ME}"
ENC_PASS=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$GITEA_PASS")

echo "Waiting for Gitea..."
for i in $(seq 1 30); do
  docker compose exec -T gitea curl -sf http://localhost:3000/api/healthz >/dev/null 2>&1 && break
  sleep 2
done

docker compose exec -T gitea gitea admin user create \
  --username m.rivera --password "$GITEA_PASS" \
  --email m.rivera@stillbrook.com --admin 2>/dev/null || true

docker compose exec -T gitea curl -sf -X POST http://localhost:3000/api/v1/orgs \
  -H "Content-Type: application/json" \
  -u "m.rivera:${GITEA_PASS}" \
  -d '{"username":"stillbrook"}' 2>/dev/null || true

docker compose exec -T gitea curl -sf -X POST http://localhost:3000/api/v1/orgs/stillbrook/repos \
  -H "Content-Type: application/json" \
  -u "m.rivera:${GITEA_PASS}" \
  -d '{"name":"web","auto_init":false}' 2>/dev/null || true

# Copy the synthetic repository content into the Gitea container, then
# build a real Git history there:
#   commit 1: app/config/secrets + an accidentally committed .env
#   commit 2: .env removed from the tree (still recoverable from history)
docker cp docker/git/repo stillbrook-gitea-1:/tmp/web

docker compose exec -T gitea sh -c '
  cd /tmp/web
  git init -q
  git config user.email "m.rivera@stillbrook.com"
  git config user.name "Maria Rivera"
  cat > .env <<EOF
# Stillbrook Web App -- Environment (accidentally committed)
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=stillbrook_prod_2026
DB_NAME=stillbrook
REDIS_HOST=redis
REDIS_PORT=6379
VAULT_ADDR=http://vault:8200
VAULT_UNSEAL_KEY_1=unseal-key-AAAA-BBBB-CCCC-DDDD-EEEE-1111
SSH_JUMPBOX_HOST=ssh-jumpbox
SSH_JUMPBOX_PORT=2222
SSH_JUMPBOX_USER=m.rivera
EOF
  git add -A
  git commit -qm "Initial commit"
  git rm -q .env
  git commit -qm "Remove committed environment file"
'

# Retry the push briefly in case Gitea is still finishing initialisation.
ok=0
for i in $(seq 1 10); do
  if docker compose exec -T gitea sh -c \
      "cd /tmp/web && git push -f 'http://m.rivera:${ENC_PASS}@localhost:3000/stillbrook/web.git' master" \
      >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done
if [ "$ok" -ne 1 ]; then
  echo "gitea-init: WARNING - could not push challenge repo" >&2
else
  echo "gitea-init: challenge repository pushed"
fi

echo "gitea-init: done"
