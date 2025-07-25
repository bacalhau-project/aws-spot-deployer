#!/bin/bash
# spot-dev - Auto-rebuild and run for local development with AWS SSO

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Always rebuild the image for development
echo -e "${BLUE}🔨 Rebuilding Docker image...${NC}"
docker build -t spot-test:local . || {
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Docker image rebuilt${NC}"

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

# Build volume mounts
VOLUMES=""

# Mount SSH directory for key access
if [ -d "$HOME/.ssh" ]; then
    VOLUMES="$VOLUMES -v $HOME/.ssh:/root/.ssh:ro"
fi

# Mount config file if it exists (not needed for setup/help)
if [ -f "$CONFIG_FILE" ]; then
    VOLUMES="$VOLUMES -v $(realpath $CONFIG_FILE):/app/config/config.yaml:ro"
fi

# Mount files directory if it exists
if [ -d "$FILES_DIR" ]; then
    VOLUMES="$VOLUMES -v $(realpath $FILES_DIR):/app/files:ro"
fi

# Mount output directory
mkdir -p "$OUTPUT_DIR"
VOLUMES="$VOLUMES -v $(realpath $OUTPUT_DIR):/app/output"

# Mount additional_commands.sh if it exists in current directory
if [ -f "./additional_commands.sh" ]; then
    echo -e "${GREEN}✓ Found additional_commands.sh - will be uploaded to instances${NC}"
    VOLUMES="$VOLUMES -v $(realpath ./additional_commands.sh):/app/output/additional_commands.sh:ro"
else
    echo -e "${YELLOW}ℹ No additional_commands.sh found in current directory${NC}"
    echo -e "${YELLOW}  To run custom commands on instances, create additional_commands.sh${NC}"
fi

# Check if we're in a terminal
if [ -t 0 ] && [ -t 1 ]; then
    TTY_FLAGS="-it"
    TERM_VARS="-e TERM=xterm-256color"
else
    TTY_FLAGS=""
    TERM_VARS="-e TERM=dumb"
fi

# Pass through Bacalhau environment variables if set
BACALHAU_VARS=""
if [ -n "$BACALHAU_API_HOST" ]; then
    BACALHAU_VARS="$BACALHAU_VARS -e BACALHAU_API_HOST=$BACALHAU_API_HOST"
fi
if [ -n "$BACALHAU_API_TOKEN" ]; then
    BACALHAU_VARS="$BACALHAU_VARS -e BACALHAU_API_TOKEN=$BACALHAU_API_TOKEN"
fi
if [ -n "$BACALHAU_API_KEY" ]; then
    BACALHAU_VARS="$BACALHAU_VARS -e BACALHAU_API_KEY=$BACALHAU_API_KEY"
fi

# Run the container with SSO credentials
exec docker run --rm $TTY_FLAGS \
    -e AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY \
    -e AWS_SESSION_TOKEN \
    -e AWS_DEFAULT_REGION \
    -e AWS_REGION \
    $BACALHAU_VARS \
    $TERM_VARS \
    $VOLUMES \
    spot-test:local \
    "$@"
