#!/bin/bash
# Create a deployment package with all necessary files

set -e

echo "Creating deployment package..."

# Create temp directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/spot-deployment"

# Create directory structure
mkdir -p "$PACKAGE_DIR/scripts"
mkdir -p "$PACKAGE_DIR/config"
mkdir -p "$PACKAGE_DIR/files"

# Copy scripts
echo "Copying scripts..."
cp instance/scripts/*.py "$PACKAGE_DIR/scripts/" 2>/dev/null || true
cp instance/scripts/*.sh "$PACKAGE_DIR/scripts/" 2>/dev/null || true
cp instance/scripts/*.service "$PACKAGE_DIR/scripts/" 2>/dev/null || true
cp instance/scripts/*.yaml "$PACKAGE_DIR/scripts/" 2>/dev/null || true

# Copy configs
echo "Copying configs..."
cp instance/config/*.yaml "$PACKAGE_DIR/config/" 2>/dev/null || true

# Copy credential files if they exist
echo "Copying credential files..."
cp files/orchestrator_endpoint "$PACKAGE_DIR/files/" 2>/dev/null || true
cp files/orchestrator_token "$PACKAGE_DIR/files/" 2>/dev/null || true

# Create tarball
cd "$TEMP_DIR"
tar -czf spot-deployment.tar.gz spot-deployment/

# Move to current directory
mv spot-deployment.tar.gz ../

# Cleanup
rm -rf "$TEMP_DIR"

echo "Created spot-deployment.tar.gz"
echo "Size: $(ls -lh ../spot-deployment.tar.gz | awk '{print $5}')"
echo ""
echo "Upload this to S3 or a web server and use the URL in your deployment"