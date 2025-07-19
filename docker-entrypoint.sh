#!/bin/bash
set -e

# Docker entrypoint for spot-deployer
# Handles AWS credentials and config file mounting

echo "🚀 Spot Deployer Docker Container"
echo "================================"

# Check for AWS credentials
check_aws_credentials() {
    # Check environment variables
    if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
        echo "✅ Using AWS credentials from environment variables"
        return 0
    fi
    
    # Check mounted credentials file
    if [ -f "$HOME/.aws/credentials" ]; then
        echo "✅ Using AWS credentials from mounted ~/.aws directory"
        return 0
    fi
    
    # Check for IAM role (EC2/ECS)
    if curl -s -m 2 http://169.254.169.254/latest/meta-data/iam/security-credentials/ > /dev/null 2>&1; then
        echo "✅ Using IAM role credentials"
        return 0
    fi
    
    echo "❌ ERROR: No AWS credentials found!"
    echo ""
    echo "Please provide AWS credentials using one of these methods:"
    echo "1. Environment variables:"
    echo "   docker run -e AWS_ACCESS_KEY_ID=xxx -e AWS_SECRET_ACCESS_KEY=yyy ..."
    echo ""
    echo "2. Mount AWS credentials:"
    echo "   docker run -v ~/.aws:/root/.aws:ro ..."
    echo ""
    echo "3. Use IAM role (when running on EC2/ECS)"
    echo ""
    return 1
}

# Check for config file
check_config_file() {
    if [ -f "$SPOT_CONFIG_PATH" ]; then
        echo "✅ Using config file: $SPOT_CONFIG_PATH"
        return 0
    fi
    
    # Check alternative locations
    if [ -f "/app/config.yaml" ]; then
        export SPOT_CONFIG_PATH="/app/config.yaml"
        echo "✅ Using config file: $SPOT_CONFIG_PATH"
        return 0
    fi
    
    # For some commands, config is optional
    if [[ "$1" == "help" ]] || [[ "$1" == "setup" ]] || [[ "$1" == "--help" ]] || [[ -z "$1" ]]; then
        return 0
    fi
    
    echo "❌ ERROR: No config file found!"
    echo ""
    echo "Please mount your config file:"
    echo "   docker run -v /path/to/config.yaml:/app/config/config.yaml ..."
    echo ""
    echo "Or run 'setup' to create one:"
    echo "   docker run -v /path/to/output:/app/output ... setup"
    echo ""
    return 1
}

# Check for credential files (for Bacalhau)
check_credential_files() {
    if [ -f "$SPOT_FILES_DIR/orchestrator_endpoint" ] && [ -f "$SPOT_FILES_DIR/orchestrator_token" ]; then
        echo "✅ Bacalhau credential files found"
    else
        echo "ℹ️  No Bacalhau credentials found (optional)"
        echo "   To use Bacalhau, mount credential files:"
        echo "   docker run -v /path/to/files:/app/files:ro ..."
    fi
}

# Handle setup command specially
if [[ "$1" == "setup" ]]; then
    echo ""
    echo "Running setup command..."
    echo "Config will be created at: $SPOT_OUTPUT_DIR/config.yaml"
    mkdir -p "$SPOT_OUTPUT_DIR"
    cd "$SPOT_OUTPUT_DIR"
    exec uv run /app/spot_deployer/main.py setup
fi

# Validate environment
if ! check_aws_credentials; then
    exit 1
fi

if ! check_config_file "$1"; then
    exit 1
fi

check_credential_files

# Prepare command
if [ $# -eq 0 ] || [[ "$1" == "--help" ]]; then
    # No command specified, show help
    set -- "help"
fi

# Execute spot deployer
echo ""
echo "Executing: spot_deployer $*"
echo "================================"
echo ""

exec uv run /app/spot_deployer/main.py "$@"