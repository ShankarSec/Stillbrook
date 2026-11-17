#!/bin/sh
# Stillbrook SMB server entrypoint.
#
# Creates the shared account, renders /etc/samba/smb.conf from the
# SAMBA_* environment variables and runs smbd in the foreground.
# Nothing is published to the host -- the share is reachable from the
# internal docker network only.
set -e

SHARE_NAME="${SAMBA_SHARE_NAME:-executive}"
SHARED_USER="${SAMBA_SHARED_USER:-admin}"
SHARED_PASSWORD="${SAMBA_SHARED_PASSWORD:-admin123}"
SHARE_PATH="/volume/samba/${SHARE_NAME}"

echo "samba: preparing share '${SHARE_NAME}' at ${SHARE_PATH} for user '${SHARED_USER}'"

mkdir -p "${SHARE_PATH}" /var/lib/samba/private /var/log/samba

# --- shared account --------------------------------------------------------
# A Linux user must back every Samba account (it owns the file access).
if ! id "${SHARED_USER}" >/dev/null 2>&1; then
    adduser -D -H -s /sbin/nologin "${SHARED_USER}"
fi

# Samba passdb entry (tdbsam). -s reads the password from stdin twice.
printf '%s\n%s\n' "${SHARED_PASSWORD}" "${SHARED_PASSWORD}" \
    | smbpasswd -s -a "${SHARED_USER}" >/dev/null 2>&1 || true

# --- smb.conf --------------------------------------------------------------
cat > /etc/samba/smb.conf <<EOF
[global]
   workgroup = WORKGROUP
   server string = Stillbrook Executive File Share
   server role = standalone server
   security = user
   map to guest = never
   guest ok = no
   hosts allow = 0.0.0.0/0
   smb ports = 445
   disable netbios = yes
   deadtime = 0
   encrypt passwords = yes
   change password = no
   ea support = yes
   logging = file
   log file = /var/log/samba/log.%m
   max log size = 1000

[${SHARE_NAME}]
   path = ${SHARE_PATH}
   browseable = yes
   read only = no
   guest ok = no
   valid users = ${SHARED_USER}
   create mask = 0664
   directory mask = 0775
   force user = ${SHARED_USER}
   force group = ${SHARED_USER}
EOF

echo "samba: starting smbd on port 445 (no host port published)"
exec smbd --foreground --no-process-group
