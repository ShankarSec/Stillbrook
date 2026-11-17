# Identity Model

## Source of truth

`database/users.db` (table `users`) is the live identity store the Flask app
authenticates against. It is seeded at **Docker image build time** by
`seed/seed_db.py` from `seed/users.yaml`, which is idempotent (upserts by
username). A companion `database/acl.db` holds role→route rules from
`seed/acl_rules.yaml`.

Both SQLite files are generated at build time and are git-ignored; they are
not part of a fresh clone.

## Schema

```
users
  id              INTEGER PK
  username        TEXT UNIQUE NOT NULL
  password_hash   TEXT NOT NULL   -- werkzeug generate_password_hash
  role            TEXT NOT NULL
  department      TEXT NOT NULL
  project         TEXT            -- nullable

acl_rules
  id              INTEGER PK
  role            TEXT NOT NULL
  route           TEXT NOT NULL
  UNIQUE(role, route)
```

## Seeded accounts

These values come from `seed/users.yaml` and are the authoritative identities
for the web application. All passwords are synthetic lab data.

| username | role | department | project |
|---|---|---|---|
| intern01 | employee | general | Spring Onboarding |
| j.castillo | finance_manager | finance | Orion Budget |
| m.rivera | engineer | engineering | BlackEcho Migration |
| d.nguyen | operations_lead | operations | Phoenix DR |
| sa_finance_sync | service_account | finance | Orion Sync |
| backupadmin | dr_admin | it | Phoenix DR |

Earlier drafts of this document listed roles (`hr_user`, `engineer` for
`d.nguyen`) that do not match the seed file; those were incorrect and have
been corrected here. The PostgreSQL challenge table (`docker/db/init.sql`)
mirrors these users for DB enumeration.

## Other identity layers

- `app/access_control.py` and `seed/acl_rules.yaml` implement route-level
  authorisation for the web app.
- `app/story/__init__.py` implements file-level ACLs over `story/` content,
  independent of the DB tables.
- Samba and the SSH jumpbox have their own synthetic accounts defined in
  `docker-compose.yml` and the image builds; these are not part of
  `users.db`.

## Note on legacy documents

References in older notes to `ad_simulator/`, `ad_domain/` and a planned
"real Samba AD DC" were aspirational and are not present in this repository.
The implemented identity model is the SQLite web-app store described above
plus the separate service accounts.
