#!/bin/sh
# Start the FastCGI handler and the reverse proxy, then hand off to Flask.
set -e

PHP_VER="$(php -r 'echo PHP_MAJOR_VERSION . "." . PHP_MINOR_VERSION;')"
FPM_BIN="/usr/sbin/php-fpm${PHP_VER}"
if [ ! -x "$FPM_BIN" ]; then
    FPM_BIN="$(command -v php-fpm 2>/dev/null || true)"
fi
if [ -z "$FPM_BIN" ]; then
    echo "web-entrypoint: php-fpm binary not found" >&2
    exit 1
fi

# php-fpm daemonises with -D; nginx daemonises by default.
"$FPM_BIN" -D
nginx

cd /app
# Gunicorn is a production-capable WSGI server. A single worker is used
# deliberately: the lab keeps lockout/WAF/IDOR state in process memory and
# seeding/state semantics are designed around one process.
exec gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 1 \
    --threads 4 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    stillbrook_wsgi:app
