#!/bin/bash
# Configure Nginx for Node.js app

set -e

echo "Configuring Nginx..."

# Enable site
ln -sf /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test configuration
nginx -t

# Reload Nginx
systemctl reload nginx

echo "Nginx configured successfully"
