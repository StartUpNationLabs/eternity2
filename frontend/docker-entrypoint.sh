#!/bin/bash

# Write environment variables to /usr/share/nginx/html/env
# for runtime configuration in the browser
{
  env | grep 'SERVER_BASE_URL'
  env | grep 'BASE_PATH'
} > /usr/share/nginx/html/env

# If BASE_PATH is set, update nginx configuration to serve from that path
if [ -n "$BASE_PATH" ]; then
  # Remove leading/trailing slashes for consistency
  CLEAN_BASE_PATH=$(echo "$BASE_PATH" | sed 's:/*$::' | sed 's:^/*::')

  if [ -n "$CLEAN_BASE_PATH" ]; then
    echo "Configuring nginx for base path: /$CLEAN_BASE_PATH"

    # Update nginx configuration with the base path
    cat > /etc/nginx/conf.d/default.conf <<EOF
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Serve the application under the base path
    location /$CLEAN_BASE_PATH {
        alias /usr/share/nginx/html;
        try_files \$uri \$uri/ /$CLEAN_BASE_PATH/index.html;
    }

    # Also serve at root for backward compatibility
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
EOF
  fi
fi

nginx -g "daemon off;"
