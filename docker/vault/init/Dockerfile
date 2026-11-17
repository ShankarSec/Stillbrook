# Stillbrook one-shot Vault initialiser (Sprint 7 / Stage 8)
#
# Built on the stock vault image so the `vault` CLI is already present.
# Extra tooling needed by docker/vault/init/vault-init.sh:
#   postgresql-client -> write unseal key 1 into PostgreSQL
#   docker-cli        -> read the vault boot log, seed the jumpbox history
#   samba-client      -> verify the executive share over real SMB
#   curl + jq         -> drive the Vault HTTP API (rekey / seal / unseal)
FROM hashicorp/vault:1.15

USER root

RUN apk add --no-cache curl jq postgresql-client docker-cli samba-client

WORKDIR /vault-init

ENTRYPOINT ["/bin/sh", "/vault-init/vault-init.sh"]
