# =====================================================================
# Stillbrook -- vault host (Stage 9)
#
# Vault and the SSH service that fronts it live in the same container.
# The player pivots through the internal router to reach this host.
#
#   sshd    -> port 2224 (vault_svc, key authentication only)
#   vault   -> port 8200 (dev mode)
#
# Escalation paths:
#   /usr/local/bin/vault-reader   SUID root helper
#   sudo /usr/bin/less             passwordless sudo escape
#   /opt/scripts/vault_rotate.sh   world-writable cron script
#
# The router<->vault-host keypair and the SSH host key are generated at
# RUNTIME by entrypoint.sh. No private key is baked into this image or
# committed to Git.
# =====================================================================

# --- build stage: the SUID helper -------------------------------------
FROM ubuntu:22.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY vault-reader.c /build/vault-reader.c
RUN gcc -O2 -Wall -Wextra -o /build/vault-reader /build/vault-reader.c && \
    strip /build/vault-reader

# --- runtime stage ------------------------------------------------------
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV VAULT_DEV_LISTEN_ADDRESS="0.0.0.0:8200"
ENV VAULT_ADDR="http://127.0.0.1:8200"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        cron \
        curl \
        less \
        e2fsprogs \
        openssh-client \
        openssh-server \
        sudo \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# --- vault 1.15 (checksum verified) ------------------------------------
ARG VAULT_VERSION=1.15.6
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
        amd64) vault_arch=amd64 ;; \
        arm64) vault_arch=arm64 ;; \
        *)     vault_arch="$(dpkg --print-architecture)" ;; \
    esac; \
    cd /tmp; \
    curl -fsSL -o "vault_${VAULT_VERSION}_linux_${vault_arch}.zip" \
        "https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_${vault_arch}.zip"; \
    curl -fsSL -o SHA256SUMS \
        "https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_SHA256SUMS"; \
    grep "vault_${VAULT_VERSION}_linux_${vault_arch}.zip" SHA256SUMS | sha256sum -c -; \
    unzip -o "vault_${VAULT_VERSION}_linux_${vault_arch}.zip" vault; \
    install -m 0755 vault /usr/local/bin/vault; \
    rm -f "vault_${VAULT_VERSION}_linux_${vault_arch}.zip" SHA256SUMS vault; \
    vault version

# --- vault_svc account --------------------------------------------------
RUN useradd --create-home --shell /bin/bash vault_svc && \
    mkdir -p /home/vault_svc/.ssh /run/sshd /vault/data /opt/scripts /shared && \
    chown -R vault_svc:vault_svc /home/vault_svc && \
    chmod 0700 /home/vault_svc/.ssh && \
    chown root:root /vault /vault/data /opt/scripts /shared

# --- sshd on port 2224, key auth only ----------------------------------
# The host key is generated at runtime by entrypoint.sh.
RUN rm -f /etc/ssh/ssh_host_* && \
    printf 'HostKey /etc/ssh/ssh_host_ed25519_key\n' >> /etc/ssh/sshd_config && \
    sed -i 's/^#\?Port .*/Port 2224/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PermitEmptyPasswords.*/PermitEmptyPasswords no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# --- SUID helper ---------------------------------------------------------
COPY --from=builder /build/vault-reader /usr/local/bin/vault-reader
COPY vault-reader.c /usr/local/src/vault-reader.c
RUN chown root:root /usr/local/bin/vault-reader && \
    chmod 4755 /usr/local/bin/vault-reader && \
    chown root:root /usr/local/src/vault-reader.c && \
    chmod 0644 /usr/local/src/vault-reader.c

# --- passwordless sudo for the "less" escape ----------------------------
RUN printf 'vault_svc ALL=(root) NOPASSWD: /usr/bin/less\n' > /etc/sudoers.d/vault_svc && \
    chown root:root /etc/sudoers.d/vault_svc && \
    chmod 0440 /etc/sudoers.d/vault_svc && \
    visudo -c

# --- challenge flags (intentional synthetic challenge data) -------------
COPY flags/suid_flag.txt    /vault/data/suid_flag.txt
COPY flags/keys.env         /vault/data/keys.env
COPY flags/sudo_flag.txt    /root/sudo_flag.txt
COPY flags/cron_flag.txt    /root/cron_flag.txt
COPY flags/tunnel_proof.txt /opt/tunnel_proof.txt

RUN chown root:root /vault/data/suid_flag.txt /vault/data/keys.env \
        /root/sudo_flag.txt /root/cron_flag.txt /opt/tunnel_proof.txt && \
    chmod 0600 /vault/data/suid_flag.txt /vault/data/keys.env && \
    chmod 0644 /opt/tunnel_proof.txt && \
    chmod 0600 /root/sudo_flag.txt /root/cron_flag.txt

# --- cron: vault_rotate.sh every 5 minutes as root ----------------------
COPY vault_rotate.sh /opt/scripts/vault_rotate.sh
RUN chown root:root /opt/scripts/vault_rotate.sh && \
    chmod 0666 /opt/scripts/vault_rotate.sh

COPY cron-vault-rotate /etc/cron.d/vault_rotate
RUN chown root:root /etc/cron.d/vault_rotate && \
    chmod 0644 /etc/cron.d/vault_rotate

# --- faked /proc/version -------------------------------------------------
COPY rc.local /etc/rc.local
RUN chown root:root /etc/rc.local && chmod 0755 /etc/rc.local

COPY proc-version /usr/local/bin/proc-version
RUN chown root:root /usr/local/bin/proc-version && chmod 0755 /usr/local/bin/proc-version

COPY entrypoint.sh /usr/local/bin/vaulthost-entrypoint.sh
RUN chmod 0755 /usr/local/bin/vaulthost-entrypoint.sh

EXPOSE 2224 8200

ENTRYPOINT ["/usr/local/bin/vaulthost-entrypoint.sh"]
