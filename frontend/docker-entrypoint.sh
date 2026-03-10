#!/bin/sh
set -e

# Try to resolve backend hostname — if fails, keep trying
echo "Backend host: $BACKEND_HOST:$BACKEND_PORT"

# Write nginx config with actual backend host
cat > /etc/nginx/conf.d/default.conf << NGINX
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    resolver 127.0.0.11 valid=10s ipv6=off;

    location /api/ {
        set \$backend http://${BACKEND_HOST}:${BACKEND_PORT};
        proxy_pass \$backend/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 120s;
        proxy_read_timeout    120s;
        proxy_send_timeout    120s;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINX

echo "nginx config written, starting..."
exec nginx -g 'daemon off;'
