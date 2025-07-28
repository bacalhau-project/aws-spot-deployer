#!/usr/bin/env bash
#
# Spot Deployer Installation Script
# Usage: curl -sSL https://tada.wang/install.sh | bash -s -- [OPTIONS]
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
VERSION="stable"  # Will be resolved to latest release
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

    # Use current directory for config and files
    WORK_DIR="${SPOT_WORK_DIR:-$(pwd)}"
    CONFIG_FILE="${SPOT_CONFIG_FILE:-$WORK_DIR/config.yaml}"
    FILES_DIR="${SPOT_FILES_DIR:-$WORK_DIR/files}"
    OUTPUT_DIR="${SPOT_OUTPUT_DIR:-$WORK_DIR/output}"

    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"

    # Check if config file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        if [[ "$COMMAND" == "setup" ]]; then
            log_info "Creating example config.yaml in current directory..."
            curl -sSL "https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/config.yaml.example" -o config.yaml.example
            cp config.yaml.example config.yaml
            log_info "Created config.yaml - please edit it with your settings"
        else
            log_error "No config.yaml found in current directory"
            log_error "Run 'setup' first to create a configuration file:"
            log_error "  curl -sSL https://tada.wang/install.sh | bash -s -- setup"
            exit 1
        fi
    fi

    # Create files directory if referenced in config
    if [[ -f "$CONFIG_FILE" ]] && grep -q "files_directory:" "$CONFIG_FILE"; then
        mkdir -p "$FILES_DIR"
    fi
}

get_latest_version() {
    if [[ "$VERSION" == "stable" ]]; then
        # Get latest stable release from GitHub API
        local latest_release
        latest_release=$(curl -s "${GITHUB_API}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' || echo "")

        if [[ -n "$latest_release" ]]; then
            VERSION="$latest_release"
            log_info "Using latest stable version: $VERSION"

            # Also show all available versions
            local all_tags
            all_tags=$(curl -s "${GITHUB_API}/tags" | grep '"name":' | sed -E 's/.*"([^"]+)".*/\1/' | head -5 || echo "")
            if [[ -n "$all_tags" ]]; then
                log_info "Recent versions available:"
                echo "$all_tags" | while read -r tag; do
                    echo "  - $tag"
                done
            fi
        else
            log_warn "Could not determine latest stable version, using 'latest' tag"
            VERSION="latest"
        fi
    elif [[ "$VERSION" == "latest" ]]; then
        log_info "Using latest development version from main branch"
    else
        log_info "Using specified version: $VERSION"
    fi
}

run_docker() {
    local docker_image="${DEFAULT_IMAGE}:${VERSION}"

    # Create a temporary directory for AWS SSO cache
    # This prevents the "Read-only file system" error when AWS SDK tries to refresh SSO tokens
    # We copy the AWS config to a temp dir to allow writes while keeping the original files safe
    local temp_aws_dir=$(mktemp -d)
    trap "rm -rf $temp_aws_dir" EXIT

    # Copy AWS config files (including SSO cache)
    if [[ -d "$HOME/.aws" ]]; then
        cp -r "$HOME/.aws/." "$temp_aws_dir/"
    fi

    # Prepare docker run command
    local docker_cmd=(
        "docker" "run" "--rm"
    )

    docker_cmd+=(
        "-v" "$HOME/.ssh:/root/.ssh:ro"
        "-v" "$temp_aws_dir:/root/.aws"
        "-v" "$(realpath "$CONFIG_FILE"):/app/config/config.yaml:ro"
        "-v" "$(realpath "$OUTPUT_DIR"):/app/output"
    )

    # Add files directory if it exists
    if [[ -d "$FILES_DIR" ]]; then
        docker_cmd+=("-v" "$(realpath "$FILES_DIR"):/app/files:ro")
    fi

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
    if [[ -n "$AWS_PROFILE" ]]; then
        docker_cmd+=("-e" "AWS_PROFILE")
    fi
    if [[ -n "$AWS_DEFAULT_REGION" ]]; then
        docker_cmd+=("-e" "AWS_DEFAULT_REGION")
    else
        docker_cmd+=("-e" "AWS_DEFAULT_REGION=us-west-2")
    fi

    # Add terminal settings
    docker_cmd+=("-e" "TERM=${TERM:-xterm-256color}")
    
    # Add Bacalhau environment variables if they exist
    if [[ -n "$BACALHAU_API_HOST" ]]; then
        docker_cmd+=("-e" "BACALHAU_API_HOST")
    fi
    if [[ -n "$BACALHAU_API_KEY" ]]; then
        docker_cmd+=("-e" "BACALHAU_API_KEY")
    fi
    if [[ -n "$BACALHAU_API_TOKEN" ]]; then
        docker_cmd+=("-e" "BACALHAU_API_TOKEN")
    fi

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
  curl -sSL https://tada.wang/install.sh | bash -s -- [COMMAND] [OPTIONS]

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
  curl -sSL https://tada.wang/install.sh | bash -s -- setup

  # Create instances
  curl -sSL https://tada.wang/install.sh | bash -s -- create

  # List instances
  curl -sSL https://tada.wang/install.sh | bash -s -- list

  # Destroy all instances
  curl -sSL https://tada.wang/install.sh | bash -s -- destroy

Environment Variables:
  SPOT_WORK_DIR      Working directory (default: current directory)
  SPOT_CONFIG_FILE   Config file path (default: ./config.yaml)
  SPOT_FILES_DIR     Files directory (default: ./files)
  SPOT_OUTPUT_DIR    Output directory (default: ./output)
  AWS_ACCESS_KEY_ID  AWS access key
  AWS_SECRET_ACCESS_KEY AWS secret key
  AWS_SESSION_TOKEN  AWS session token (optional)
  AWS_PROFILE        AWS profile name (for SSO/named profiles)
  AWS_DEFAULT_REGION AWS region (default: us-west-2)
  BACALHAU_API_HOST  Bacalhau orchestrator endpoint
  BACALHAU_API_KEY   Bacalhau authentication key
  BACALHAU_API_TOKEN Bacalhau authentication token

Files:
  Config: ./config.yaml
  Files:  ./files/
  Output: ./output/

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
