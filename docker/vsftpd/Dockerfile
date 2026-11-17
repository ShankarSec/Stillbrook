# =====================================================================
# Stillbrook -- vsftpd 2.3.4 (backdoored build)
#
# The FTP service is compiled from the original 2.3.4 sources with the
# lab backdoor switched on:
#
#   1. vsftpd-2.3.4-lab.patch adds the hidden account (docker/vsftpd/
#      vsftpd.c) and hooks it into the login handler,
#   2. the classic one character change "#if 0" -> "#if 1" makes the
#      hidden account live,
#   3. the banner promises "any username and password", so every login
#      is accepted and the session runs as "nobody".
#
# The source tarball is vendored (upstream:
# https://ftp.osuosl.org/pub/blfs/conglomeration/vsftpd/) and verified
# against the upstream sha256 below.
# =====================================================================

# --- build stage -------------------------------------------------------
FROM ubuntu:22.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        libpam0g-dev \
        patch \
    && rm -rf /var/lib/apt/lists/*

ARG VSFTPD_VERSION=2.3.4
ARG VSFTPD_SHA256=b466edf96437afa2b2bea6981d4ab8b0204b83ca0a2ac94bef6b62b42cc71a5a

WORKDIR /src
COPY vsftpd-${VSFTPD_VERSION}.tar.gz /src/vsftpd.tar.gz
RUN echo "${VSFTPD_SHA256}  /src/vsftpd.tar.gz" | sha256sum -c - && \
    tar xzf /src/vsftpd.tar.gz && \
    mv "/src/vsftpd-${VSFTPD_VERSION}" /src/vsftpd

# --- apply the lab backdoor --------------------------------------------
COPY vsftpd-2.3.4-lab.patch /lab/vsftpd-2.3.4-lab.patch
RUN set -eux; \
    cd /src/vsftpd; \
    patch -p1 < /lab/vsftpd-2.3.4-lab.patch; \
    # the classic change: the hidden account goes live
    sed -i 's/^#if 0$/#if 1/' vsftpd.c; \
    grep -n '^#if 1' vsftpd.c; \
    make LIBS="-lpam"; \
    ./vsftpd --help 2>&1 | head -3 || true

# --- runtime stage ------------------------------------------------------
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpam0g \
        procps \
        socat \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /src/vsftpd/vsftpd /usr/sbin/vsftpd
RUN chmod 0755 /usr/sbin/vsftpd

COPY vsftpd.conf /etc/vsftpd.conf
COPY entrypoint.sh /usr/local/bin/vsftpd-entrypoint.sh

# the service account needs a real home directory (vsftpd chdir()s into
# it after the login) and a shell that is listed in /etc/shells
RUN mkdir -p /srv/ftp && \
    usermod --home /srv/ftp --shell /bin/bash nobody && \
    chown nobody:nogroup /srv/ftp && \
    chmod 0755 /usr/local/bin/vsftpd-entrypoint.sh

EXPOSE 21

ENTRYPOINT ["/usr/local/bin/vsftpd-entrypoint.sh"]
