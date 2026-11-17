# Stillbrook SMB file server (Stage 6/8 - unseal key 2)
#
# WHY A LOCAL IMAGE?
#   The lab originally targeted `bitnami/samba:4.19`, but Bitnami pulled
#   their public catalogue off Docker Hub in 2025 (bitnami/samba and
#   bitnamilegacy/samba now both answer "pull access denied"), so that image
#   can no longer be pulled. This image keeps the *exact same contract* the
#   lab depends on:
#
#     env SAMBA_SHARE_NAME       name of the shared folder
#     env SAMBA_SHARED_USER      SMB account allowed on that share
#     env SAMBA_SHARED_PASSWORD  password for that account
#     path /volume/samba/<share> on-disk location of the share
#
#   Samba 4.19 (Alpine 3.20 main) is used so the SMB server version still
#   matches the 4.19 series the attack chain documents.
FROM alpine:3.20

RUN apk add --no-cache samba=4.19.9-r0 samba-common-tools && \
    mkdir -p /volume/samba /var/lib/samba/private /var/log/samba && \
    chmod 0755 /var/lib/samba/private

COPY entrypoint.sh /usr/local/bin/samba-entrypoint.sh
RUN chmod 0755 /usr/local/bin/samba-entrypoint.sh

EXPOSE 445

ENTRYPOINT ["/usr/local/bin/samba-entrypoint.sh"]
