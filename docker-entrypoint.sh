#!/bin/bash
set -e

# Simple entrypoint for spot-deployer

# Function to check AWS credentials
check_aws_credentials() {
    # Check various credential sources
    if [ -n "$AWS_ACCESS_KEY_ID" ]; then
        echo "ℹ️  Using AWS credentials from environment variables"
        return 0
    elif [ -n "$AWS_PROFILE" ]; then
        echo "ℹ️  Using AWS profile: $AWS_PROFILE"
        if [ -f "$HOME/.aws/credentials" ] || [ -f "$HOME/.aws/config" ]; then
            return 0
        else
            echo "⚠️  AWS profile specified but no credentials file found"
        fi
    elif [ -f "$HOME/.aws/credentials" ]; then
        echo "ℹ️  Using AWS credentials from ~/.aws/credentials"
        return 0
    elif [ -d "$HOME/.aws/sso/cache" ] && [ "$(ls -A $HOME/.aws/sso/cache 2>/dev/null)" ]; then
        echo "ℹ️  Using AWS SSO credentials"
        # Check if SSO session is still valid
        if aws sts get-caller-identity > /dev/null 2>&1; then
            echo "✅ AWS SSO session is active"
            return 0
        else
            echo "⚠️  AWS SSO session expired. Run: aws sso login"
            return 1
        fi
    elif curl -s -m 1 http://169.254.169.254/latest/meta-data/iam/security-credentials/ > /dev/null 2>&1; then
        echo "ℹ️  Using IAM instance role"
        return 0
    elif [ -n "$AWS_CONTAINER_CREDENTIALS_RELATIVE_URI" ]; then
        echo "ℹ️  Using ECS task role"
        return 0
    fi

    echo "❌ ERROR: No AWS credentials found!"
    echo ""
    echo "Please provide AWS credentials using one of the following methods:"
    echo ""
    echo "Option 1 - Environment variables:"
    echo "  docker run -e AWS_ACCESS_KEY_ID=xxx -e AWS_SECRET_ACCESS_KEY=yyy ..."
    echo ""
    echo "Option 2 - AWS SSO (recommended):"
    echo "  aws sso login  # Run this first on your host"
    echo "  docker run -v ~/.aws:/root/.aws:ro ..."
    echo ""
    echo "Option 3 - AWS Profile:"
    echo "  docker run -v ~/.aws:/root/.aws:ro -e AWS_PROFILE=myprofile ..."
    echo ""
    echo "Option 4 - IAM role (when running on EC2/ECS)"
    echo ""
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
    exec spot-deployer setup
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

# Check if the first argument looks like a command or script
if [[ "$1" == "bash" ]] || [[ "$1" == "sh" ]] || [[ "$1" == "python" ]] || [[ -x "$1" ]]; then
    # Execute the command directly
    exec "$@"
else
    # Execute spot deployer (it's already installed)
    exec spot-deployer "$@"
fi
