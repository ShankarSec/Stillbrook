# =====================================================================
# Stillbrook -- host side helper tools
#
# A tiny image with iptables in it.  It is used by
# scripts/lab_isolation.sh to manage the host firewall rules that keep
# the "internal" docker network unreachable from the host (the helper
# container shares the host network namespace).
# =====================================================================
FROM alpine:3.20

RUN apk add --no-cache iptables ip6tables
