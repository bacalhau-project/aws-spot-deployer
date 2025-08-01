#!/usr/bin/env bash
# spot-uvx.sh - Universal wrapper for spot-deployer using uvx
#
# This script runs spot-deployer directly using uvx without Docker
# Usage: uvx https://tada.wang <VERB>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default directories
CONFIG_FILE="${SPOT_CONFIG:-./config.yaml}"
FILES_DIR="${SPOT_FILES:-./files}"
OUTPUT_DIR="${SPOT_OUTPUT:-./output}"

# Function to check if running on EC2
is_ec2_instance() {
    if curl -s -m 1 http://169.254.169.254/latest/meta-data/instance-id >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Detect AWS credentials
detect_aws_credentials() {
    echo -e "${BLUE}🔍 Detecting AWS credentials...${NC}"

    # 1. Check environment variables
    if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
        echo -e "${GREEN}✓ Using AWS credentials from environment variables${NC}"
        return 0
    fi

    # 2. Check if running on EC2 with instance role
    if is_ec2_instance; then
        echo -e "${GREEN}✓ Using EC2 instance role${NC}"
        return 0
    fi

    # 3. Check AWS SSO
    if command -v aws >/dev/null 2>&1; then
        if aws sts get-caller-identity >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Using AWS SSO session${NC}"
            # Export SSO credentials as environment variables
            eval $(aws configure export-credentials --format env 2>/dev/null || true)
            return 0
        fi
    fi

    # 4. Check AWS config/credentials files
    if [ -f "$HOME/.aws/credentials" ] || [ -f "$HOME/.aws/config" ]; then
        echo -e "${GREEN}✓ Using AWS config files${NC}"
        if [ -n "$AWS_PROFILE" ]; then
            echo -e "${BLUE}  Profile: $AWS_PROFILE${NC}"
        fi
        return 0
    fi

    # No credentials found
    echo -e "${RED}❌ No AWS credentials found!${NC}"
    echo ""
    echo "Please configure AWS credentials using one of these methods:"
    echo ""
    echo -e "${YELLOW}1. AWS SSO (Recommended):${NC}"
    echo "   aws sso login"
    echo ""
    echo -e "${YELLOW}2. Environment Variables:${NC}"
    echo "   export AWS_ACCESS_KEY_ID=your-key-id"
    echo "   export AWS_SECRET_ACCESS_KEY=your-secret-key"
    echo ""
    echo -e "${YELLOW}3. AWS Profile:${NC}"
    echo "   aws configure"
    echo "   export AWS_PROFILE=your-profile"
    echo ""
    return 1
}

# Main execution
main() {
    # Show help for certain commands without credential check
    if [[ "$1" == "help" ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ -z "$1" ]]; then
        # Run spot-deployer directly with uvx
        uvx --from git+https://github.com/bacalhau-project/aws-spot-deployer spot-deployer help
        exit 0
    fi

    # Check for version
    if [[ "$1" == "version" ]] || [[ "$1" == "--version" ]] || [[ "$1" == "-v" ]]; then
        uvx --from git+https://github.com/bacalhau-project/aws-spot-deployer spot-deployer --version
        exit 0
    fi

    # Detect credentials for commands that need them
    if [[ "$1" != "setup" ]]; then
        if ! detect_aws_credentials; then
            exit 1
        fi
    fi

    # Create output directory if needed
    mkdir -p "$OUTPUT_DIR"

    # Set environment variables for spot-deployer
    export SPOT_CONFIG_FILE="$CONFIG_FILE"
    export SPOT_FILES_DIR="$FILES_DIR"
    export SPOT_OUTPUT_DIR="$OUTPUT_DIR"

    # If additional_commands.sh exists, copy it to the files directory
    if [ -f "./additional_commands.sh" ]; then
        echo -e "${GREEN}✓ Found additional_commands.sh${NC}"
        cp ./additional_commands.sh "$FILES_DIR/scripts/additional_commands.sh"
    fi

    echo -e "${BLUE}→ Running spot-deployer with uvx...${NC}"
    echo ""

    # Execute spot-deployer directly with uvx
    exec uvx --from git+https://github.com/bacalhau-project/aws-spot-deployer spot-deployer "$@"
}

# Run main function
main "$@"
