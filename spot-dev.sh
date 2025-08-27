#!/bin/bash
# spot-dev - Development wrapper for running spot-deployer locally with uv

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if this is the random-ip command
QUIET_MODE=false
if [ "$1" = "random-ip" ]; then
    QUIET_MODE=true
fi

# Check if uv is available
if ! command -v uv >/dev/null 2>&1; then
    if [ "$QUIET_MODE" = false ]; then
        echo -e "${RED}❌ uv not found. Please install it first.${NC}"
        echo "Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
    exit 1
fi

# Check if AWS CLI is available
if ! command -v aws >/dev/null 2>&1; then
    if [ "$QUIET_MODE" = false ]; then
        echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    fi
    exit 1
fi

# Check if logged in with SSO
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    if [ "$QUIET_MODE" = false ]; then
        echo -e "${YELLOW}⚠️  Not logged in to AWS SSO${NC}"
        echo "Please run: aws sso login"
    fi
    exit 1
fi

if [ "$QUIET_MODE" = false ]; then
    echo -e "${GREEN}✅ AWS SSO session active${NC}"
    echo "Exporting SSO credentials..."
fi

# Export SSO credentials
eval $(aws configure export-credentials --format env 2>/dev/null)

if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    if [ "$QUIET_MODE" = false ]; then
        echo -e "${RED}❌ Failed to export SSO credentials${NC}"
    fi
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

# Check for additional_commands.sh (only if not in quiet mode)
if [ "$QUIET_MODE" = false ]; then
    if [ -f "./additional_commands.sh" ]; then
        echo -e "${GREEN}✓ Found additional_commands.sh - will be uploaded to instances${NC}"
        mkdir -p "$FILES_DIR/scripts"
        cp ./additional_commands.sh "$FILES_DIR/scripts/additional_commands.sh"
    else
        echo -e "${YELLOW}ℹ No additional_commands.sh found in current directory${NC}"
        echo -e "${YELLOW}  To run custom commands on instances, create additional_commands.sh${NC}"
    fi
else
    # Still copy the file if it exists, just don't print about it
    if [ -f "./additional_commands.sh" ]; then
        mkdir -p "$FILES_DIR/scripts"
        cp ./additional_commands.sh "$FILES_DIR/scripts/additional_commands.sh" 2>/dev/null
    fi
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

if [ "$QUIET_MODE" = false ]; then
    echo -e "${BLUE}→ Running spot-deployer locally with uv...${NC}"
fi

# Run spot-deployer directly from the local code
exec uv run python -m spot_deployer "$@"
