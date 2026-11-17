# 17 — Redundant Repository Investigation (Stillbrook)

**Date:** 2026-11-17
**Scope:** `docker/gitea_repos/stillbrook/web.git` (legacy bare Git repository).
**Method:** Reference search, history/content comparison and dependency review.

---

## 0. Summary

`docker/gitea_repos/` was a stale, prebuilt bare repository that is not
referenced by any Dockerfile, Compose mount, entrypoint or initialisation
script. `scripts/init_gitea.sh` builds the challenge repository from scratch
using `docker/git/repo/` and a real two-commit history, so the bare repository
duplicated challenge data with **different, obsolete content**. It also
contained a stale personal filesystem path in its `config`. It was backed up
and removed. Gitea challenge behaviour is unchanged because nothing used it.

---

## 1. Dependency investigation

| Check | Result |
|---|---|
| Referenced in any Dockerfile? | No. |
| Mounted by `docker-compose.yml`? | No — Gitea uses the `gitea_data` named volume only. |
| Used by `scripts/init_gitea.sh`? | No — it uses `docker/git/repo/` and `docker cp`. |
| Used by `reset_lab.sh` / any entrypoint / init script? | No. |
| Referenced in source code / config? | No — only in `README.md`'s structure tree and audit docs. |
| Does it hold Git history required by a challenge? | No. The live Gitea history is generated at reset; the bare repo had its own, different history (see below). |
| Generated automatically? | No — it was committed legacy content. |
| Does it duplicate another repository? | Yes — an obsolete duplicate of the Gitea challenge idea. |

Reference search (excluding `.git`) found only documentation mentions.

---

## 2. Content comparison

Bare repository history (subject lines only):

- `02f297e` Initial commit
- `6411c36` Add environment config

Both commits contained `.env`, `README.md`, `app.py` and `config.py`, and the
repository lacked the `secrets/ntlm_3f7a2b1c.txt` artifact.

By contrast, `scripts/init_gitea.sh` generates the repository that the lab
actually uses:

- commit 1 adds app files plus an accidentally committed `.env`;
- commit 2 removes `.env` from the tree (still recoverable from history);
- `secrets/ntlm_3f7a2b1c.txt` is present as the planted NTLM artifact.

The bare repo was therefore stale and not a source for the working challenge.

Its `.git/config` also contained a developer-specific absolute path from a
personal machine. That path had no function in the lab and is one more reason
to exclude the directory from a public release.

---

## 3. Actions taken

1. Backed up the complete directory (including its internal `.git`) to
   `/tmp/opencode/stillbrook-gitea_repos-backup-<timestamp>.tar.gz`
   (44 entries, verified).
2. Removed `docker/gitea_repos/` from the Git index and working tree.
3. Updated `README.md`'s repository-structure overview to drop the entry.
4. Confirmed no remaining code/config references.

No challenge files, flags, hashes or functionality were removed. The working
Gitea challenge data (`docker/git/repo/` and `scripts/init_gitea.sh`) is
unchanged.

---

## 4. Recovery procedure

If the legacy repository is ever needed, restore it from the backup:

```bash
cd ~/Stillbrook-GitHub
tar xzf /tmp/opencode/stillbrook-gitea_repos-backup-<timestamp>.tar.gz
```

It is not needed to build, run or reset Stillbrook.

---

## 5. Verification

- `grep -rn gitea_repos` (excluding `.git`) — only documentation references
  remain; no build/runtime dependency.
- `docker compose config` and the Gitea challenge checks are re-run during
  the functional regression (`AUDIT_REPORT/18_FINAL_GITHUB_RELEASE_READINESS.md`).
- The Gitea history check (`git ls-remote` and `.env` recoverability from
  history) is performed by `scripts/reset_lab.sh` and Phase 8 testing.

---

## 6. Conclusion

The directory was genuinely redundant and has been safely removed. This item
is not a release blocker.
