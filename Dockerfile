FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-tools \
    postgresql-client \
    git \
    openssh-client \
    sshpass \
    nginx-extras \
    libnginx-mod-http-headers-more-filter \
    php-fpm \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# php-fpm's stock pool uses a unix socket; nginx fastcgi_pass needs TCP.
RUN sed -i 's|^listen = .*|listen = 127.0.0.1:9000|' /etc/php/*/fpm/pool.d/www.conf \
    && mkdir -p /etc/nginx/ssl /var/www/html

# Self-signed certificate for the 443 -> 301 redirect listener.
RUN openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
        -keyout /etc/nginx/ssl/stillbrook.key \
        -out /etc/nginx/ssl/stillbrook.crt \
        -subj "/C=US/ST=NY/L=New York/O=Stillbrook/CN=stillbrook.internal"

COPY docker/web/nginx.conf /etc/nginx/nginx.conf
COPY docker/web/entrypoint.sh /usr/local/bin/web-entrypoint.sh
COPY docker/web/html/ /var/www/html/
RUN chmod +x /usr/local/bin/web-entrypoint.sh

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

COPY . .

# Seed the application's SQLite databases at build time so a fresh clone
# produces a working lab without any host-side manual preparation step.
RUN python3 seed/seed_db.py

EXPOSE 80 443 5000 8080 9090

ENTRYPOINT ["/usr/local/bin/web-entrypoint.sh"]
