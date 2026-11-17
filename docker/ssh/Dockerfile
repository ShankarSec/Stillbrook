FROM alpine:3.20

# Passwords are injected as build args from .env by docker compose.
ARG MRIVERA_PASS
ARG BACKUPADMIN_PASS

RUN apk add --no-cache openssh-server dante-server socat && \
    adduser -D -s /bin/sh m.rivera && \
    echo "m.rivera:${MRIVERA_PASS}" | chpasswd && \
    adduser -D -s /bin/sh backupadmin && \
    echo "backupadmin:${BACKUPADMIN_PASS}" | chpasswd && \
    sed -i 's/^#\?Port .*/Port 2222/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?AllowTcpForwarding .*/AllowTcpForwarding yes/' /etc/ssh/sshd_config && \
    ssh-keygen -A && \
    mkdir -p /run/sshd /home/m.rivera/.ssh /var/log && \
    touch /var/log/dante.log

COPY .bash_history /home/m.rivera/.bash_history
COPY ssh_config /home/m.rivera/.ssh/config
COPY dante.conf /etc/dante/dante.conf
COPY entrypoint.sh /usr/local/bin/jumpbox-entrypoint.sh

# BusyBox chown treats the first '.' as a user/group separator, so use
# numeric IDs for the dotted username m.rivera.
RUN chown -R "$(id -u m.rivera):$(id -g m.rivera)" /home/m.rivera && \
    chmod 0755 /home/m.rivera && \
    chmod 0644 /home/m.rivera/.bash_history && \
    chmod 0700 /home/m.rivera/.ssh && \
    chmod 0600 /home/m.rivera/.ssh/config && \
    chmod 0644 /etc/dante/dante.conf && \
    chmod 0600 /var/log/dante.log && \
    chmod 0755 /usr/local/bin/jumpbox-entrypoint.sh

EXPOSE 2222 1080 8082

ENTRYPOINT ["/usr/local/bin/jumpbox-entrypoint.sh"]
