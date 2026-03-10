#!/bin/sh
set -e

BACKEND_HOST="${BACKEND_HOST:-backend}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "=== Hotel Hotspot Frontend ==="
echo "Backend: ${BACKEND_HOST}:${BACKEND_PORT}"

# Remove default nginx configs to avoid conflicts
rm -f /etc/nginx/conf.d/default.conf

# Write clean nginx config — upstream block (no resolver needed)
cat > /etc/nginx/conf.d/app.conf << EOF
upstream api_backend {
    server ${BACKEND_HOST}:${BACKEND_PORT};
}

server {
    listen 80 default_server;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 50M;

    # API proxy to FastAPI backend
    location /api/ {
        proxy_pass         http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 120s;
        proxy_read_timeout    120s;
        proxy_send_timeout    120s;
    }

    # React SPA — all other routes
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Health check for Coolify
    location /nginx-health {
        access_log off;
        return 200 'ok';
        add_header Content-Type text/plain;
    }
}
EOF

echo "--- Generated nginx config ---"
cat /etc/nginx/conf.d/app.conf
echo "--- Testing nginx config ---"
nginx -t
echo "--- Starting nginx ---"
exec nginx -g 'daemon off;'
