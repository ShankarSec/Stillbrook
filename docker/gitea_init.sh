#!/bin/sh
set -e

for i in $(seq 1 30); do
  curl -sf http://gitea:3000/api/healthz >/dev/null 2>&1 && break
  sleep 2
done

curl -sf -X POST http://gitea:3000/api/v1/orgs \
  -H "Content-Type: application/json" \
  -u "m.rivera:${GITEA_PASS}" \
  -d '{"username":"stillbrook"}' 2>/dev/null || true

curl -sf -X POST http://gitea:3000/api/v1/orgs/stillbrook/repos \
  -H "Content-Type: application/json" \
  -u "m.rivera:${GITEA_PASS}" \
  -d '{"name":"web","auto_init":false}' 2>/dev/null || true

cd /repos
git push "http://m.rivera:Rivera%232026@gitea:3000/stillbrook/web.git" master 2>/dev/null || true

echo "gitea-init: done"   
