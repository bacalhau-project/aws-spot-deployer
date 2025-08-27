#!/bin/bash
"""
Setup script for SkyPilot Bacalhau deployment.
Creates example credential files and validates the environment.
"""

set -e

echo "=== SkyPilot Bacalhau Deployment Setup ==="
echo

# Check if we're in the right directory
if [ ! -f "sky-config.yaml" ]; then
    echo "❌ Must run from skypilot-deployment directory"
    exit 1
fi

# Create example credential files if they don't exist
echo "📁 Setting up credential files..."

if [ ! -f "credentials/orchestrator_endpoint" ]; then
    cat > credentials/orchestrator_endpoint << EOF
nats://your-orchestrator.example.com:4222
EOF
    echo "✓ Created credentials/orchestrator_endpoint (EDIT THIS FILE)"
else
    echo "✓ credentials/orchestrator_endpoint exists"
fi

if [ ! -f "credentials/orchestrator_token" ]; then
    cat > credentials/orchestrator_token << EOF
your-secret-token-here
EOF
    echo "✓ Created credentials/orchestrator_token (EDIT THIS FILE)"
else
    echo "✓ credentials/orchestrator_token exists"
fi

if [ ! -f "credentials/aws-credentials" ]; then
    cat > credentials/aws-credentials << EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
region = us-west-2
EOF
    echo "✓ Created credentials/aws-credentials (EDIT THIS FILE)"
else
    echo "✓ credentials/aws-credentials exists"
fi

echo
echo "🔧 Checking environment..."

# Check if SkyPilot is available
if ./install_skypilot.py > /dev/null 2>&1; then
    echo "✓ SkyPilot is installed and configured"
else
    echo "❌ SkyPilot is not properly configured"
    echo "   Run: ./install_skypilot.py"
    exit 1
fi

# Check AWS credentials
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✓ AWS credentials are configured"
    echo "  Account: $(aws sts get-caller-identity --query Account --output text)"
    echo "  User: $(aws sts get-caller-identity --query Arn --output text)"
else
    echo "❌ AWS credentials not configured"
    echo "   Run: aws configure"
    exit 1
fi

# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

echo
echo "🚀 Setup complete!"
echo
echo "Next steps:"
echo "1. Edit credential files in credentials/ directory:"
echo "   - credentials/orchestrator_endpoint"
echo "   - credentials/orchestrator_token"
echo "   - credentials/aws-credentials"
echo
echo "2. Optionally modify sky-config.yaml for your deployment"
echo
echo "3. Deploy the cluster:"
echo "   ./sky-deploy deploy"
echo
echo "4. Check status:"
echo "   ./sky-deploy status"
echo
echo "5. View health:"
echo "   ./sky-deploy logs"
