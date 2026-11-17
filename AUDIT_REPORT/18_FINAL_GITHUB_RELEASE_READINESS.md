# 18 — Final GitHub Release Readiness (Stillbrook)

**Date:** 2026-11-17
**Environment:** Kali Linux, Docker Engine 28.5.2, Docker Compose v2.40.3.
**Scope:** All ten release phases. No secret values are reproduced in this
report; only booleans, counts, hashes and statuses.

---

## 1. Project overview

Stillbrook is a Docker-based, intentionally vulnerable enterprise
cybersecurity training environment. It models a segmented corporate
intrusion across ten Compose services (nine long-running plus the one-shot
`vault-init`), two Docker networks, and a staged narrative. It is **not
production software** and must be run only in an isolated lab, with all
published ports bound to `127.0.0.1`. Every credential, hash, token and flag
is synthetic training data. This audit did not rebuild the project; it closed
the remaining publication gaps.

---

## 2. Git history security findings

- Original state: one commit (`8463c68`) containing two genuine SSH private
  keys (`docker/router/id_rsa`, `docker/vaulthost/ssh_host_ed25519_key`).
  Runtime replacements already existed.
- A verified backup (845 entries, 480 objects, including `.git`) was created
  at `/tmp/opencode/stillbrook-backup-<timestamp>.tar.gz`; recovery was proven
  by trial extraction and `git fsck`.
- The single root commit was rebuilt (`git commit --amend`), unreachable
  objects purged (`git reflog expire` + `git gc --prune=now --aggressive`).
- Result: 1 commit, 0 private keys reachable, old commit and both key blobs
  purged, `git fsck --full` clean, working tree clean. No remote configured
  and nothing pushed.
- Details: `AUDIT_REPORT/15_GIT_HISTORY_SECURITY.md`.

**Status: PASS.**

---

## 3. Secret scanning results

| Scan | Result |
|---|---|
| Private-key headers across all revisions (post-cleanup) | 0 files |
| Real-secret signatures (AWS/GitHub/Slack/Google/Stripe/JWT) | 0 files |
| Personal absolute paths in tracked files | 0 |
| Sensitive lines in `docker logs` (all 10 containers) | 0 |
| Real credentials in `.env` / source / docs | 0 (all synthetic) |

Synthetic challenge credentials (Postgres/Gitea/Samba/SSH passwords, NTLM
hash, proof markers, final flag) were confirmed intentional and preserved.
`keys.env` is a `__PENDING__` placeholder, not a live key map.

**Status: PASS.**

---

## 4. Documentation corrections

- `README.md`: removed the non-existent "pre-built image package" (`CYBER-RANGE-STILLBROOK.tar.gz`) option; reconciled RAM/disk figures (8 GB min / 16 GB recommended, 10 GB min / 20 GB recommended disk) with `installguide.md`; removed the unsubstantiated "15 staged flags" claim; clarified the ten-service topology, synthetic credentials, dev-mode Vault, and repository structure (including removal of the stale `gitea_repos/` entry).
- `installguide.md`: rewritten from a fictional archive workflow to the real clone → `.env` → `reset_lab.sh` workflow, with verified requirements, startup/reset/teardown commands, service URLs, ports, login guidance and troubleshooting.
- `docs/architecture/identity.md`: corrected seeded roles/departments to match `seed/users.yaml`; removed references to non-existent AD simulators.
- `docs/architecture/logging.md`: removed references to non-existent `tests/` and `app/operations/monitoring.py`; reflected actual log/detection layout.

**Status: PASS.**

---

## 5. Architecture documentation status

Created `docs/ARCHITECTURE.md` from the actual implementation. It covers all
20 required topics: overall architecture, services, dependencies, networks,
host ports, internal-only services, databases, Redis, Gitea, SSH jumpbox,
internal router, chisel, Vault, Shamir 3-of-3, SMB, FTP, web application,
challenge artefacts, flag retrieval, and reset/recovery. It includes Mermaid
diagrams and a host-accessible / internal / vulnerable / infrastructure
classification. Assumptions are labelled, not asserted as fact.

**Status: PASS.**

---

## 6. Dashboard flag investigation

`story/private_flags/` was never authored or generated; it is a planned
(Sprint 10) per-user flag feature that is unimplemented. `get_flag_for_session()`
already degrades safely: it scopes to the authenticated session, blocks path
traversal, and the story route refuses direct access (HTTP 403 observed). No
replacement flags were invented and no static flag files were created.
Documentation was corrected instead. Full analysis:
`AUDIT_REPORT/16_DASHBOARD_FLAG_INVESTIGATION.md`.

Runtime check: authenticated dashboard returned 200 with widgets rendered and
no flag div; unauthenticated dashboard returned 302; direct `private_flags`
path returned 403. The real final flag remains retrievable from Vault.

**Status: PASS (documented limitation; no code defect).**

---

## 7. Redundant file investigation

`docker/gitea_repos/` was a stale bare repository with no build/runtime
dependency and obsolete content (its `config` also held a personal path).
It was backed up to `/tmp/opencode/stillbrook-gitea_repos-backup-<timestamp>.tar.gz`
(44 entries) and removed; README was updated. Gitea challenge checks still
pass (2 commits, NTLM artifact in HEAD, `.env` in history). Full analysis:
`AUDIT_REPORT/17_REPOSITORY_CLEANUP.md`.

**Status: PASS.**

---

## 8. Public repository file audit

Classified all tracked files. Required source, Docker assets, challenge
artefacts and synthetic data are preserved. `.gitignore` now explicitly
exceptions the required vsftpd source archive; `.dockerignore` excludes
`.env` and generated local DB/log state while retaining narrative
`story/logs/*.log`. No real private keys, personal credentials, runtime
secrets, local DB files, secret-bearing logs, personal machine paths or
unnecessary caches are tracked. The vsftpd archive and `seed/users.yaml`
were proven necessary and kept.

**Status: PASS.**

---

## 9. Vault security review

- No host ports published (`docker port` = 0 lines).
- Dev mode deliberately retained; documented in README and architecture.
- Bootstrap banner redirected to root-only `/vault/dev-bootstrap.log` (mode
  600 root); 0 sensitive lines in `docker logs` for `vault-host`/`vault-init`.
- Runtime token file and key map are mode 0600.
- Three recovery locations verified: Postgres handle 1, SMB checklist handle
  2, jumpbox `.bash_history` handle 3.
- `vault status` = n 3 / t 3 / unsealed; seal + `vault-unseal` with all three
  handles returned to unsealed.
- Final flag read back successfully from `secret/data/final_flag`.

**Status: PASS (dev-mode limitations accepted and documented).**

---

## 10. PostgreSQL security review

- No host port published.
- `pg_hba.conf`: `trust` only for local socket and loopback; `scram-sha-256`
  for all other hosts; `password_encryption = scram-sha-256`.
- Six synthetic challenge users; no unnecessary application roles.
- Vault token and unseal handle 1 present in `service_config` /
  `vault_secrets`; synthetic credentials functional.
- Reset scripts re-seed successfully (15/15).

**Status: PASS (local trust is image default, confined to the container).**

---

## 11. Docker verification

- `docker compose config -q` valid from both the working repo and fresh clone.
- All images built from current source via `reset_lab.sh` (`--build`).
- Nine services running with zero restarts; `vault-init` exited 0.
- Health checks healthy for `web` dependencies (gitea, postgres, redis,
  vault-host).
- Six localhost-bound ports: 21, 80, 443, 2222, 8080, 9090; internal ports
  unpublished.

**Status: PASS.**

---

## 12. Functional regression results

All checks were executed; none are inferred from earlier runs.

| # | Check | Result |
|---:|---|---|
| 1 | Docker Compose configuration | PASS |
| 2 | Image builds from source | PASS |
| 3 | Service startup (9 + init) | PASS |
| 4 | Health checks | PASS |
| 5 | Application readiness (`/health` 200) | PASS |
| 6 | Gunicorn startup (1 worker, 4 threads) | PASS |
| 7 | Application routes | PASS (`/`,`/health`,`/story/` 200; `/dashboard` 302→200 auth; `/admin`,`/wp-admin` 403; IDOR 302; `/api/search` 200) |
| 8 | SSH jumpbox password auth (both accounts) | PASS |
| 9 | Router→Vault key auth (`vault_svc`) | PASS |
| 10 | Chisel connectivity (:8081, :1080, :8082) | PASS |
| 11 | SMB challenge (share listed from internal net) | PASS |
| 12 | FTP banner + backdoor listener :6200 | PASS |
| 13 | Gitea challenge (history + NTLM artifact) | PASS |
| 14 | PostgreSQL challenge (users, token, handle 1) | PASS |
| 15 | Vault initialization (3-of-3, unsealed) | PASS |
| 16 | Vault 3-of-3 seal/unseal ceremony | PASS |
| 17 | Final flag retrieval | PASS |
| 18 | Privilege-escalation artifacts (SUID, immutable shadow, writable cron) | PASS |
| 19 | Dashboard flag behaviour (no leak, no div) | PASS |
| 20 | Reset process | PASS (15/15, twice) |
| 21 | Container log secret scan | PASS (0 lines) |

---

## 13. Fresh-clone installation results

A genuine clean clone was created at
`/tmp/opencode/fresh-clone/Stillbrook-GitHub` from the cleaned repository;
no files, volumes or hidden state from the working repository were reused.

| # | Check | Result |
|---:|---|---|
| 1 | `git clone` succeeds | PASS |
| 2 | Required files present (incl. vsftpd archive, `seed/users.yaml`) | PASS |
| 3 | No pre-existing `.env`/DB/logs/checklist in clone | PASS (all absent) |
| 4 | Environment setup (`cp .env.example .env`) | PASS |
| 5 | `docker compose config -q` | PASS |
| 6 | Images build | PASS |
| 7 | All services start (9 + `vault-init` exit 0) | PASS |
| 8 | Initialization completes (15/15) | PASS |
| 9 | Dashboard loads (anon 302→login; auth 200) | PASS |
| 10 | Challenge instructions / story paths function (403 anon, 200 auth) | PASS |
| 11 | Reset works (second full reset 15/15) | PASS |
| 12 | No missing archive/config blocks install | PASS |

Note on isolation: the Compose file pins `name: stillbrook`, so the clone's
`reset_lab.sh` operated on the same Compose project. It began with
`docker compose down -v`, deleting and recreating all four lab volumes, and
rebuilt images from the **clone's** build context and bind mounts. No file,
hidden state or volume from the working repository was reused; the only
shared element was Docker's content-addressed build cache.

External downloads on first build: base images from Docker registries,
chisel 1.10.1 from GitHub, Vault 1.15.6 binaries + checksums from HashiCorp.
The vsftpd 2.3.4 source archive is tracked in the repository and requires no
download. All download URLs are pinned in the Dockerfiles.

**Status: PASS.**

---

## 14. Remaining limitations

| Item | Nature | Impact |
|---|---|---|
| Vault runs in dev mode | Deliberate, documented | In-memory state lost on container recreation; reset rebuilds it. Not suitable for production. |
| Per-user dashboard flags empty | Planned feature never populated | Dashboard shows no flag widget; real final flag unaffected. Do not invent flags. |
| Synthetic credentials embedded in source | Intentional training data | Must never be reused on real systems. |
| First build needs outbound HTTPS | Documented prerequisite | Offline installs need pre-cached images/binaries. |
| Host isolation rules are runtime-only | `lab_isolation.sh` | Re-run `install` after a host reboot. |
| Backup copies contain the old keys | Kept outside the repo in `/tmp/opencode` | Treat as sensitive; never publish the backup. |

None of these are release blockers.

---

## 15. Files modified (this audit)

- `README.md` — installation/resource/flag-count/dev-mode/structure corrections.
- `installguide.md` — rewritten to the real clone-and-build workflow.
- `.gitignore` — explicit vsftpd archive exception.
- `.dockerignore` — exclude `.env` and generated local state; keep narrative logs.
- `docs/architecture/identity.md` — roles aligned to `seed/users.yaml`.
- `docs/architecture/logging.md` — removed non-existent references.

The final clean commit also folds in the prior audit's already-present working
tree fixes (`Dockerfile`, `docker-compose.yml`, `docker/router/*`,
`docker/vaulthost/*`, `docker/ssh/Dockerfile`, `docker/web/entrypoint.sh`,
`docker/vault/init/vault-init.sh`, `requirements.txt`,
`scripts/init_gitea.sh`, `scripts/reset_lab.sh`, `stillbrook_wsgi.py`,
`seed/users.yaml`, the runtime-checklist template and the vsftpd archive).

## 16. Files added

- `docs/ARCHITECTURE.md`
- `AUDIT_REPORT/15_GIT_HISTORY_SECURITY.md`
- `AUDIT_REPORT/16_DASHBOARD_FLAG_INVESTIGATION.md`
- `AUDIT_REPORT/17_REPOSITORY_CLEANUP.md`
- `AUDIT_REPORT/18_FINAL_GITHUB_RELEASE_READINESS.md`

## 17. Files removed, with reasons

- `docker/gitea_repos/**` — stale, unused bare repository holding obsolete
  challenge data and a personal path; backed up first.
- From Git history only: `docker/router/id_rsa`, `docker/router/id_rsa.pub`,
  `docker/router/known_hosts`, `docker/router/ssh_config`,
  `docker/vaulthost/authorized_keys`,
  `docker/vaulthost/ssh_host_ed25519_key`, `.pub` — replaced by runtime
  generation; backed up first.

No working challenge functionality was removed.

---

## 18. Final release verdict

**READY FOR PUBLIC RELEASE.**

Rationale: no actual secrets remain in Git history; the fresh-clone install
and reset both pass end-to-end; all required challenge files are present; all
functional tests pass; documentation contains no serious installation errors;
and the dashboard does not expose private flags. The remaining items in §14
are deliberate, documented design decisions rather than unresolved defects.
This verdict is based on manual source review plus executed tests, not on
automated tests alone.

Nothing was pushed to GitHub and the repository was not published. The final
commit is clean; the operator must add a remote and push manually after
review.
