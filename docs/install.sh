#!/usr/bin/env bash
#
# Spot Deployer Installation Script
# Usage: curl -sSL https://tada.wang/install.sh | bash -s -- [COMMAND] [OPTIONS]
#
# Commands:
#   create    - Create spot instances
#   destroy   - Destroy all spot instances
#   list      - List running instances
#   setup     - Initial setup
#   help      - Show help
#
# Options:
#   --version VERSION - Use specific version (default: latest)
#   --dry-run - Show what would be done without doing it
#

set -e

# Configuration
REPO_OWNER="bacalhau-project"
REPO_NAME="aws-spot-deployer"
GITHUB_REPO="https://github.com/${REPO_OWNER}/${REPO_NAME}"
GITHUB_API="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERSION="latest"
DRY_RUN=false
COMMAND=""
CONFIG_DIR="$HOME/.config/spot-deployer"
FILES_DIR="$PWD/files"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        create|destroy|list|setup|help|version)
            COMMAND="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [create|destroy|list|setup|help] [--version VERSION] [--dry-run]"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if uvx is available
check_uvx() {
    if command -v uvx &> /dev/null; then
        log_success "uvx is available"
        return 0
    fi

    log_warn "uvx not found, checking for uv..."

    if command -v uv &> /dev/null; then
        log_info "Found uv, uvx should be available"
        return 0
    fi

    log_warn "uv/uvx not found, attempting to install..."

    # Try to install uv which includes uvx
    if command -v curl &> /dev/null; then
        log_info "Installing uv (includes uvx)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # Source the shell profile to get uv in PATH
        if [[ -f "$HOME/.cargo/env" ]]; then
            source "$HOME/.cargo/env"
        fi

        # Add to current session PATH
        export PATH="$HOME/.cargo/bin:$PATH"

        if command -v uvx &> /dev/null; then
            log_success "uvx installed successfully"
            return 0
        fi
    fi

    log_error "Failed to install uvx. Please install uv manually:"
    log_error "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
}

# Check AWS credentials
check_aws_credentials() {
    log_info "Checking AWS credentials..."

    # Check environment variables
    if [[ -n "$AWS_ACCESS_KEY_ID" ]] && [[ -n "$AWS_SECRET_ACCESS_KEY" ]]; then
        log_success "Found AWS credentials in environment variables"
        return 0
    fi

    # Check AWS CLI
    if command -v aws &> /dev/null; then
        if aws sts get-caller-identity &> /dev/null; then
            log_success "AWS credentials available via AWS CLI"
            return 0
        fi
    fi

    # Check for AWS config files
    if [[ -f "$HOME/.aws/credentials" ]] || [[ -f "$HOME/.aws/config" ]]; then
        log_success "AWS configuration files found"
        return 0
    fi

    log_warn "No AWS credentials detected"
    log_warn "Please configure AWS credentials before running deployment commands"
    log_warn "Options:"
    log_warn "  1. AWS SSO: aws sso login"
    log_warn "  2. Environment: export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=..."
    log_warn "  3. AWS CLI: aws configure"

    return 1
}

# Resolve version
resolve_version() {
    if [[ "$VERSION" == "latest" ]]; then
        log_info "Resolving latest version..."

        if command -v curl &> /dev/null; then
            LATEST=$(curl -s "$GITHUB_API/releases/latest" | grep -o '"tag_name": *"[^"]*"' | cut -d'"' -f4)
            if [[ -n "$LATEST" ]]; then
                VERSION="$LATEST"
                log_info "Using latest version: $VERSION"
            else
                log_warn "Could not resolve latest version, using main branch"
                VERSION="main"
            fi
        else
            log_warn "curl not available, using main branch"
            VERSION="main"
        fi
    fi
}

# Create config directory
setup_config_dir() {
    if [[ ! -d "$CONFIG_DIR" ]]; then
        log_info "Creating config directory: $CONFIG_DIR"
        mkdir -p "$CONFIG_DIR"
    fi
}

# Run spot-deployer with uvx
run_spot_deployer() {
    local uvx_source

    if [[ "$VERSION" == "main" ]] || [[ "$VERSION" == "latest" ]]; then
        uvx_source="git+${GITHUB_REPO}"
    else
        uvx_source="git+${GITHUB_REPO}@${VERSION}"
    fi

    local uvx_cmd=(
        "uvx"
        "--from" "$uvx_source"
        "spot-deployer"
    )

    # Add the command
    if [[ -n "$COMMAND" ]]; then
        uvx_cmd+=("$COMMAND")
    fi

    # Add dry-run flag if set
    if [[ "$DRY_RUN" == "true" ]]; then
        uvx_cmd+=("--dry-run")
    fi

    log_info "Running: ${uvx_cmd[*]}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would execute the above command"
        return 0
    fi

    # Set environment variables for spot-deployer
    export SPOT_CONFIG_DIR="$CONFIG_DIR"
    export SPOT_FILES_DIR="$FILES_DIR"

    # Run the command
    "${uvx_cmd[@]}"
}

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "🚀 Spot Deployer Installation Script"
    echo "════════════════════════════════════"
    echo -e "${NC}"
    echo "Repository: $GITHUB_REPO"
    echo "Version: $VERSION"
    if [[ -n "$COMMAND" ]]; then
        echo "Command: $COMMAND"
    fi
    echo ""
}

# Main execution
main() {
    print_banner

    # Show help if no command provided
    if [[ -z "$COMMAND" ]]; then
        echo "Available commands:"
        echo "  setup   - Create initial configuration"
        echo "  create  - Create spot instances"
        echo "  list    - List running instances"
        echo "  destroy - Destroy all instances"
        echo "  help    - Show detailed help"
        echo ""
        echo "Usage examples:"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- setup"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- create"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- list"
        echo ""
        exit 0
    fi

    # Check prerequisites
    check_uvx

    # Check AWS credentials for commands that need them
    if [[ "$COMMAND" != "setup" ]] && [[ "$COMMAND" != "help" ]] && [[ "$COMMAND" != "version" ]]; then
        check_aws_credentials
    fi

    # Resolve version
    resolve_version

    # Setup config directory
    setup_config_dir

    # Create files directory if it doesn't exist
    if [[ ! -d "$FILES_DIR" ]]; then
        log_info "Creating files directory: $FILES_DIR"
        mkdir -p "$FILES_DIR"
    fi

    # Run spot-deployer
    run_spot_deployer

    log_success "Command completed successfully!"

    if [[ "$COMMAND" == "setup" ]]; then
        echo ""
        log_info "Next steps:"
        log_info "1. Edit your configuration: $CONFIG_DIR/config.yaml"
        log_info "2. Add any files to upload: $FILES_DIR/"
        log_info "3. Deploy instances: curl -sSL https://tada.wang/install.sh | bash -s -- create"
    fi
}

# Run main function
main "$@"
