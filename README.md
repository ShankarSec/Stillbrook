<div align="center">

# STILLBROOK
### Enterprise Security Training Environment

**A segmented, multi-container corporate intrusion simulation**

![Difficulty](https://img.shields.io/badge/Difficulty-Medium--Hard-orange?style=for-the-badge)
![Docker](https://img.shields.io/badge/Runtime-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Platform](https://img.shields.io/badge/Attacker-Kali%20Linux-557C94?style=for-the-badge&logo=kalilinux&logoColor=white)
![Training](https://img.shields.io/badge/Focus-Red%20Team%20%7C%20Blue%20Team-7B61A8?style=for-the-badge)

**6–12 hours** · **Medium–Hard** · **Local Docker lab**

*Discover the attack path. Preserve the evidence. Improve the defence.*

</div>

---

## Overview

**Stillbrook** is a Docker-based enterprise security training environment that models a corporate intrusion across a segmented network. Learners investigate a connected attack scenario beginning with external reconnaissance and progressing through web application weaknesses, credential discovery, proxy chaining, lateral movement, privilege escalation and a final secrets-recovery objective involving HashiCorp Vault.

Rather than presenting isolated vulnerable services, Stillbrook connects its components through a staged corporate narrative. Story artefacts—including emails, chat messages, tickets, CMDB records, HR documents and logs—provide investigation context and clues.

The environment is intended for:

- **Red-team practice:** reconnaissance, enumeration, controlled exploitation, credential attacks, pivoting and privilege escalation.
- **Blue-team practice:** evidence collection, event review, attack-path reconstruction and incident reporting.
- **Detection engineering:** identifying useful telemetry, developing detection hypotheses and validating them against lab activity.
- **Security education:** understanding how weaknesses across identity, applications, infrastructure and operations can combine into a larger compromise.

> [!WARNING]
> **Authorised training use only.** Stillbrook intentionally contains vulnerable services, weak configurations, planted credentials and simulated attack paths. Run it only on systems and networks you own or are explicitly authorised to test. Keep the published services bound to localhost and do not expose the lab to the public internet.

## At a glance

| Attribute | Details |
|---|---|
| Environment | Stillbrook Corporation |
| Lab type | Multi-container enterprise intrusion simulation |
| Runtime | Docker Engine and Docker Compose v2 |
| Difficulty | Medium–Hard |
| Estimated completion | 6–12 hours |
| Containers | 10 services (9 long-running + the one-shot `vault-init`) |
| Objectives | Staged challenges culminating in a final Vault flag |
| Published ports | 6, bound to `127.0.0.1` |
| Networks | `lab` (`172.29.0.0/16`) and `internal` (`172.28.0.0/16`) |
| Internal egress | Disabled for the Docker `internal` network |
| Attacker platform | Kali Linux recommended |
| Main technologies | Flask/Gunicorn, nginx, PHP-FPM, OpenSSH, vsftpd, PostgreSQL, Redis, Gitea, Samba and Vault |

*Container, port and health-check figures reflect the current Compose configuration and reset output. There is no fixed count of per-user dashboard flags; the dashboard flag feature is described in `AUDIT_REPORT/16_DASHBOARD_FLAG_INVESTIGATION.md`.*

## Learning objectives

By completing the lab, learners should be able to:

1. Perform unauthenticated reconnaissance and identify exposed services.
2. Correlate corporate story artefacts to derive investigation leads.
3. Examine authentication, lockout and role-based access behaviour.
4. Identify insecure direct object reference (IDOR) weaknesses.
5. Investigate blind SQL injection and understand incomplete WAF filtering.
6. Discover a concealed PHP command endpoint.
7. Enumerate internal services and investigate exposed repository artefacts.
8. Analyse challenge-response credential material offline.
9. Understand the risks of vulnerable services and weak SSH credentials.
10. Establish a SOCKS/SSH pivot into an internal network.
11. Investigate lateral movement opportunities across network segments.
12. Compare SUID, sudo and scheduled-task privilege-escalation weaknesses.
13. Investigate a multi-part Vault unseal workflow.
14. Preserve evidence and construct a defensible attack timeline.
15. Recommend practical mitigations and detection opportunities.

---

## Architecture

The player begins on a local assessment workstation. Six services are published on the Docker host; supporting services remain on the internal Docker network and are not published directly to the host.

```text
                    ASSESSMENT WORKSTATION
                         127.0.0.1
                              |
       +----------+-----------+----------+----------+----------+
       |          |           |          |          |          |
      :21        :80         :443       :8080      :9090     :2222
       |          |           |          |          |          |
+------v----------v-----------v----------v----------v----------v------+
|                           DOCKER HOST                              |
|                                                                    |
|  +-------------+  +---------------------------+  +---------------+ |
|  | FTP         |  | WEB APPLICATION           |  | SSH JUMPBOX   | |
|  | vsftpd      |  | nginx / Flask / PHP-FPM    |  | OpenSSH       | |
|  | 2.3.4 lab   |  | Hidden cmd.php endpoint    |  | Dante SOCKS5  | |
|  | /shared     |  | Tomcat / Grafana decoys    |  | Chisel decoy  | |
|  +-------------+  +-------------+-------------+  +-------+-------+ |
|                                 |                         |         |
|                                 +------------+------------+         |
|                                              |                      |
|                     INTERNAL NETWORK (172.28.0.0/16)                |
|                     Docker network: internal: true                  |
|  +----------------------------------------------------------------+ |
|  |                                                                | |
|  |  +---------+  +----------+  +---------+  +---------+           | |
|  |  | Redis   |  |PostgreSQL|  | Gitea   |  | Samba   |           | |
|  |  +---------+  +----------+  +---------+  +---------+           | |
|  |                                                                | |
|  |  +----------------------+        +--------------------------+  | |
|  |  | INTERNAL ROUTER      |        | VAULT HOST               |  | |
|  |  | SSH :2223            |------->| SSH :2224                |  | |
|  |  | Chisel :8081         |        | Vault :8200              |  | |
|  |  +----------------------+        | SUID / sudo / cron       |  | |
|  |                                  +--------------------------+  | |
|  +----------------------------------------------------------------+ |
+--------------------------------------------------------------------+
```

### Network segments

| Network | Subnet | Purpose |
|---|---|---|
| `lab` | `172.29.0.0/16` | Player-facing lab segment and service connectivity |
| `internal` | `172.28.0.0/16` | Internal-only services; configured with `internal: true` |

The internal network is intended to prevent attached containers from reaching external networks. This does **not** automatically prevent the Docker host from communicating with the bridge subnet. Host-side isolation is handled separately by the supplied script.

### Published ports

Exactly six ports are intended to be published by the Compose stack. All should bind to `127.0.0.1`.

| Port | Service | Intended role |
|---:|---|---|
| `21/tcp` | vsftpd 2.3.4 | FTP service and backdoor investigation |
| `80/tcp` | nginx → Flask | Main corporate web application |
| `443/tcp` | nginx TLS endpoint | Self-signed TLS endpoint and HTTP redirect |
| `2222/tcp` | OpenSSH | SSH jumpbox |
| `8080/tcp` | Tomcat decoy | Service-enumeration decoy |
| `9090/tcp` | nginx / fake Grafana | Service-enumeration decoy |

Internal services such as Redis, PostgreSQL, Gitea, Samba, the router and Vault host should not publish ports directly to the Docker host.

Verify the actual bindings with:

```bash
docker compose ps
docker compose config
ss -lntp
nmap -p 21,80,443,2222,8080,9090 127.0.0.1
```

---

## Assessment stages

The scenario is designed as a connected progression. Stage numbering below follows the current assessment outline.

| Stage | Area | Investigation focus |
|---:|---|---|
| 0 | Story reconnaissance | Role-gated file access and artefact correlation |
| 1 | Credential derivation | Pattern-based password construction from corporate documents |
| 2 | Initial access | Web login workflow and lockout policy |
| 3 | Dashboard enumeration | Role-based widget visibility |
| 4 | Department discovery | Metadata and application information gathering |
| 5 | IDOR | `/api/v2/fin/exports/<id>` and object-level authorisation |
| 6 | Blind SQL injection | Time-based behaviour and incomplete WAF filtering |
| 7 | Hidden webshell | PHP endpoint discovery and nginx behaviour |
| 8 | Service enumeration | Redis, PostgreSQL, Gitea and repository artefacts |
| 9 | Credential attacks | Hydra, Hashcat and FTP backdoor investigation |
| 10 | Proxy chain and lateral movement | SOCKS5 → SSH pivoting across network segments |
| 11 | Privilege escalation | SUID binary, sudo rule and writable scheduled task |
| 12 | Secrets extraction | Three-part Shamir unseal and Vault data access |

### Investigation method

For each stage, document the following:

- **Observation:** What did you find?
- **Evidence:** Which request, response, file, event or command output supports it?
- **Hypothesis:** What weakness could explain the behaviour?
- **Validation:** How did you confirm it within the lab?
- **Impact:** What could an attacker gain?
- **Detection:** Which logs or telemetry could reveal the activity?
- **Remediation:** What change would reduce the risk?

This approach makes the lab useful for incident investigation and detection engineering—not only flag collection.

---

## Privilege-escalation scenarios

The vault host contains three intentional privilege-escalation paths and one misleading kernel-version clue.

| Vector | Lab condition | Learning focus |
|---|---|---|
| SUID | `/usr/local/bin/vault-reader` has mode `4755` and reads from `/vault/data/` | SUID program review and file-access boundaries |
| Sudo | `vault_svc` has `NOPASSWD` permission for `/usr/bin/less` | Risks of granting privileged access to interactive programs |
| Cron | `/opt/scripts/vault_rotate.sh` is world-writable (`0666`) and executed by root every five minutes | Privileged scheduled-task permissions |
| Decoy | `proc-version` reports `4.15.0-91-generic`, while the actual runtime kernel is newer | Validating environment information before selecting an exploit |

### SUID path

```text
/usr/local/bin/vault-reader
/usr/local/src/vault-reader.c
```

The SUID reader is intentionally designed to demonstrate how a privileged helper can expose sensitive data when its access controls are insufficient.

### Sudo path

The `vault_svc` account is configured to run `/usr/bin/less` as root without a password. This demonstrates why interactive tools and shell-capable programs require careful sudo policy review.

### Scheduled-task path

```text
/opt/scripts/vault_rotate.sh
```

The script is described as world-writable and executed by root on a five-minute schedule. A privileged task must never trust a script that unprivileged users can modify.

### Kernel-version decoy

The `proc-version` helper presents an old kernel-version string. Treat this as a lab decoy, not proof of the actual kernel version or exploitability. Validate the real execution environment before drawing conclusions.

---

## Decoys and rabbit holes

The lab includes misleading artefacts to encourage careful validation and evidence correlation.

| Decoy | Intended effect |
|---|---|
| Port `443` | Redirects to HTTP rather than providing a separate application |
| Port `8080` | Tomcat decoy; `/manager/html` returns 404 |
| Port `9090` | Fake Grafana endpoint returns 503 |
| Port `8082` | Chisel decoy with a 30-second timeout; described as decommissioned |
| `old_password_reset.eml` | Contains an outdated 2025 password |
| `hd-9999.txt` | Claims `admin123`, which has been rotated |
| `random.txt` | References the incorrect address `192.168.99.99:8200` |
| Fake kernel version | Reports `4.15.0`; misleading for exploit selection |
| WAF rules | Block selected strings such as `UNION` and `SELECT` while allowing other suspicious patterns |

**Training point:** do not treat every clue as trustworthy. Correlate dates, identities, service responses, network location and supporting evidence before accepting a finding.

---

## Tooling

The lab exercises common tools used in security assessment and investigation.

| Tool | Purpose |
|---|---|
| `nmap` | Port and service enumeration |
| `curl` | HTTP requests and response inspection |
| `dirb` | Web content discovery |
| `sqlmap` | Controlled SQL injection validation |
| `hydra` | Lab authentication testing |
| `hashcat` | Offline challenge-response analysis |
| `proxychains4` | Routing supported tools through a SOCKS proxy |
| `ssh` | SSH access and dynamic port forwarding |
| `smbclient` | SMB share enumeration |
| `ftp` | FTP service interaction |
| `vault` | Vault interaction during the final scenario |
| Metasploit | Optional framework-based service investigation, where applicable |

### Kali prerequisites

Recommended platform: Kali Linux 2024.1 or later.

The lab documentation specifies:

- Docker Engine 24 or later (28.x verified)
- Docker Compose v2 (v2.40+ verified)
- 8 GB RAM minimum, 16 GB recommended
- 10 GB free disk space minimum, 20 GB recommended
- Internet access on first build (base images plus verified chisel, Vault and vsftpd downloads)

Resource figures are based on the current Compose stack (nine long-running
services plus a one-shot initialiser) and were validated by building and
resetting the full project. See `installguide.md` for details.

Check installed versions:

```bash
docker --version
docker compose version
```

Check tool availability:

```bash
for tool in nmap curl dirb sqlmap hydra hashcat proxychains4 \
            ssh smbclient ftp; do
    command -v "$tool" || echo "Missing: $tool"
done
```

Install missing Kali packages as required:

```bash
sudo apt update
sudo apt install -y nmap curl dirb sqlmap hydra hashcat \
    proxychains4 smbclient ftp
```

Install and use only the tools needed for the exercise. Avoid putting real credentials in shell history or reusable scripts.

---

## Setup and launch

Run these commands from the root of the Stillbrook repository.

### Option A — Build and start from source

If you already have the repository locally:

```bash
cd ~/Stillbrook-GitHub
```

Review the environment template and create the local environment file if required by the Compose configuration:

```bash
cp .env.example .env
```

Build and start the services:

```bash
docker compose up -d --build
```

> If `.env.example` is not present in your current checkout, do not create an empty `.env` blindly. Inspect `docker-compose.yml` and `installguide.md` to identify the required variables first.

### Option B — Start from a clean lab state

The project provides a reset script:

```bash
./scripts/reset_lab.sh
```

The reset script is intended to:

1. Stop and remove Compose containers and volumes.
2. Re-seed the application database.
3. Restart the services.
4. Re-initialise Gitea.
5. Run the one-shot Vault initialisation.
6. Generate new unseal material and the final objective.
7. Verify the lab services and report key-retrieval locations.

> [!CAUTION]
> The reset process runs `docker compose down -v --remove-orphans`. The `-v` option removes Compose-managed volumes. This destroys persistent lab state. Back up anything you need before resetting.

### Verify the deployment

```bash
docker compose ps
docker compose logs --tail=100
nmap -p 21,80,443,2222,8080,9090 127.0.0.1
```

Expected result: the lab's services are running and the six intended published ports are reachable on localhost. Confirm container health from the actual Compose output; a port scan alone does not prove application health.

---

## Network isolation

The `internal` Docker network is configured with `internal: true`. This restricts external connectivity for containers attached to that network, but the Docker host may still have a bridge interface on the internal subnet.

The project includes a host-side isolation helper:

```bash
./scripts/lab_isolation.sh install
./scripts/lab_isolation.sh status
./scripts/lab_isolation.sh remove
```

| Command | Purpose |
|---|---|
| `install` | Install the lab's host-side isolation rules |
| `status` | Display the current rule status |
| `remove` | Remove rules managed by the helper |

Review `scripts/lab_isolation.sh` before running it. Firewall changes can affect other Docker workloads and host connectivity. Do not flush the host firewall as a shortcut. Verify the resulting rules and maintain a recovery path.

---

## Vault secrets management

Vault runs in **development mode** (`vault server -dev`) on the internal
network only. This is a deliberate design choice for a reset-driven lab:
dev mode auto-initialises with a single bootstrap share that the one-shot
`vault-init` service then rekeys to a genuine 3-of-3 Shamir quorum. The
consequences are documented in `docs/ARCHITECTURE.md`: state uses the
in-memory backend and is lost when the container is recreated, and dev mode
is not suitable for production. The lab is not production software.

The Vault root token is generated at container start by
`docker/vaulthost/entrypoint.sh`:

- It is a fresh runtime value, not a committed secret.
- It is written to `/vault/.vault_token` with permissions `0600`.
- The dev-mode startup banner (which contains the bootstrap unseal key and
  root token) is redirected to a root-only `/vault/dev-bootstrap.log`, not
  to `docker logs`.
- It is not hard-coded in `docker-compose.yml`, Dockerfiles or application
  source, and is not automatically available to a host-side Vault CLI call.

The three Shamir unseal-key *handles* are distributed across three lab
services — PostgreSQL, the Samba executive share and the SSH jumpbox — while
the real shares stay container-local in a root-only key map. The handles and
the final flag are regenerated on every full reset. See
`docs/ARCHITECTURE.md` and `AUDIT_REPORT/14_POST_RESET_VERIFICATION.md`.

> **Secret-handling note:** generated tokens, unseal keys, private SSH keys and planted credentials are sensitive lab artefacts. Never reuse them outside this environment. Before publishing the repository, verify that no real credentials or reusable private keys are included.

---

## Evidence collection and blue-team exercises

Stillbrook can be used to practise building an incident narrative from multiple evidence sources.

| Activity | Evidence to preserve | Defensive question |
|---|---|---|
| Reconnaissance | Scan output, banners and timestamps | Were unexpected services exposed? |
| Web discovery | HTTP requests, response codes and access logs | Was sensitive content enumerated? |
| Authentication | Login failures, successes and source addresses | Were brute-force or password-spraying patterns visible? |
| IDOR testing | Request paths, user context and object identifiers | Was object-level authorisation enforced? |
| SQL injection | Request parameters, timing and application logs | Could anomalous query behaviour be detected? |
| Webshell access | Web logs and process telemetry | Did a web process execute unexpected commands? |
| Repository investigation | Git access records and exposed artefacts | Were secrets committed or made accessible? |
| Credential attacks | Authentication logs and account events | Were abnormal authentication attempts detected? |
| Pivoting | SSH, SOCKS and network connection records | Could internal access be linked to the initial foothold? |
| Privilege escalation | SUID execution, sudo logs and cron changes | Was a privilege boundary crossed unexpectedly? |
| Vault activity | Vault audit and unseal events | Was sensitive administrative activity authorised? |

### Recommended blue-team deliverables

At the end of the exercise, produce:

1. Executive incident summary.
2. Chronological attack timeline.
3. Asset and service inventory.
4. Evidence register, including timestamps and hashes.
5. Findings with impact and supporting evidence.
6. MITRE ATT&CK mappings where appropriate.
7. Detection hypotheses and relevant event fields.
8. Prioritised remediation plan.
9. Lessons-learned summary.

A detection should not be described as effective until it has been tested against representative malicious and benign activity.

---

## Repository structure

The following tree is a curated overview based on the supplied repository listing. It highlights the main application, infrastructure, story, logging and training components rather than reproducing every Git object and sample file.

```text
Stillbrook-GitHub/
├── app/
│   ├── auth/
│   ├── dashboard/
│   ├── engineering/
│   ├── finance/
│   ├── scoring/
│   ├── story/
│   ├── access_control.py
│   ├── db.py
│   ├── detection_loader.py
│   └── logging_utils.py
├── config/
│   └── medium.yaml
├── database/
├── docker/
│   ├── db/
│   ├── git/
│   │   └── repo/
│   │       └── secrets/
│   ├── redis/
│   ├── router/
│   ├── samba/
│   ├── ssh/
│   ├── tools/
│   ├── vault/
│   │   └── init/
│   ├── vaulthost/
│   │   ├── flags/
│   │   ├── vault-reader.c
│   │   └── vault_rotate.sh
│   ├── vsftpd/
│   └── web/
├── docs/
│   └── architecture/
├── AUDIT_REPORT/
├── logging/
│   └── detections/
├── screenshots/
├── scripts/
│   ├── init_gitea.sh
│   ├── lab_isolation.sh
│   └── reset_lab.sh
├── seed/
│   ├── acl_rules.yaml
│   ├── seed_db.py
│   └── users.yaml
├── story/
│   ├── chats/
│   ├── cmdb/
│   ├── emails/
│   ├── hr/
│   ├── logs/
│   ├── noise/
│   ├── projects/
│   ├── reports/
│   ├── shares/
│   ├── tickets/
│   └── vault/
├── templates/
│   ├── auth/
│   ├── dashboard/
│   ├── engineering/
│   ├── finance/
│   └── layout.html
├── tools/
│   └── make_vsftpd_patch.py
├── app.py
├── docker-compose.yml
├── Dockerfile
├── installguide.md
├── README.md
├── requirements.txt
└── stillbrook_wsgi.py
```

### Important repository hygiene

The lab intentionally contains sensitive-looking artefacts that are part of
the training experience:

- `docker/git/repo/secrets/ntlm_3f7a2b1c.txt` — a synthetic NTLM hash planted
  for the offline-cracking challenge.
- `docker/vaulthost/flags/` — synthetic proof-of-completion markers for the
  privilege-escalation stages.
- `docker-compose.yml`, `.env.example`, `seed/users.yaml` — synthetic lab
  credentials used only inside the isolated environment.

Private SSH keys and host keys are **never committed**: they are generated
at container startup by the vault-host entrypoint and shared through a
Docker volume. Historical private keys were removed from Git history before
publication; see `AUDIT_REPORT/15_GIT_HISTORY_SECURITY.md`. Generated runtime
state (`.env`, `.db` files, logs, the live Samba checklist and Python caches)
is covered by `.gitignore` and is not part of a fresh clone.

---

## Reset and teardown

### Full reset

```bash
./scripts/reset_lab.sh
```

A full reset is intended to rebuild the challenge state, regenerate credentials and flags, and reinitialise dependent services. It is destructive to Compose-managed volumes.

### Stop containers

```bash
docker compose down
```

### Remove containers and volumes

```bash
docker compose down -v --remove-orphans
```

Use the final command only when you intentionally want to delete persistent lab data.

---

## Troubleshooting

### Containers fail to start

```bash
docker compose ps
docker compose logs --tail=150
docker compose config
```

Check for invalid Compose configuration, missing environment variables, build failures, port conflicts and insufficient disk space.

### A published port is unavailable

```bash
ss -lntp
docker compose ps
nmap -p 21,80,443,2222,8080,9090 127.0.0.1
```

Confirm that the corresponding container is running and that the port is bound to the expected loopback address.

### The application is not ready

```bash
docker compose logs --tail=200
```

Check the web, database and initialisation service logs. A running container does not necessarily mean the application inside it is ready.

### Isolation rules affect other workloads

```bash
./scripts/lab_isolation.sh status
```

Inspect the helper and host firewall rules before making changes. Avoid broad firewall flushes or changes that could disrupt unrelated containers.

### The lab state is inconsistent

If you do not need to preserve the current state, use the full reset script. Remember that it removes Compose-managed volumes and regenerates lab data.

---

## Responsible-use policy

- Use Stillbrook only in an isolated environment you control.
- Keep the six published ports bound to `127.0.0.1`.
- Do not connect the vulnerable environment to production networks.
- Do not reuse challenge credentials on real systems.
- Protect generated keys, tokens and other challenge artefacts.
- Review Docker, firewall and reset scripts before execution.
- Obtain permission before running the lab on shared infrastructure.
- Stop the environment when the exercise is complete.

## License and disclaimer

## License

Copyright 2026 Shankar M

Stillbrook's original project code, documentation and original materials are licensed under the **Apache License, Version 2.0**.

You may use, modify and distribute this work under the terms and conditions of the Apache License 2.0.

A copy of the license is available in the [`LICENSE`](LICENSE) file.

You can also read the license here:

https://www.apache.org/licenses/LICENSE-2.0

**Third-party components:** Stillbrook includes or uses third-party software and dependencies. Those components remain subject to their respective copyright notices and license terms. The Apache License applied to Stillbrook does not replace or override third-party licenses.

## Disclaimer and responsible use

Stillbrook is an intentionally vulnerable cybersecurity training environment designed exclusively for educational purposes and authorised security testing.

- Use the environment only on systems and networks you own or have explicit permission to test.
- Keep the lab isolated and do not expose vulnerable services to the public internet.
- Do not reuse synthetic challenge credentials outside the lab.
- Review Docker, firewall and reset scripts before execution.
- Users are responsible for their deployment, configuration and use of the environment.

Stillbrook is provided on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, as described in the Apache License 2.0.

The author is not responsible for misuse, unauthorised activity, damage or data loss resulting from deployment or use of this training environment.

---

<div align="center">

**STILLBROOK — ENTERPRISE SECURITY TRAINING ENVIRONMENT**

*Explore the attack path · Preserve the evidence · Strengthen the defence*

</div>
