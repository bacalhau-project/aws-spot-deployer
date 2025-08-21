#!/bin/bash
# Install Node.js application

set -e

echo "Installing Node.js application..."

# Create app directory
mkdir -p /opt/app
cd /opt/app

# Clone or download your application
# git clone https://github.com/youruser/yourapp.git .
# OR
# wget https://example.com/app.tar.gz
# tar -xzf app.tar.gz

# Install dependencies
npm install --production

# Build if necessary
# npm run build

echo "Node.js application installed successfully"
