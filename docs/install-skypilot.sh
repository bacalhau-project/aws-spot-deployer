#!/usr/bin/env bash
#
# SkyPilot Bacalhau Deployer Installation Script
# Usage: curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- [COMMAND] [OPTIONS]
#
# Commands:
#   deploy    - Deploy Bacalhau sensor cluster
#   status    - Show cluster status
#   logs      - Show cluster logs and health
#   ssh       - SSH to cluster nodes
#   destroy   - Destroy cluster
#   setup     - Initial setup and credential configuration
#   help      - Show help
#
# Options:
#   --version VERSION - Use specific version (default: latest)
#   --dry-run - Show what would be done without doing it
#   --node N - Target specific node (for logs/ssh commands)
#

set -e

# Configuration
REPO_OWNER="bacalhau-project"
REPO_NAME="aws-spot-deployer"
GITHUB_REPO="https://github.com/${REPO_OWNER}/${REPO_NAME}"
GITHUB_API="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"
RAW_GITHUB="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERSION="main"
DRY_RUN=false
COMMAND=""
NODE_ID=""
WORK_DIR="$HOME/.skypilot-bacalhau"
DEPLOYMENT_DIR="$WORK_DIR/deployment"

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
        --node)
            NODE_ID="$2"
            shift 2
            ;;
        deploy|status|logs|ssh|destroy|setup|help|version)
            COMMAND="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [deploy|status|logs|ssh|destroy|setup|help] [--version VERSION] [--dry-run] [--node N]"
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

# Check if uv is available
check_uv() {
    if command -v uv &> /dev/null; then
        log_success "uv is available"
        return 0
    fi

    log_warn "uv not found, attempting to install..."

    # Try to install uv
    if command -v curl &> /dev/null; then
        log_info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # Source the shell profile to get uv in PATH
        if [[ -f "$HOME/.cargo/env" ]]; then
            source "$HOME/.cargo/env"
        fi

        # Add to current session PATH
        export PATH="$HOME/.cargo/bin:$PATH"

        if command -v uv &> /dev/null; then
            log_success "uv installed successfully"
            return 0
        fi
    fi

    log_error "Failed to install uv. Please install uv manually:"
    log_error "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
}

# Check SkyPilot installation
check_skypilot() {
    log_info "Checking SkyPilot installation..."

    if uv run --script -c "import sky; print('SkyPilot available')" &> /dev/null; then
        log_success "SkyPilot is available"
        return 0
    fi

    log_info "SkyPilot not found, will install on first run"
    return 0
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

# Download deployment files
download_deployment_files() {
    log_info "Downloading SkyPilot deployment files..."

    # Create deployment directory
    mkdir -p "$DEPLOYMENT_DIR"/{credentials,config,compose,scripts}

    # Define files to download
    local files=(
        "skypilot-deployment/sky-config.yaml:sky-config.yaml"
        "skypilot-deployment/bacalhau-cluster.yaml:bacalhau-cluster.yaml"
        "skypilot-deployment/sky-deploy:sky-deploy"
        "skypilot-deployment/install_skypilot.py:install_skypilot.py"
        "skypilot-deployment/setup-example.sh:setup-example.sh"
        "skypilot-deployment/.gitignore:.gitignore"
        "skypilot-deployment/credentials/README.md:credentials/README.md"
        "skypilot-deployment/config/sensor-config.yaml:config/sensor-config.yaml"
        "skypilot-deployment/compose/bacalhau-compose.yml:compose/bacalhau-compose.yml"
        "skypilot-deployment/compose/sensor-compose.yml:compose/sensor-compose.yml"
        "skypilot-deployment/scripts/generate_bacalhau_config.py:scripts/generate_bacalhau_config.py"
        "skypilot-deployment/scripts/generate_node_identity.py:scripts/generate_node_identity.py"
        "skypilot-deployment/scripts/health_check.sh:scripts/health_check.sh"
    )

    for file_mapping in "${files[@]}"; do
        local source_path="${file_mapping%%:*}"
        local dest_path="${file_mapping##*:}"
        local url="${RAW_GITHUB}/${VERSION}/${source_path}"
        local full_dest_path="$DEPLOYMENT_DIR/$dest_path"

        # Create directory if needed
        mkdir -p "$(dirname "$full_dest_path")"

        log_info "Downloading $dest_path..."
        if curl -sSL -f "$url" -o "$full_dest_path"; then
            # Make scripts executable
            if [[ "$dest_path" == *".sh" ]] || [[ "$dest_path" == "sky-deploy" ]] || [[ "$dest_path" == *".py" ]]; then
                chmod +x "$full_dest_path"
            fi
        else
            log_warn "Failed to download $dest_path, skipping..."
        fi
    done

    log_success "Deployment files downloaded to: $DEPLOYMENT_DIR"
}

# Run setup
run_setup() {
    log_info "Running initial setup..."

    cd "$DEPLOYMENT_DIR"

    if [[ -f "setup-example.sh" ]]; then
        ./setup-example.sh
    else
        log_warn "setup-example.sh not found, creating basic credential templates..."

        # Create example credential files
        mkdir -p credentials

        if [[ ! -f "credentials/orchestrator_endpoint" ]]; then
            echo "nats://your-orchestrator.example.com:4222" > credentials/orchestrator_endpoint
            log_info "Created credentials/orchestrator_endpoint (EDIT THIS FILE)"
        fi

        if [[ ! -f "credentials/orchestrator_token" ]]; then
            echo "your-secret-token-here" > credentials/orchestrator_token
            log_info "Created credentials/orchestrator_token (EDIT THIS FILE)"
        fi

        if [[ ! -f "credentials/aws-credentials" ]]; then
            cat > credentials/aws-credentials << 'EOF'
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
region = us-west-2
EOF
            log_info "Created credentials/aws-credentials (EDIT THIS FILE)"
        fi
    fi

    log_success "Setup complete!"
    log_info "Next steps:"
    log_info "1. Edit credential files in: $DEPLOYMENT_DIR/credentials/"
    log_info "2. Deploy cluster: curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- deploy"
}

# Run sky-deploy command
run_sky_deploy() {
    cd "$DEPLOYMENT_DIR"

    local sky_cmd=("./sky-deploy" "$COMMAND")

    # Add node option if specified
    if [[ -n "$NODE_ID" ]] && [[ "$COMMAND" == "logs" || "$COMMAND" == "ssh" ]]; then
        sky_cmd+=("--node" "$NODE_ID")
    fi

    log_info "Running: ${sky_cmd[*]}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would execute the above command"
        return 0
    fi

    # Execute the command
    "${sky_cmd[@]}"
}

# Ensure deployment files exist
ensure_deployment_files() {
    if [[ ! -d "$DEPLOYMENT_DIR" ]] || [[ ! -f "$DEPLOYMENT_DIR/sky-deploy" ]]; then
        log_info "Deployment files not found, downloading..."
        download_deployment_files
    else
        log_success "Using existing deployment files in: $DEPLOYMENT_DIR"
    fi
}

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "🚀 SkyPilot Bacalhau Deployment"
    echo "══════════════════════════════════"
    echo -e "${NC}"
    echo "Repository: $GITHUB_REPO"
    echo "Version: $VERSION"
    echo "Work Directory: $DEPLOYMENT_DIR"
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
        echo "  setup   - Download files and create initial configuration"
        echo "  deploy  - Deploy Bacalhau sensor cluster"
        echo "  status  - Show cluster status"
        echo "  logs    - Show cluster logs and health status"
        echo "  ssh     - SSH to cluster nodes"
        echo "  destroy - Destroy cluster"
        echo "  help    - Show detailed help"
        echo ""
        echo "Usage examples:"
        echo "  curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- setup"
        echo "  curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- deploy"
        echo "  curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- status"
        echo "  curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- logs --node 1"
        echo "  curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- ssh --node 2"
        echo ""
        exit 0
    fi

    # Check prerequisites
    check_uv

    # Handle setup command specially
    if [[ "$COMMAND" == "setup" ]]; then
        download_deployment_files
        run_setup
        return 0
    fi

    # For other commands, ensure deployment files exist
    ensure_deployment_files

    # Check SkyPilot for deployment commands
    if [[ "$COMMAND" == "deploy" ]]; then
        check_skypilot
    fi

    # Check AWS credentials for commands that need them
    if [[ "$COMMAND" != "help" ]] && [[ "$COMMAND" != "version" ]]; then
        if ! check_aws_credentials; then
            log_error "AWS credentials required for this command"
            exit 1
        fi
    fi

    # Run the sky-deploy command
    run_sky_deploy

    log_success "Command completed successfully!"

    if [[ "$COMMAND" == "deploy" ]]; then
        echo ""
        log_info "Next steps:"
        log_info "- Check status: curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- status"
        log_info "- View health: curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- logs"
        log_info "- SSH to nodes: curl -sSL https://tada.wang/install-skypilot.sh | bash -s -- ssh"
    fi
}

# Run main function
main "$@"
