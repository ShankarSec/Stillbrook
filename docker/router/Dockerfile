# =====================================================================
# Stillbrook -- internal router (Stage 9: chisel pivot + vault gateway)
#
#   player --> chisel tunnel --> internal-router:2223 --(ssh key)-->
#            vault-host:2224
#
# The container is attached to the "internal" docker network only.
# The SSH key for the vault-host hop is generated at RUNTIME by the
# vault-host entrypoint and shared through the `vault_shared` volume;
# no private key is baked into this image or committed to Git.
# =====================================================================
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# --- base tooling -----------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        cron \
        curl \
        gzip \
        openssh-client \
        openssh-server \
        procps \
    && rm -rf /var/lib/apt/lists/*

# --- chisel v1.10.1 (the tunnel server) -------------------------------
ARG CHISEL_VERSION=1.10.1
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
        amd64) chisel_arch=amd64 ;; \
        arm64) chisel_arch=arm64 ;; \
        *)     chisel_arch="$(dpkg --print-architecture)" ;; \
    esac; \
    curl -fsSL -o /tmp/chisel.gz \
        "https://github.com/jpillora/chisel/releases/download/v${CHISEL_VERSION}/chisel_${CHISEL_VERSION}_linux_${chisel_arch}.gz"; \
    gunzip -c /tmp/chisel.gz > /usr/local/bin/chisel; \
    chmod 0755 /usr/local/bin/chisel; \
    rm -f /tmp/chisel.gz; \
    chisel --version

# --- svc_router account ------------------------------------------------
RUN useradd --create-home --shell /bin/bash svc_router && \
    echo 'svc_router:Phoenix_DR#2026' | chpasswd && \
    mkdir -p /home/svc_router/.ssh /run/sshd /opt/scripts /var/log && \
    chmod 0700 /home/svc_router/.ssh && \
    touch /var/log/healthcheck.log && \
    chmod 0666 /var/log/healthcheck.log

# --- sshd on port 2223 -------------------------------------------------
RUN sed -i 's/^#\?Port .*/Port 2223/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    ssh-keygen -A

# --- ssh client config for the runtime-generated key ------------------
# No private key or known_hosts is baked into the image. The key is
# copied from the shared volume by the entrypoint at startup.
RUN printf 'Host vault-host\n    HostName vault-host\n    Port 2224\n    User vault_svc\n    IdentityFile /home/svc_router/.ssh/id_rsa\n    StrictHostKeyChecking no\n    UserKnownHostsFile /dev/null\n' \
        > /home/svc_router/.ssh/config

COPY welcome.txt   /home/svc_router/welcome.txt
COPY users.json    /home/svc_router/users.json
COPY healthcheck.sh /opt/scripts/healthcheck.sh

RUN chown -R svc_router:svc_router /home/svc_router && \
    chmod 0600 /home/svc_router/.ssh/config && \
    chmod 0644 /home/svc_router/welcome.txt && \
    chmod 0644 /home/svc_router/users.json && \
    chmod 0666 /opt/scripts/healthcheck.sh

# --- cron: healthcheck.sh every 5 minutes as root ---------------------
COPY cron-stillbrook-healthcheck /etc/cron.d/stillbrook-healthcheck
RUN chown root:root /etc/cron.d/stillbrook-healthcheck && \
    chmod 0644 /etc/cron.d/stillbrook-healthcheck

COPY entrypoint.sh /usr/local/bin/router-entrypoint.sh
RUN chmod 0755 /usr/local/bin/router-entrypoint.sh

EXPOSE 2223 8081

ENTRYPOINT ["/usr/local/bin/router-entrypoint.sh"]
