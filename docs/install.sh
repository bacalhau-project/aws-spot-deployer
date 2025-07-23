#!/usr/bin/env bash
#
# Spot Deployer Installation Script
# Usage: curl -sSL https://yourdomain.com/install.sh | bash -s -- [OPTIONS]
#
# Options:
#   create    - Create spot instances
#   destroy   - Destroy all spot instances
#   list      - List running instances
#   setup     - Initial setup
#   --version VERSION - Use specific version (default: latest)
#   --dry-run - Show what would be done without doing it
#

set -e

# Configuration
REPO_OWNER="bacalhau-project"
REPO_NAME="aws-spot-deployer"
DEFAULT_IMAGE="ghcr.io/${REPO_OWNER}/${REPO_NAME}"
GITHUB_API="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
VERSION="latest"
DRY_RUN=false
COMMAND=""

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
        create|destroy|list|setup|help)
            COMMAND="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Default to help if no command specified
COMMAND=${COMMAND:-help}

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    local missing=()

    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi

    # Check AWS CLI or environment variables
    if ! command -v aws &> /dev/null; then
        if [[ -z "$AWS_ACCESS_KEY_ID" ]] || [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
            log_warn "AWS CLI not found and AWS credentials not in environment"
            log_warn "You'll need to provide AWS credentials when running"
        fi
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing prerequisites: ${missing[*]}"
        log_error "Please install missing tools and try again"
        exit 1
    fi
}

setup_directories() {
    log_info "Setting up directories..."

    # Create working directory
    WORK_DIR="${SPOT_WORK_DIR:-$HOME/.spot-deployer}"
    mkdir -p "$WORK_DIR"/{config,files,output}

    # Create default config if it doesn't exist
    if [[ ! -f "$WORK_DIR/config/config.yaml" ]]; then
        cat > "$WORK_DIR/config/config.yaml" << 'EOF'
aws:
  total_instances: 3
  username: ubuntu
  tags:
    Project: "SpotDeployment"
    App: "SpotDeployer"
regions:
  - us-west-2:
      machine_type: t3.medium
      image: auto
EOF
        log_info "Created default config at $WORK_DIR/config/config.yaml"
        log_warn "Please edit this file with your settings before running 'create'"
    fi
}

get_latest_version() {
    if [[ "$VERSION" == "latest" ]]; then
        # Try to get latest release from GitHub API
        local latest_release
        latest_release=$(curl -s "${GITHUB_API}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v?([^"]+)".*/\1/' || echo "")

        if [[ -n "$latest_release" ]]; then
            VERSION="$latest_release"
        else
            VERSION="latest"
        fi
    fi

    log_info "Using version: $VERSION"
}

run_docker() {
    local docker_image="${DEFAULT_IMAGE}:${VERSION}"

    # Prepare docker run command
    local docker_cmd=(
        "docker" "run" "--rm"
    )
    
    # Only add -it if running interactively (not piped)
    if [ -t 0 ] && [ -t 1 ]; then
        docker_cmd+=("-it")
    fi
    
    docker_cmd+=(
        "-v" "$HOME/.ssh:/root/.ssh:ro"
        "-v" "$WORK_DIR/config/config.yaml:/app/config/config.yaml:ro"
        "-v" "$WORK_DIR/files:/app/files:ro"
        "-v" "$WORK_DIR/output:/app/output"
    )

    # Add AWS credentials if available
    if [[ -n "$AWS_ACCESS_KEY_ID" ]]; then
        docker_cmd+=("-e" "AWS_ACCESS_KEY_ID")
    fi
    if [[ -n "$AWS_SECRET_ACCESS_KEY" ]]; then
        docker_cmd+=("-e" "AWS_SECRET_ACCESS_KEY")
    fi
    if [[ -n "$AWS_SESSION_TOKEN" ]]; then
        docker_cmd+=("-e" "AWS_SESSION_TOKEN")
    fi
    if [[ -n "$AWS_DEFAULT_REGION" ]]; then
        docker_cmd+=("-e" "AWS_DEFAULT_REGION")
    else
        docker_cmd+=("-e" "AWS_DEFAULT_REGION=us-west-2")
    fi

    # Add terminal settings
    docker_cmd+=("-e" "TERM=${TERM:-xterm-256color}")

    # Add image and command
    docker_cmd+=("$docker_image" "$COMMAND")

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would run: ${docker_cmd[*]}"
    else
        log_info "Pulling Docker image..."
        docker pull "$docker_image"

        log_info "Running: spot-deployer $COMMAND"
        "${docker_cmd[@]}"
    fi
}

show_help() {
    cat << EOF
Spot Deployer - Easy AWS Spot Instance Deployment

Usage:
  curl -sSL https://yourdomain.com/install.sh | bash -s -- [COMMAND] [OPTIONS]

Commands:
  create    Create spot instances
  destroy   Destroy all spot instances
  list      List running instances
  setup     Initial configuration setup
  help      Show this help message

Options:
  --version VERSION  Use specific version (default: latest)
  --dry-run         Show what would be done without doing it

Examples:
  # Initial setup
  curl -sSL https://yourdomain.com/install.sh | bash -s -- setup

  # Create instances
  curl -sSL https://yourdomain.com/install.sh | bash -s -- create

  # List instances
  curl -sSL https://yourdomain.com/install.sh | bash -s -- list

  # Destroy all instances
  curl -sSL https://yourdomain.com/install.sh | bash -s -- destroy

Environment Variables:
  SPOT_WORK_DIR     Working directory (default: ~/.spot-deployer)
  AWS_ACCESS_KEY_ID AWS access key
  AWS_SECRET_ACCESS_KEY AWS secret key
  AWS_SESSION_TOKEN AWS session token (optional)
  AWS_DEFAULT_REGION AWS region (default: us-west-2)

Files:
  Config: $HOME/.spot-deployer/config/config.yaml
  Files:  $HOME/.spot-deployer/files/
  Output: $HOME/.spot-deployer/output/

EOF
}

# Main execution
main() {
    echo "🚀 Spot Deployer Installer"
    echo "========================="

    if [[ "$COMMAND" == "help" ]]; then
        show_help
        exit 0
    fi

    check_prerequisites
    setup_directories
    get_latest_version
    run_docker
}

# Run main function
main
