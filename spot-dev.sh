#!/bin/bash
# spot-dev - Development wrapper for running spot-deployer locally with uv

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if uv is available
if ! command -v uv >/dev/null 2>&1; then
    echo -e "${RED}❌ uv not found. Please install it first.${NC}"
    echo "Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

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

# Check for additional_commands.sh
if [ -f "./additional_commands.sh" ]; then
    echo -e "${GREEN}✓ Found additional_commands.sh - will be uploaded to instances${NC}"
    mkdir -p "$FILES_DIR/scripts"
    cp ./additional_commands.sh "$FILES_DIR/scripts/additional_commands.sh"
else
    echo -e "${YELLOW}ℹ No additional_commands.sh found in current directory${NC}"
    echo -e "${YELLOW}  To run custom commands on instances, create additional_commands.sh${NC}"
fi

# Pass through Bacalhau environment variables if set
if [ -n "$BACALHAU_API_HOST" ]; then
    export BACALHAU_API_HOST
fi
if [ -n "$BACALHAU_API_TOKEN" ]; then
    export BACALHAU_API_TOKEN
fi
if [ -n "$BACALHAU_API_KEY" ]; then
    export BACALHAU_API_KEY
fi

echo -e "${BLUE}→ Running spot-deployer locally with uv...${NC}"

# Run spot-deployer directly from the local code
exec uv run python -m spot_deployer "$@"
