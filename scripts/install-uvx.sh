#!/usr/bin/env bash
#
# Spot Deployer Installation Script (uvx version)
# Usage: curl -sSL https://tada.wang | bash -s -- [OPTIONS]
#
# Options:
#   create    - Create spot instances
#   destroy   - Destroy all spot instances
#   list      - List running instances
#   setup     - Initial setup
#   --dry-run - Show what would be done without doing it
#

set -e

# Configuration
REPO_OWNER="bacalhau-project"
REPO_NAME="aws-spot-deployer"
GITHUB_REPO="${REPO_OWNER}/${REPO_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DRY_RUN=false
COMMAND=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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

    # Check uvx
    if ! command -v uvx &> /dev/null; then
        log_warn "uvx not found. Installing..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"

        # Verify installation
        if ! command -v uvx &> /dev/null; then
            log_error "Failed to install uvx"
            exit 1
        fi
    fi

    # Check AWS CLI or environment variables
    if ! command -v aws &> /dev/null; then
        if [[ -z "$AWS_ACCESS_KEY_ID" ]] || [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
            log_warn "AWS CLI not found and AWS credentials not in environment"
            log_warn "You'll need to provide AWS credentials when running"
        fi
    fi
}

setup_directories() {
    # Use current directory for config and files
    WORK_DIR="${SPOT_WORK_DIR:-$(pwd)}"
    CONFIG_FILE="${SPOT_CONFIG_FILE:-$WORK_DIR/config.yaml}"
    FILES_DIR="${SPOT_FILES_DIR:-$WORK_DIR/files}"
    OUTPUT_DIR="${SPOT_OUTPUT_DIR:-$WORK_DIR/output}"

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # For setup command, we don't need config file to exist
    if [[ "$COMMAND" != "setup" ]] && [[ "$COMMAND" != "help" ]]; then
        if [[ ! -f "$CONFIG_FILE" ]]; then
            log_error "Config file not found: $CONFIG_FILE"
            log_info "Run 'setup' command first to create configuration"
            exit 1
        fi
    fi

    # Export for spot-deployer
    export SPOT_CONFIG_FILE="$CONFIG_FILE"
    export SPOT_FILES_DIR="$FILES_DIR"
    export SPOT_OUTPUT_DIR="$OUTPUT_DIR"
}

run_uvx() {
    local uvx_cmd=(
        "uvx" "--from" "git+https://github.com/${GITHUB_REPO}"
        "spot-deployer" "$COMMAND"
    )

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would run: ${uvx_cmd[*]}"
    else
        log_info "Running: spot-deployer $COMMAND"
        "${uvx_cmd[@]}"
    fi
}

show_help() {
    cat << EOF
Spot Deployer - Easy AWS Spot Instance Deployment

Usage:
  curl -sSL https://tada.wang | bash -s -- [COMMAND] [OPTIONS]

Commands:
  create    Create spot instances
  destroy   Destroy all spot instances
  list      List running instances
  setup     Initial configuration setup
  help      Show this help message

Options:
  --dry-run         Show what would be done without doing it

Examples:
  # Initial setup
  curl -sSL https://tada.wang | bash -s -- setup

  # Create instances
  curl -sSL https://tada.wang | bash -s -- create

  # List instances
  curl -sSL https://tada.wang | bash -s -- list

  # Destroy all instances
  curl -sSL https://tada.wang | bash -s -- destroy

Environment Variables:
  SPOT_WORK_DIR      Working directory (default: current directory)
  SPOT_CONFIG_FILE   Config file path (default: ./config.yaml)
  SPOT_FILES_DIR     Files directory (default: ./files)
  SPOT_OUTPUT_DIR    Output directory (default: ./output)
  AWS_ACCESS_KEY_ID  AWS access key
  AWS_SECRET_ACCESS_KEY AWS secret key
  AWS_SESSION_TOKEN  AWS session token (optional)
  AWS_DEFAULT_REGION AWS region (default: us-west-2)

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
    run_uvx
}

# Run main function
main
