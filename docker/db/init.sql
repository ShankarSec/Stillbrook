-- UNVERIFIED -- not run against a live Postgres instance (no Docker in
-- the build environment). Review before trusting it runs as written.
-- Stillbrook PostgreSQL -- Initial Schema + Data

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    full_name VARCHAR(128),
    role VARCHAR(32),
    department VARCHAR(64),
    email VARCHAR(128),
    last_login TIMESTAMP
);

CREATE TABLE service_config (
    key VARCHAR(128) PRIMARY KEY,
    value TEXT
);

CREATE TABLE vault_secrets (
    id SERIAL PRIMARY KEY,
    secret_name VARCHAR(64),
    unseal_key TEXT,
    location_hint VARCHAR(256)
);

-- Seed users (mirror of web app, for DB-based enumeration)
INSERT INTO users (username, full_name, role, department, email, last_login) VALUES
('intern01', 'New Intern', 'employee', 'General', 'intern01@stillbrook.internal', '2026-03-28 09:01:00'),
('m.rivera', 'Maria Rivera', 'engineer', 'Engineering', 'm.rivera@stillbrook.internal', '2026-03-28 10:04:00'),
('d.nguyen', 'David Nguyen', 'operations_lead', 'Operations', 'd.nguyen@stillbrook.internal', '2026-03-28 09:22:00'),
('j.castillo', 'Juan Castillo', 'finance_manager', 'Finance', 'j.castillo@stillbrook.internal', '2026-03-28 09:15:00'),
('backupadmin', 'Backup Admin', 'dr_admin', 'IT Admin', 'backupadmin@stillbrook.internal', '2026-03-28 11:00:00'),
('svc_dr_backup', 'DR Backup Service', 'service', 'IT Admin', 'svc_dr_backup@stillbrook.internal', '2026-03-29 02:00:00');

-- NOTE: roles above match seed/users.yaml exactly (m.rivera=engineer,
-- d.nguyen=operations_lead) -- the earlier draft of this file had them
-- swapped, which would have taught the wrong lesson during DB
-- enumeration (Stage 2/3). Keep this table in sync with seed/users.yaml
-- if either ever changes.

-- Service config (player finds this after DB access)
INSERT INTO service_config (key, value) VALUES
('redis_url', 'redis://redis:6379'),
('git_url', 'http://gitea:3000/stillbrook/web.git'),
('vault_url', 'http://vault-host:8200'),
('ssh_host', 'ssh-jumpbox'),
('ssh_port', '2222'),
('ssh_user', 'm.rivera'),
('ldap_url', 'ldap://samba:389'),
('smb_share', '\\\\samba\\executive');

-- Vault unseal keys (scattered -- one here, others in SMB + SSH)
INSERT INTO vault_secrets (secret_name, unseal_key, location_hint) VALUES
('vault_unseal_key_1', '__PENDING_VAULT_INIT__', 'Found in PostgreSQL vault_secrets table'),
('vault_unseal_key_2', '__PENDING_VAULT_INIT__', 'Found in SMB share: recovery_checklist.txt'),
('vault_unseal_key_3', '__PENDING_VAULT_INIT__', 'Found in SSH: .bash_history');
