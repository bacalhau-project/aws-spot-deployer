#!/bin/bash
# spot-sso - AWS SSO wrapper for spot-deployer using uvx

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
GITHUB_REPO="${SPOT_GITHUB_REPO:-bacalhau-project/aws-spot-deployer}"

# Check if AWS CLI is available
if ! command -v aws >/dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check if logged in with SSO
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Not logged in to AWS SSO${NC}"
    echo "Please run: aws sso login"
    exit 1
fi

echo -e "${GREEN}✅ AWS SSO session active${NC}"

# Export SSO credentials
echo "Exporting SSO credentials..."
eval $(aws configure export-credentials --format env)

if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo -e "${RED}❌ Failed to export SSO credentials${NC}"
    exit 1
fi

# Default directories
CONFIG_FILE="${SPOT_CONFIG:-./config.yaml}"
FILES_DIR="${SPOT_FILES:-./files}"
OUTPUT_DIR="${SPOT_OUTPUT:-./output}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Set environment variables for spot-deployer
export SPOT_CONFIG_FILE="$CONFIG_FILE"
export SPOT_FILES_DIR="$FILES_DIR"
export SPOT_OUTPUT_DIR="$OUTPUT_DIR"

# Run spot-deployer with SSO credentials using uvx
exec uvx --from git+https://github.com/${GITHUB_REPO} spot-deployer "$@"
