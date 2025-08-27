#!/usr/bin/env bash
#
# SkyPilot Bacalhau Deployment - One-Line Install
# Usage: curl -sSL https://tada.wang/install.sh | bash -s -- [COMMAND] [OPTIONS]
#
# Commands:
#   setup     - Download and configure deployment files
#   deploy    - Deploy Bacalhau sensor cluster
#   status    - Show cluster status
#   logs      - Show cluster health and logs
#   ssh       - SSH to cluster nodes
#   destroy   - Destroy cluster
#   help      - Show help
#
# Options:
#   --node N  - Target specific node (for logs/ssh)
#   --dry-run - Show what would be done
#

set -e

# Configuration
REPO_OWNER="bacalhau-project"
REPO_NAME="aws-spot-deployer"
GITHUB_REPO="https://github.com/${REPO_OWNER}/${REPO_NAME}"
RAW_GITHUB="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}"
VERSION="main"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Runtime settings
DRY_RUN=false
COMMAND=""
NODE_ID=""
WORK_DIR="$HOME/.skypilot-bacalhau"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --node)
            NODE_ID="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        setup|deploy|status|logs|ssh|destroy|help)
            COMMAND="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: curl -sSL https://tada.wang/install.sh | bash -s -- [setup|deploy|status|logs|ssh|destroy|help] [--node N] [--dry-run]"
            exit 1
            ;;
    esac
done

# Logging
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check prerequisites
check_prerequisites() {
    # Check uv
    if ! command -v uv &> /dev/null; then
        log_info "Installing uv (required for SkyPilot)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
        if ! command -v uv &> /dev/null; then
            log_error "Failed to install uv"
            exit 1
        fi
    fi
    log_success "uv is available"

<<<<<<< HEAD
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
                VERSION="1.1.1"
                log_info "Using latest version: $VERSION"
            else
                log_warn "Could not resolve latest version, using main branch"
                VERSION="1.1.1"
            fi
        else
            log_warn "curl not available, using main branch"
            VERSION="1.1.1"
=======
    # Check AWS (for deploy commands)
    if [[ "$COMMAND" == "deploy" ]] || [[ "$COMMAND" == "status" ]] || [[ "$COMMAND" == "logs" ]] || [[ "$COMMAND" == "ssh" ]] || [[ "$COMMAND" == "destroy" ]]; then
        if ! aws sts get-caller-identity &> /dev/null 2>&1; then
            log_warn "AWS credentials not configured"
            log_warn "Please run: aws configure (or aws sso login)"
            exit 1
>>>>>>> d4fd114 (feat: add SkyPilot global deployment system)
        fi
        log_success "AWS credentials configured"
    fi
}

# Download deployment files
download_files() {
    log_info "Downloading SkyPilot deployment files..."

    mkdir -p "$WORK_DIR"/{credentials,config,compose,scripts}

    # Core files to download
    local files=(
        "skypilot-deployment/sky-config.yaml"
        "skypilot-deployment/bacalhau-cluster.yaml"
        "skypilot-deployment/sky-deploy"
        "skypilot-deployment/install_skypilot.py"
        "skypilot-deployment/.gitignore"
        "skypilot-deployment/credentials/README.md"
        "skypilot-deployment/config/sensor-config.yaml"
        "skypilot-deployment/compose/bacalhau-compose.yml"
        "skypilot-deployment/compose/sensor-compose.yml"
        "skypilot-deployment/scripts/generate_bacalhau_config.py"
        "skypilot-deployment/scripts/generate_node_identity.py"
        "skypilot-deployment/scripts/health_check.sh"
    )

    for file_path in "${files[@]}"; do
        local filename=$(basename "$file_path")
        local subdir=$(echo "$file_path" | cut -d'/' -f2)
        local dest_path="$WORK_DIR"

        # Place files in correct subdirectories
        if [[ "$subdir" != "sky-config.yaml" ]] && [[ "$subdir" != "bacalhau-cluster.yaml" ]] && [[ "$subdir" != "sky-deploy" ]] && [[ "$subdir" != "install_skypilot.py" ]] && [[ "$subdir" != ".gitignore" ]]; then
            dest_path="$WORK_DIR/$subdir"
            mkdir -p "$dest_path"
        fi

        local url="${RAW_GITHUB}/${VERSION}/${file_path}"
        local output_file="$dest_path/$filename"

        if curl -sSL -f "$url" -o "$output_file" 2>/dev/null; then
            # Make scripts executable
            if [[ "$filename" == *".sh" ]] || [[ "$filename" == "sky-deploy" ]] || [[ "$filename" == *".py" ]]; then
                chmod +x "$output_file"
            fi
        else
            log_warn "Could not download $filename (continuing...)"
        fi
    done

    log_success "Files downloaded to: $WORK_DIR"
}

# Setup credentials
setup_credentials() {
    log_info "Setting up credential templates..."

    # Create credential templates
    if [[ ! -f "$WORK_DIR/credentials/orchestrator_endpoint" ]]; then
        echo "nats://your-orchestrator.example.com:4222" > "$WORK_DIR/credentials/orchestrator_endpoint"
        log_info "Created: credentials/orchestrator_endpoint"
    fi

    if [[ ! -f "$WORK_DIR/credentials/orchestrator_token" ]]; then
        echo "your-secret-token-here" > "$WORK_DIR/credentials/orchestrator_token"
        log_info "Created: credentials/orchestrator_token"
    fi

    if [[ ! -f "$WORK_DIR/credentials/aws-credentials" ]]; then
        cat > "$WORK_DIR/credentials/aws-credentials" << 'EOF'
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
region = us-west-2
EOF
        log_info "Created: credentials/aws-credentials"
    fi

    log_success "Credential templates ready!"
    echo
    log_warn "IMPORTANT: Edit these credential files before deploying:"
    echo "  - $WORK_DIR/credentials/orchestrator_endpoint"
    echo "  - $WORK_DIR/credentials/orchestrator_token"
    echo "  - $WORK_DIR/credentials/aws-credentials"
}

# Run sky-deploy command
run_command() {
    if [[ ! -f "$WORK_DIR/sky-deploy" ]]; then
        log_info "Deployment files not found, downloading..."
        download_files
    fi

    cd "$WORK_DIR"

    local cmd_args=("./sky-deploy" "$COMMAND")

    # Add node option for logs/ssh
    if [[ -n "$NODE_ID" ]] && [[ "$COMMAND" == "logs" || "$COMMAND" == "ssh" ]]; then
        cmd_args+=("--node" "$NODE_ID")
    fi

    log_info "Running: ${cmd_args[*]}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would execute the above command"
        return 0
    fi

    "${cmd_args[@]}"
}

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "🚀 SkyPilot Bacalhau Deployment"
    echo "══════════════════════════════════"
    echo -e "${NC}"
    echo "Modern multi-cloud spot deployment"
    echo "Work Directory: $WORK_DIR"
    if [[ -n "$COMMAND" ]]; then
        echo "Command: $COMMAND"
    fi
    echo
}

# Main execution
main() {
    print_banner

    # Show help if no command
    if [[ -z "$COMMAND" ]]; then
        echo "Available commands:"
        echo "  setup     - Download files and setup credentials"
        echo "  deploy    - Deploy 6-node Bacalhau sensor cluster"
        echo "  status    - Show cluster status"
        echo "  logs      - Show cluster health and logs"
        echo "  ssh       - SSH to cluster nodes"
        echo "  destroy   - Destroy cluster"
        echo "  help      - Show this help"
        echo
        echo "Usage examples:"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- setup"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- deploy"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- status"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- logs --node 1"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- ssh --node 2"
        echo "  curl -sSL https://tada.wang/install.sh | bash -s -- destroy"
        echo
        exit 0
    fi

    # Check prerequisites
    check_prerequisites

    # Handle setup specially
    if [[ "$COMMAND" == "setup" ]]; then
        download_files
        setup_credentials
        log_success "Setup complete!"
        echo
        log_info "Next steps:"
        log_info "1. Edit credential files (see paths above)"
        log_info "2. Deploy: curl -sSL https://tada.wang/install.sh | bash -s -- deploy"
        return 0
    fi

    # Run other commands
    run_command

    log_success "Command completed!"

    # Show next steps after deploy
    if [[ "$COMMAND" == "deploy" ]]; then
        echo
        log_info "Next steps:"
        echo "  Status: curl -sSL https://tada.wang/install.sh | bash -s -- status"
        echo "  Health: curl -sSL https://tada.wang/install.sh | bash -s -- logs"
        echo "  SSH:    curl -sSL https://tada.wang/install.sh | bash -s -- ssh"
    fi
}

# Run it
main "$@"
