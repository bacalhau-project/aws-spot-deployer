#!/bin/bash
set -e

# Simple entrypoint for spot-deployer using uv

# Function to check AWS credentials
check_aws_credentials() {
    if [ -n "$AWS_ACCESS_KEY_ID" ] || [ -f "$HOME/.aws/credentials" ] || curl -s -m 1 http://169.254.169.254/latest/meta-data/iam/security-credentials/ > /dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ ERROR: No AWS credentials found!"
    echo ""
    echo "Please provide AWS credentials using one of:"
    echo "- Environment variables: -e AWS_ACCESS_KEY_ID=xxx -e AWS_SECRET_ACCESS_KEY=yyy"
    echo "- Mount AWS directory: -v ~/.aws:/root/.aws:ro"
    echo "- IAM role (when running on EC2/ECS)"
    return 1
}

# Function to check config file
check_config_file() {
    # Some commands don't need config
    if [[ "$1" == "help" ]] || [[ "$1" == "setup" ]] || [[ "$1" == "--help" ]] || [[ -z "$1" ]]; then
        return 0
    fi
    
    if [ -f "$SPOT_CONFIG_PATH" ] || [ -f "/app/config.yaml" ]; then
        return 0
    fi
    
    echo "❌ ERROR: No config file found!"
    echo ""
    echo "Mount your config: -v /path/to/config.yaml:/app/config/config.yaml"
    echo "Or run setup: docker run -v /path/to/output:/app/output ... setup"
    return 1
}

# Main logic
if [[ "$1" == "setup" ]]; then
    mkdir -p "$SPOT_OUTPUT_DIR"
    # Create config in output directory by setting environment variable
    export SPOT_CONFIG_PATH="$SPOT_OUTPUT_DIR/config.yaml"
    exec uv run spot-deployer setup
fi

# Default to help if no command
if [ $# -eq 0 ]; then
    set -- "help"
fi

# Only check AWS credentials for commands that need them
if [[ "$1" != "help" ]] && [[ "$1" != "setup" ]] && [[ "$1" != "--help" ]]; then
    if ! check_aws_credentials; then
        exit 1
    fi
    
    if ! check_config_file "$1"; then
        exit 1
    fi
fi

# Execute spot deployer using the installed package
exec uv run spot-deployer "$@"