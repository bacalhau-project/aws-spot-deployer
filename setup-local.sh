#!/bin/bash
"""
Local Setup for SkyPilot Bacalhau Deployment
Copies configuration files to current directory for easy use.
"""

set -e

echo "=== Local SkyPilot Setup ==="
echo

# Check if we're in the right place
if [[ ! -d "skypilot-deployment" ]]; then
    echo "❌ Must run from repository root (directory with skypilot-deployment/)"
    exit 1
fi

# Create directories in current working directory
echo "📁 Creating local configuration..."
mkdir -p credentials config compose scripts

# Copy core files
echo "📄 Copying configuration files..."
cp skypilot-deployment/sky-config.yaml ./
cp skypilot-deployment/bacalhau-cluster.yaml ./
cp skypilot-deployment/.gitignore ./skypilot.gitignore

# Copy directories
cp -r skypilot-deployment/credentials/* credentials/
cp -r skypilot-deployment/config/* config/
cp -r skypilot-deployment/compose/* compose/
cp -r skypilot-deployment/scripts/* scripts/

# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

echo "✅ Files copied to current directory!"
echo
echo "📝 Next steps:"
echo "1. Edit credential files:"
echo "   - credentials/orchestrator_endpoint"
echo "   - credentials/orchestrator_token"
echo "   - credentials/aws-credentials"
echo
echo "2. Deploy from current directory:"
echo "   sky launch -c bacalhau-sensors bacalhau-cluster.yaml"
echo
echo "3. Or use the SkyPilot CLI directly:"
echo "   sky status"
echo "   sky ssh bacalhau-sensors"
echo "   sky down bacalhau-sensors"
echo
echo "💡 All files are now in your current directory"
echo "   You can modify sky-config.yaml and deploy from here"
