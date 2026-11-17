#!/bin/sh
# UNVERIFIED -- not run against a live Redis instance (no Docker in the
# build environment). Review before trusting it runs as written.
redis-cli SET "session:admin_api_key" "sbk-admin-7f3a9c2e1d4b"
redis-cli SET "session:redis_password_hint" "see eng_standup chat"
redis-cli SET "config:redis_url" "redis://redis:6379"
redis-cli SET "config:db_url" "postgresql://postgres:stillbrook_prod_2026@postgres:5432/stillbrook"
redis-cli SET "config:git_url" "http://gitea:3000/stillbrook/web.git"
redis-cli SET "config:vault_url" "http://vault-host:8200"
redis-cli SET "config:ssh_host" "ssh-jumpbox"
redis-cli SET "config:ssh_port" "2222"
redis-cli SET "config:ssh_user" "m.rivera"
echo "Redis seeded."
