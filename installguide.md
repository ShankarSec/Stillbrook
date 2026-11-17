# STILLBROOK — Installation Guide

Stillbrook is an **intentionally vulnerable cybersecurity training
environment** distributed as source code. There is **no pre-built archive
or downloadable image package** — you build the lab from the Git repository
on your own machine.

> [!WARNING]
> This is a lab, not production software. It contains deliberately weak
> services, planted credentials and exploitable application paths. Run it
> only inside an isolated lab that you own or are authorised to test. Keep
> every published port bound to `127.0.0.1` and never expose these services
> to a public or production network. All passwords, hashes, tokens and
> flags in the repository are synthetic training data.

---

## 1. System requirements

These figures reflect the current Compose stack (nine long-running services
plus one one-shot initialiser) and have been validated by building and
resetting the full project.

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Free disk space | 10 GB | 20 GB |

- CPU must support the container images used below (standard x86-64 or
  arm64; the Dockerfiles select release binaries by architecture).
- Disk space covers Docker layers, build caches, the downloaded vsftpd and
  Vault sources, and the Compose volumes (`pgdata`, `gitea_data`,
  `jumpbox_home`, `vault_shared`).
- Internet access is required on first build: the images pull base layers
  and the router, vault-host and vsftpd builds download verified upstream
  binaries/sources (chisel, Vault, vsftpd 2.3.4). Subsequent runs reuse the
  Docker cache.

Supported host operating systems:

- Kali Linux (recommended; 2024.1 or later)
- Ubuntu 22.04 or later
- Debian 12 or later

## 2. Required software

Check your installed versions before starting:

```bash
docker --version          # Docker Engine 24+ (28.x verified)
docker compose version    # Docker Compose v2 (v2.40+ verified)
git --version
python3 --version         # 3.11+ (3.12 used by the web image)
```

Install Docker and the Compose v2 plugin using your distribution's official
instructions if the commands above are not available. Your user must be in
the `docker` group (or you must prefix Docker commands with `sudo`).

Optional client tools used during the exercises (all standard on Kali):

```bash
sudo apt update
sudo apt install -y nmap curl dirb sqlmap hydra hashcat proxychains4 \
    smbclient ftp
```

## 3. Clone the repository

There is no archive to download. Clone the source repository:

```bash
git clone <REPOSITORY_URL> ~/Stillbrook-GitHub
cd ~/Stillbrook-GitHub
```

Replace `<REPOSITORY_URL>` with the URL of the published Stillbrook
repository. Confirm that the following files are present before continuing:

```bash
ls docker-compose.yml Dockerfile scripts/reset_lab.sh \
    seed/users.yaml docker/vsftpd/vsftpd-2.3.4.tar.gz \
    docker/samba/share/recovery_checklist.txt.example
```

All of these are required. In particular, the vsftpd source archive is a
build input for the FTP challenge and `seed/users.yaml` seeds the web
application — a fresh clone cannot build or run the lab without them.

## 4. Environment configuration

Copy the example environment file. It defines the synthetic lab passwords
used by the SSH jumpbox and Gitea seed:

```bash
cp .env.example .env
```

`.env` is ignored by Git and must never be committed. The values in
`.env.example` are synthetic challenge credentials; change them only if you
understand the dependency (`scripts/init_gitea.sh` and the jumpbox image
build read them).

## 5. Build and start the lab

The recommended path is the reset script, which builds current source,
seeds a clean state and runs all verification checks:

```bash
./scripts/reset_lab.sh
```

The script:

1. Stops all Compose containers and removes Compose-managed volumes.
2. Re-seeds the local SQLite databases and clears detection logs.
3. Rebuilds images from source (`docker compose up -d --build`).
4. Initialises the Gitea challenge repository with real Git history.
5. Runs the one-shot `vault-init` service (generates the unseal material
   and stores the final flag).
6. Verifies the stack and reports where to retrieve the three unseal keys.

> [!CAUTION]
> Reset runs `docker compose down -v --remove-orphans`, which deletes
> Compose-managed volumes. Those volumes contain only regenerable lab state
> (databases, Gitea data, jumpbox home and the shared SSH key), so this is
> safe — but back up anything you added before resetting.

For a manual start without the full reset checks:

```bash
docker compose up -d --build
./scripts/init_gitea.sh
```

## 6. Verify services

```bash
docker compose ps
```

Expected: nine services running and `vault-init` exited with code 0 (it is
a one-shot container by design). Confirm application readiness rather than
relying on container status alone:

```bash
curl -sf http://127.0.0.1/health
docker compose logs --tail=100
```

## 7. Web access and published ports

Open the dashboard and the story application in a browser:

- <http://127.0.0.1/>
- <https://127.0.0.1/> (self-signed certificate; redirects to HTTP)

Six ports are published, all bound to `127.0.0.1`:

| Port | Service | Role |
|---:|---|---|
| 21/tcp | vsftpd 2.3.4 | FTP service / backdoor investigation |
| 80/tcp | nginx → Gunicorn/Flask | Main web application |
| 443/tcp | nginx | Self-signed TLS endpoint / redirect |
| 2222/tcp | OpenSSH | SSH jumpbox |
| 8080/tcp | decoy | Service-enumeration decoy |
| 9090/tcp | decoy | Fake monitoring endpoint |

Verify with:

```bash
ss -lntp
nmap -p 21,80,443,2222,8080,9090 127.0.0.1
```

Redis, PostgreSQL, Gitea, Samba, the internal router and the Vault host are
**internal-only** and have no host port mappings.

## 8. Login and challenge access

Log in to the web application with one of the synthetic accounts defined in
`seed/users.yaml` (for example `intern01`, `m.rivera`, `j.castillo`,
`d.nguyen`, `backupadmin` or `sa_finance_sync`). Credentials are derived
from the corporate story artefacts — that derivation is part of Stage 1.

- After login, the dashboard links to role-gated story resources under
  `/story/`.
- SSH into the jumpbox on port 2222 using the accounts documented in the
  story (the passwords originate from `.env`).
- The remaining stages (IDOR, SQL injection, hidden webshell, Gitea history,
  FTP backdoor, SSH/SOCKS pivot, privilege escalation and the Vault unseal
  ceremony) follow the staged outline in `README.md`.

## 9. Reset, stop and teardown

```bash
./scripts/reset_lab.sh          # full destructive reset + rebuild + verify
docker compose down             # stop containers, keep volumes
docker compose down -v --remove-orphans   # stop and delete lab volumes
```

Use the last command only when you intentionally want to discard lab state.

## 10. Troubleshooting

| Symptom | Checks |
|---|---|
| Containers will not start | `docker compose ps`, `docker compose logs --tail=150`, `docker compose config` |
| Port unavailable | `ss -lntp`, `docker compose ps`, confirm loopback binding |
| Application not ready | `docker compose logs --tail=200 web`, `curl -v http://127.0.0.1/health` |
| `vault-init` failed | `docker compose logs --tail=100 vault-init` |
| Stale behaviour after edits | Re-run `./scripts/reset_lab.sh` (uses `--build`) |
| State inconsistent | Full reset; remember it removes Compose volumes |
| Build cannot download chisel/Vault/vsftpd | Confirm outbound HTTPS access and retry |

Do not flush the host firewall as a shortcut. Review
`scripts/lab_isolation.sh` before using the optional host-side isolation
helper, and keep a recovery path.

## 11. Success criteria

The installation succeeded when:

- all images build from source with no missing-file errors;
- `docker compose ps` shows nine running services and `vault-init` exited 0;
- `http://127.0.0.1/` loads the dashboard;
- the reset script reports all checks passing;
- the three unseal-key locations are populated and the final flag is
  retrievable from Vault.

---

*No real secrets are required to install Stillbrook. Every credential and
flag used by the lab is synthetic and regenerated on reset.*
