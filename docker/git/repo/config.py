# Stillbrook Web App -- Configuration (leaked copy, for the git-leak vuln)
import os

class Config:
    SECRET_KEY = os.environ.get("STILLBROOK_SECRET", "dev-secret-change-me")
    DB_URL = os.environ.get("DB_URL", "postgresql://postgres:stillbrook_prod_2026@postgres:5432/stillbrook")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")
    VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://vault:8200")
    GITEA_URL = os.environ.get("GITEA_URL", "http://gitea:3000")
