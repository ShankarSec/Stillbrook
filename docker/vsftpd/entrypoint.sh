#!/bin/sh
# =====================================================================
# Stillbrook -- vsftpd entrypoint
#
# vsftpd wants to own port 21 and to fork its privileged helper, so it
# starts as root and drops to "nobody" itself.
#
# The backdoor also exposes its classic shell listener on container
# port 6200 (nmap's ftp-vsftpd-backdoor script probes that port first).
# It is container-local -- never published to the host.
# =====================================================================
set -e

# The backdoor shell listener: a shell on 6200 as "nobody".
su -s /bin/sh nobody -c \
    'exec socat TCP-LISTEN:6200,reuseaddr,fork EXEC:/bin/sh' >/dev/null 2>&1 &

exec /usr/sbin/vsftpd /etc/vsftpd.conf
