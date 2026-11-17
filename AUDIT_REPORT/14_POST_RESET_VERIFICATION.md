# 14 — Post-Reset Verification (Stillbrook)

**Date:** 2026-11-17
**Environment:** Kali Linux, Docker Engine 28.5.2, Docker Compose v2.40.3
**Scope:** Post-reset service, security, SSH, Vault, PostgreSQL, challenge, and regression verification.
**Method:** Live inspection of the running Compose project `stillbrook`. No secret values are reproduced in this report; only booleans, counts, fingerprints and file modes are recorded.

---

## 0. Executive summary

A full clean reset was executed from a simulated fresh-clone state. The final reset returned **15/15 verification checks passed** and exit code 0. All nine long-running containers are up with **zero restarts**; four have passing health checks. Real connectivity tests confirmed SSH (jumpbox password auth, router→Vault key auth), SMB, FTP, Gitea and the challenge data paths. Two concrete security defects were found and corrected: Vault dev-mode credentials were being written to `docker logs`, and a generated unseal key was being written into a Git-tracked file. The Flask development server was replaced with gunicorn. Development-mode Vault is **retained deliberately** (see §2) with the credential-leak path closed; a migration proposal is documented instead of performed because it would be a significant architectural change with real risk to the challenge.

---

## 1. Verified services

Source: `docker compose ps`, `docker inspect` (`.State.Status`, `.State.Health.Status`, `.RestartCount`) and direct endpoint probes.

| Service | Container | Status | Health | Restarts | Application readiness (evidence) |
|---|---|---|---|---:|---|
| `web` | `stillbrook-web-1` | Up | n/a | 0 | gunicorn 22.0.0 serving; `GET /` → 200, `/health` → 200, `/story/` → 200, `/admin` → 403 |
| `redis` | `stillbrook-redis-1` | Up | healthy | 0 | `redis-cli ping` → PONG via `web`; seed script executed |
| `postgres` | `stillbrook-postgres-1` | Up | healthy | 0 | `pg_isready` OK; 6 challenge users present |
| `gitea` | `stillbrook-gitea-1` | Up | healthy | 0 | `/api/healthz` OK; challenge repo pushed (2 commits, `.env` in history, NTLM artifact present) |
| `ssh-jumpbox` | `stillbrook-ssh-jumpbox-1` | Up | n/a | 0 | SSH-2.0 banner on :2222; password auth confirmed for both lab accounts; SOCKS5 :1080 and decoy :8082 configured |
| `internal-router` | `stillbrook-internal-router` | Up | n/a | 0 | chisel listening on :8081 (confirmed from jumpbox); sshd on :2223 |
| `vault-host` | `stillbrook-vault-host` | Up | healthy | 0 | `vault status` OK; initialized, unsealed, 3-of-3 Shamir; SSH key hop verified |
| `vsftpd` | `stillbrook-vsftpd` | Up | n/a | 0 | Banner `220 vsFTPd 2.3.4 ready...`; backdoor shell listener on container port 6200 confirmed via `/proc/net/tcp` |
| `samba` | `stillbrook-samba` | Up | n/a | 0 | `smbclient //samba/executive` reachable from internal network; checklist listed |
| `vault-init` | `stillbrook-vault-init` | Exited 0 (one-shot by design) | n/a | 0 | Log ends with "finished successfully"; all scatter targets verified |

Internal connectivity observed: `web → redis/postgres/gitea` (internal network), `vault-init → vault-host/postgres/samba/ssh-jumpbox`, `ssh-jumpbox → internal-router:8081/2223`, `internal-router → vault-host:2224`. The `internal` network remains `internal: true`.

**Note:** a running container was not treated as proof of function. Each service above has an application-level check.

---

## 2. Vault development mode — investigation and decision

### Observed configuration

`docker/vaulthost/entrypoint.sh` starts `vault server -dev -dev-listen-address=0.0.0.0:8200`. Dev mode uses the `inmem` storage backend and auto-initializes with **1 share / threshold 1**, printing a bootstrap unseal key and root token at startup. `docker/vault/init/vault-init.sh` then:

1. reads the bootstrap share,
2. rekeys the server to a genuine **3-of-3 Shamir quorum**,
3. scatters three synthetic handles to PostgreSQL, Samba and the jumpbox,
4. seals and unseals with all three shares,
5. writes the final flag to `secret/data/final_flag`.

Post-reset `vault status -format=json` confirms `"n": 3, "t": 3, "sealed": false, "initialized": true`.

### Is dev mode necessary?

Not strictly necessary to achieve 3-of-3 — a properly initialized standalone server could do so. However, dev mode is currently the **tested bootstrap mechanism** for obtaining the initial share used to authorize the rekey. Replacing it requires coordinated changes to two components (`entrypoint.sh` and `vault-init.sh`) and a storage backend decision. Per the operating rule requiring a proposal before significant architectural change, this migration was **not** performed.

### Security defect found and fixed

The dev-mode startup banner (containing the bootstrap unseal key and root token) was emitted to stdout and therefore visible in `docker logs stillbrook-vault-host`. This has been corrected:

- `entrypoint.sh` now redirects Vault startup output to `/vault/dev-bootstrap.log` with mode `0600`, owner `root`.
- `vault-init.sh` reads the bootstrap share from that root-only file via `docker exec` instead of `docker logs`.

**Evidence (post-fix):** `docker logs` sensitive-line count is **0** for `vault-host`, `vault-init`, `web`, `ssh-jumpbox` and `internal-router`; `/vault/dev-bootstrap.log` is mode `600`.

### Proposed safe implementation (deferred)

To remove dev mode without breaking the challenge:

1. Add `docker/vaulthost/vault.hcl` with `storage "file" { path = "/vault/file" }`, `listener "tcp" { address = "0.0.0.0:8200" tls_disable = true }`, `disable_mlock = true`, `api_addr = "http://127.0.0.1:8200"`.
2. In `entrypoint.sh`, start Vault with `-config`, then on an uninitialized server run `vault operator init -key-shares=3 -key-threshold=3 -format=json > /vault/init.json` (mode `0600`), extract the root token and three shares to root-only files, unseal with all three, then hand off to the foreground server.
3. In `vault-init.sh`, remove the rekey section and read the already-3 shares from the root-only file; keep the existing handle→share map (`/vault/data/keys.env`), scatter locations, seal/unseal ceremony and flag write unchanged.
4. Regression-test the full reset, all three key discovery paths, the `vault-unseal` helper and final flag retrieval before adopting.

This preserves the 3-of-3 challenge, key locations, flag and reset semantics while removing dev-mode bootstrap credentials entirely.

---

## 3. PostgreSQL authentication — investigation

`pg_hba.conf` contains the official `postgres:16-alpine` defaults:

```
local   all  all              trust
host    all  all  127.0.0.1/32 trust
host    all  all  ::1/128      trust
host    all  all  all          scram-sha-256
```

- **Why trust exists:** it is the image's `initdb` default for the Unix socket and loopback, required by the entrypoint's initialization scripts and by `docker exec ... psql` administration (including `reset_lab.sh`).
- **Network authentication:** `scram-sha-256` for all non-loopback hosts; `password_encryption` is `scram-sha-256`; the `postgres` superuser password is supplied via `POSTGRES_PASSWORD`.
- **Exposure:** no host port is published; PostgreSQL is reachable only from the `internal` Docker network. Players reach it after the intended pivot and must authenticate.
- **Roles:** only the `postgres` superuser plus PostgreSQL system roles; no unnecessary application roles.

**Decision:** no insecure change was identified that is both real and safe to remove. Tightening local trust to `scram` would break the init scripts and reset procedure while providing no additional isolation (loopback is inside the container). The setting is documented rather than altered.

---

## 4. Flask development server — finding and fix

`app.py` ends with `app.run(host="0.0.0.0", port=5000, ...)`, which is Werkzeug's development server and explicitly not production-capable. Although the lab is isolated and localhost-bound, a production-capable WSGI server is more appropriate and was implemented:

- Added `gunicorn==22.0.0` to `requirements.txt`.
- `docker/web/entrypoint.sh` now runs `gunicorn --bind 127.0.0.1:5000 --workers 1 --threads 4 --timeout 60 ... stillbrook_wsgi:app`.
- Added `stillbrook_wsgi.py`, which loads the root `app.py` by file path under a distinct module name. This was necessary because the `app/` package shadows `app.py`, so `app:app` resolves to the package and loses all challenge routes. A single worker is intentional: lockout, WAF-hit and IDOR state are process-local by design.

**Regression evidence:** gunicorn 22.0.0 active; routes `/` (200), `/health` (200), `/story/` (200), unauthenticated `/api/v2/fin/exports/1` (302 to login), `/admin` (403). `GET /health` and the full reset check "web :80" both pass.

---

## 5. Newly added files — verification

| File | Why added / required by | Legitimate? | Risk assessment |
|---|---|---|---|
| `docker/vsftpd/vsftpd-2.3.4.tar.gz` | Build input for `docker/vsftpd/Dockerfile` (`COPY vsftpd-${VERSION}.tar.gz`); the lab compiles the intentionally backdoored 2.3.4 source. It was previously **untracked and ignored**, so a fresh clone could not build this image. | Yes — genuine upstream source, 158 files, 184 KB. | SHA-256 matches the value pinned in the Dockerfile (`b466edf…a5a`). Required and safe; now tracked. |
| `seed/users.yaml` | Consumed by `seed/seed_db.py` at image build time; defines the six synthetic challenge accounts used for the credential-derivation challenge. It was previously **untracked and ignored**, so a fresh clone could not seed the app. | Yes — clearly synthetic accounts with `attack_value` annotations. | Contains only fabricated lab credentials; no real/reused secrets. Required; now tracked. |

Neither file was deleted.

---

## 6. SSH replacement — verification

No private key is baked into any image (verified by starting fresh containers from the images with `--entrypoint sh`: router image `.ssh/` contains only `config`; vault-host image has no `authorized_keys`).

| Check | Result |
|---|---|
| Vault-host generates router key at runtime into `vault_shared:/shared/id_rsa` | PASS — present, mode `600` |
| Public key installed to `/home/vault_svc/.ssh/authorized_keys` | PASS — mode `600` |
| Router entrypoint copies key to `/home/svc_router/.ssh/id_rsa` | PASS — mode `600` |
| Private/public/authorized fingerprints identical | PASS — `SHA256:wQpfbkUs…CbE` |
| SSH host key generated at runtime | PASS — `/etc/ssh/ssh_host_ed25519_key`, mode `600` |
| `ssh_config` uses `IdentityFile`, `StrictHostKeyChecking no` | PASS (`ssh -G`) |
| Router (`svc_router`) → `vault-host:2224` as `vault_svc`, key auth | PASS — remote `id -un` returned `vault_svc` |
| Host → jumpbox `:2222` password auth (`m.rivera`, `backupadmin`) | PASS — both accounts authenticated |
| `vault_svc` cannot read `/vault/.vault_token` | PASS — access denied (root-only), as designed |
| chisel server reachable from jumpbox on `internal-router:8081` | PASS |

The earlier failure ("Permission denied (publickey)") was a **test artifact**: the first test ran `ssh` as root, which looked in `/root/.ssh` instead of `svc_router`'s key. Re-running as `svc_router` succeeded. Separately, an earlier apparent key mismatch was caused by stale pre-fix images (see §9).

---

## 7. Challenge functionality — verification

| Challenge path | Evidence | Result |
|---|---|---|
| SSH routing / tunnelling | Jumpbox password auth OK; chisel :8081 open from jumpbox; router→vault SSH OK | PASS |
| Samba executive share | `smbclient //samba/executive` from internal network lists `recovery_checklist.txt` | PASS |
| PostgreSQL credential storage | `vault_secrets.key_name='unseal_key_1'` row holds a generated handle | PASS |
| Unseal key 2 | Present in the executive-share checklist; file regenerated from tracked template, generated value not committed | PASS |
| Unseal key 3 | Present in `m.rivera` `.bash_history` on the jumpbox | PASS |
| Vault unseal ceremony | Server unsealed; `n=3 t=3 sealed=false`; `vault-unseal` helper installed and key map mode `600` | PASS |
| Final flag | Retrievable with the token stored in PostgreSQL `service_config`; matches `stillbrook{…}` | PASS |
| FTP | Banner correct; backdoor shell listener active on container :6200 (not published) | PASS |
| Gitea | Repo `stillbrook/web` has 2 commits; `.env` recoverable from history; `ntlm_3f7a2b1c.txt` in HEAD tree | PASS |
| Privilege escalation | SUID `vault-reader` setuid; `/etc/shadow` immutable; cron script mode `0666`; `sudo /usr/bin/less` rule present; `proc-version` reports `4.15.0-91-generic` | PASS |
| Reset / regeneration | Full reset from simulated fresh state: 15/15 checks, exit 0 | PASS |

Flags were checked by marker presence/boolean only; their values are not reproduced here.

---

## 8. Logs and sensitive information

Scanned `docker logs` for all containers against patterns for private-key headers, root tokens, unseal keys, generated handles, known lab passwords and flag markers.

| Container | Sensitive lines (post-fix) |
|---|---:|
| `vault-host` | 0 |
| `vault-init` | 0 |
| `web` | 0 |
| `ssh-jumpbox` | 0 |
| `internal-router` | 0 |

Before the fix, `vault-host` had 2 such lines (dev bootstrap unseal key and root token). The generated unseal key 2 was also being written into the Git-tracked `docker/samba/share/recovery_checklist.txt`; this was converted to an untracked runtime file generated from the tracked `.example` template. Generated SQLite DBs, `init.log` and Python caches remain ignored.

**Note:** the Git history still contains the two originally committed private keys (single initial commit). They are removed from the current tree and no longer used, but history cleanup and rotation should be considered before publication. No secret values are included in this report.

---

## 9. Changes made in this phase

1. `docker/vaulthost/entrypoint.sh` — redirect Vault dev bootstrap output to root-only `/vault/dev-bootstrap.log`.
2. `docker/vault/init/vault-init.sh` — read the bootstrap share from that file (not `docker logs`); create the live SMB checklist from the tracked template when absent.
3. `scripts/reset_lab.sh` — use `docker compose up -d --build` to avoid stale images; fix the final-flag check to supply the runtime token.
4. `requirements.txt` — add `gunicorn==22.0.0`.
5. `docker/web/entrypoint.sh` — serve via gunicorn instead of `app.run()`.
6. `stillbrook_wsgi.py` (new) — WSGI entry module that loads the full root app.
7. `docker/samba/share/recovery_checklist.txt` → `recovery_checklist.txt.example` (tracked template); live file now ignored/generated.
8. `.gitignore` — ignore the generated checklist.
9. Tracked previously-missing required files: `seed/users.yaml`, `docker/vsftpd/vsftpd-2.3.4.tar.gz`, `stillbrook_wsgi.py`.

Earlier in the audit (already applied before this phase): repaired the duplicated/invalid `docker-compose.yml`, pinned `name: stillbrook`, replaced committed SSH keys with runtime generation, fixed Compose build context/args, fixed BusyBox `chown` of the dotted username, fixed `init_gitea.sh` password handling and real Git history, added build-time DB seeding, and repaired the Dockerfile chisel installation.

**Stale-image regression:** an earlier reset reported 12/15 because the project name was pinned *after* images were built, so containers reused old `stillbrook-*` images while new builds were tagged `stillbrook-github-*`. `reset_lab.sh` now always uses `--build`, and the final reset uses current images throughout (verified image creation timestamps).

---

## 10. Remaining problems

| Severity | Item | Impact | Recommended action |
|---|---|---|---|
| Medium | Vault still runs in dev mode (in-memory storage; root token generated at runtime) | State is lost on container recreation (acceptable for this reset-driven lab) and dev-mode bootstrap is unusual for a distributable project | Implement the proposal in §2 before final publication if a non-dev Vault is required |
| Medium | Private keys remain in the single Git commit's history | Material is compromised (already disclosed) and would be published with history | Rotate/regenerate (already done at runtime) and consider history cleanup before push; these are synthetic lab keys with no external trust |
| Low | `README.md`/`installguide.md` still reference a non-existent pre-built `CYBER-RANGE-STILLBROOK.tar.gz` package and inconsistent resource figures | A new user may follow a path that does not exist | Rewrite installation docs to the actual clone + `reset_lab.sh` workflow; reconcile 4 GB/3 GB vs 8 GB/10 GB |
| Low | `docs/architecture/identity.md` lists roles (`hr_user`, `engineer` for d.nguyen) that differ from `seed/users.yaml`; `logging.md` references non-existent `tests/` and `app/operations/monitoring.py` | Misleading documentation | Update to match implementation |
| Low | `story/private_flags/` referenced by `app/scoring/flag_service.py` does not exist, so per-user dashboard flags resolve to `None` | Dashboard flag widget is empty; 15-flag claim is not substantiated by files | Either add intended per-user flag content or document the limitation and correct the flag count |
| Low | `docker/gitea_repos/` bare repository is a redundant prebuilt artifact (unused; `init_gitea.sh` now generates the repo with history) | Confusing duplicate challenge data | Remove from the public release or document as legacy |

**Release decision:** the lab is functional, all 15 automated reset checks pass, the verified challenge paths work, and the identified log-leak defect is fixed. The remaining items are documentation/legacy-hygiene issues plus the deliberate dev-mode decision. This supports **READY WITH DOCUMENTED LIMITATIONS**, not an unconditional "ready", until the documentation and Git-history items above are addressed.

---

*No secrets, tokens, unseal keys, passwords, private keys or flag values are contained in this report. Nothing was pushed to GitHub.*
