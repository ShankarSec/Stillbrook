#!/bin/sh
# =====================================================================
# Stillbrook -- host side isolation for the "internal" docker network
#
# WHY IS THIS NEEDED?
#   A docker network with `internal: true` stops the *containers* from
#   reaching the outside world, but the host still owns an interface on
#   that bridge and can therefore open connections to the containers
#   directly.  The lab wants the vault host (172.28.0.20) and the
#   internal router (172.28.0.10) to be unreachable from the host, so
#   this script drops that traffic in the host's OUTPUT chain.
#
#   Container to container traffic is untouched (it is bridged inside
#   the network namespace, it never traverses the host firewall), so the
#   lab keeps working: web -> redis/postgres/gitea, vault-init ->
#   vault-host, ssh-jumpbox -> internal-router.
#
# USAGE
#   ./scripts/lab_isolation.sh install    # block the internal subnet
#   ./scripts/lab_isolation.sh remove     # undo
#   ./scripts/lab_isolation.sh status
#
# The rule lives in the host's netfilter table, so it is gone after a
# reboot -- run "install" again after one.
# =====================================================================
set -e

SUBNET="${SUBNET:-172.28.0.0/16}"
CHAIN="OUTPUT"
TARGET="STILLBROOK-INTERNAL"
COMMENT="stillbrook: internal network is not reachable from the host"

# The host firewall is administered through a privileged container that
# shares the host network namespace (the same trick the lab uses for
# anything else that needs host level access).
TOOLS_IMAGE="stillbrook/lab-tools:1.0"
IPT="docker run --rm --privileged --network host ${TOOLS_IMAGE} iptables"

usage() {
    echo "usage: $0 {install|remove|status}   (subnet: ${SUBNET})"
    exit 2
}

[ "$#" -eq 1 ] || usage

# build the helper image on first use
if ! docker image inspect "${TOOLS_IMAGE}" >/dev/null 2>&1; then
    echo "building ${TOOLS_IMAGE} ..."
    docker build -t "${TOOLS_IMAGE}" docker/tools >/dev/null
fi

case "$1" in
    install)
        # create a dedicated chain so the rule is easy to find and remove
        ${IPT} -N "${TARGET}" 2>/dev/null || true
        ${IPT} -F "${TARGET}" 2>/dev/null || true
        ${IPT} -A "${TARGET}" -j DROP
        ${IPT} -C "${CHAIN}" -d "${SUBNET}" -j "${TARGET}" 2>/dev/null || \
            ${IPT} -I "${CHAIN}" -d "${SUBNET}" -j "${TARGET}"
        echo "isolation installed: host traffic to ${SUBNET} is dropped"
        ;;
    remove)
        ${IPT} -D "${CHAIN}" -d "${SUBNET}" -j "${TARGET}" 2>/dev/null || true
        ${IPT} -F "${TARGET}" 2>/dev/null || true
        ${IPT} -X "${TARGET}" 2>/dev/null || true
        echo "isolation removed: host traffic to ${SUBNET} is allowed again"
        ;;
    status)
        if ${IPT} -C "${CHAIN}" -d "${SUBNET}" -j "${TARGET}" 2>/dev/null; then
            echo "isolation ACTIVE: host traffic to ${SUBNET} is dropped"
        else
            echo "isolation INACTIVE: host traffic to ${SUBNET} is allowed"
        fi
        ;;
    *)
        usage
        ;;
esac
