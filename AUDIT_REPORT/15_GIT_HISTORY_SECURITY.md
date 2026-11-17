# 15 — Git History Security Audit (Stillbrook)

**Date:** 2026-11-17
**Scope:** Working tree, index, all commits, historical blobs, deleted files,
branches/tags and publication-relevant Git configuration.
**Method:** `git status`, `git ls-tree`, `git grep` over all revisions,
blob inspection by pattern (no secret values printed), and a controlled
single-commit rebuild after a verified backup.

---

## 0. Executive summary

The repository originally had a single commit (`8463c68`) containing two
genuine SSH private keys. They had already been deleted from the working
tree/index and replaced with runtime-generated keys, but remained recoverable
from Git history. No other private keys, API tokens, cloud keys or real
credentials were found. All other secret-looking strings are synthetic lab
credentials that are intentional and required.

A verified full backup (including `.git`) was taken, a recovery procedure was
established, and the history was rewritten into a single clean root commit.
The original commit and both private-key blobs were purged. The cleaned
history contains zero private-key material, `git fsck` is clean, and the
working tree is clean. **Git history is now safe for public release.**

No secret values are reproduced in this report.

---

## 1. State at the start of the audit

- One branch (`master`), no tags, no remotes configured.
- One commit: `8463c68 Initial public release of Stillbrook Cyber Range`.
- Working tree/index already contained the previous audit's fixes; the
  private-key files were staged as deleted and regenerated at runtime.

### Affected files in the original commit

| Path | Type | Classification | In working tree at start? |
|---|---|---|---|
| `docker/router/id_rsa` | OpenSSH RSA private key (3401 B) | **A — actual private key** | No (deleted, runtime-generated) |
| `docker/vaulthost/ssh_host_ed25519_key` | OpenSSH ED25519 private key (411 B) | **A — actual private key** | No (deleted, runtime-generated) |
| `docker/router/id_rsa.pub` | Public key | D — harmless public material | No (deleted, runtime-generated) |
| `docker/router/known_hosts` | Host fingerprints | D — harmless config | No (deleted, runtime-generated) |
| `docker/router/ssh_config` | Client config | D — harmless config | No (deleted, runtime-generated) |
| `docker/vaulthost/authorized_keys` | Public-key list | D — harmless public material | No (deleted, runtime-generated) |
| `docker/vaulthost/ssh_host_ed25519_key.pub` | Public key | D — harmless public material | No (deleted, runtime-generated) |

Only the two private-key files were treated as sensitive historical material.
The public/config files were removed from the tree for consistency with the
runtime-generation design, but they are not secrets.

### Classification of other matches

- `POSTGRES_PASSWORD`, `DB_PASSWORD`, Samba `admin123`, Gitea
  `SECRET_KEY`, `.env.example` values — **B — synthetic challenge
  credentials**, intentional and required. Do not remove.
- `docker/git/repo/secrets/ntlm_3f7a2b1c.txt` — **B — synthetic NTLM hash**
  planted for the offline-cracking challenge. Required.
- `docker/vaulthost/flags/*` — **B — synthetic proof markers**. Required.
- `story/vault/final_flag.txt` — **B — synthetic final flag**. Required.
- Vault tokens / unseal handles — generated at runtime, not committed
  (**C**). `keys.env` in the repo is a placeholder, not a live key map.
- `.env` is git-ignored and was never committed.

Pattern scan across all revisions found no AWS/GitHub/Slack/Google/Stripe
token signatures, no JWTs, and no other PEM private-key blocks.

---

## 2. Runtime replacements (verified before cleanup)

- `docker/vaulthost/entrypoint.sh` generates the router↔Vault RSA keypair
  into `vault_shared:/shared/id_rsa` and an ED25519 SSH host key into
  `/etc/ssh/ssh_host_ed25519_key` (mode `0600`) on every fresh start.
- `docker/router/entrypoint.sh` copies the key from the shared volume and
  writes `~/.ssh/config` with `IdentityFile`/`StrictHostKeyChecking no`; no
  key is baked into the image.
- Fresh containers started from the images contain no private keys (verified
  in the prior post-reset audit).
- Router→Vault key auth and host→jumpbox password auth were re-confirmed in
  Phase 8 of this release audit.

Therefore the historical keys were redundant and safe to purge.

---

## 3. Backup and recovery procedure

Before rewriting history, a complete archive of the repository (including
`.git`) was created and verified:

```bash
cd /tmp/opencode
tar czf stillbrook-backup-<timestamp>.tar.gz -C /home/kali Stillbrook-GitHub
sha256sum stillbrook-backup-<timestamp>.tar.gz
tar tzf stillbrook-backup-<timestamp>.tar.gz | grep -E \
  'Stillbrook-GitHub/\.git/(index|HEAD|refs/heads/master)$'
```

Verified: 845 entries, `.git/index`, `.git/HEAD`, branch ref and 480 Git
objects present. A trial extraction to `/tmp/opencode/verify-restore` passed
`git fsck --full` and reproduced the original commit. The backup intentionally
still contains the two historical keys — it is the recovery source.

**Recovery procedure** (only if the rewrite must be undone):

```bash
cd /tmp/opencode
rm -rf restore-here && mkdir restore-here
tar xzf stillbrook-backup-<timestamp>.tar.gz -C restore-here
cd restore-here/Stillbrook-GitHub
git fsck --full            # verifies recovered history
```

The recovered repo is the pre-cleanup state; review before use.

---

## 4. Cleanup plan and execution

Because the repository had exactly one commit, the lowest-risk cleanup was a
controlled rebuild of that root commit rather than a multi-commit filter.

1. Staged the complete final working tree with `git add -A`.
2. Verified the index contained no ignored artifacts and no private-key
   headers (`git grep --cached`).
3. Rewrote the single root commit with `git commit --amend --no-edit`,
   preserving the original commit message and author.
4. Purged unreachable objects:
   `git reflog expire --expire=now --all && git gc --prune=now --aggressive`.
5. Did **not** push or configure any remote.

All legitimate source files, challenge artefacts and history (including the
separate Gitea challenge history in `scripts/init_gitea.sh`) were preserved.
Only the confirmed sensitive historical material was removed.

---

## 5. Verification commands and results

| Command | Result |
|---|---|
| `git rev-list --all --count` | 1 (single clean root commit) |
| `git grep -l -I -E 'BEGIN ... PRIVATE KEY' $(git rev-list --all)` | 0 files |
| Old commit `8463c68...` reachable? | No (pruned) |
| Old key blobs `03399a7...` / `10160c6...` in object DB? | Purged / Purged |
| `git fsck --full` (including dangling) | Clean, no output |
| `git status --short` | Clean |
| New commit | single clean root commit (hash changes if reports are amended) |
| Real-secret signature scan (AWS/GitHub/Slack/JWT/etc.) | 0 matches |
| Personal absolute paths in tracked files | 0 (stale Gitea repo removed) |

Raw secret values were never printed; only hashes, booleans and counts.

---

## 6. Remaining risks

- The historical private keys were disclosed in the original commit. They
  are synthetic lab keys with no external trust and are no longer used; the
  runtime generates fresh keys on every reset. Rotation is therefore
  inherent. Anyone holding a copy of the original commit (the backup) should
  treat it as sensitive.
- Synthetic lab credentials are intentionally embedded in source and
  documentation. They are not real secrets, but users must not reuse them.
- A future `git push` must be made from the cleaned repository, never from the
  backup copy.

---

## 7. Verdict

**Git history is safe for public release.** No actual private keys or real
secrets remain in any reachable commit, the object database is clean, and the
working tree reproduces a fully functional lab (verified in the regression
and fresh-clone phases recorded in
`AUDIT_REPORT/18_FINAL_GITHUB_RELEASE_READINESS.md`).
