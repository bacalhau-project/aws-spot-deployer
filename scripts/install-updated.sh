#!/bin/bash
# Spot Deployer Installer Script
# This script installs and configures the Spot Deployer tool

set -e

# Configuration
GITHUB_REPO="bacalhau-project/aws-amauo"
INSTALL_DIR="$HOME/.amauo"
BINARY_NAME="amauo"
DOCKER_IMAGE="ghcr.io/${GITHUB_REPO}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
}

# Check if AWS CLI is installed
check_aws() {
    if ! command -v aws &> /dev/null; then
        warning "AWS CLI is not installed. You'll need it to use Spot Deployer."
        echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    fi
}

# Get the latest version or use specified version
get_version() {
    local version="${1:-latest}"

    if [ "$version" = "latest" ]; then
        # Get latest release tag from GitHub
        version=$(curl -s "https://api.github.com/repos/${GITHUB_REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

        if [ -z "$version" ]; then
            warning "Could not fetch latest version, using 'latest' tag"
            version="latest"
        fi
    fi

    echo "$version"
}

# Setup directories
setup_directories() {
    info "Setting up directories..."

    mkdir -p "$INSTALL_DIR"/{config,files,output}

    # Create orchestrator credential placeholders
    if [ ! -f "$INSTALL_DIR/files/orchestrator_endpoint" ]; then
        echo "# Add your orchestrator NATS endpoint here" > "$INSTALL_DIR/files/orchestrator_endpoint"
        echo "# Example: nats://orchestrator.example.com:4222" >> "$INSTALL_DIR/files/orchestrator_endpoint"
    fi

    if [ ! -f "$INSTALL_DIR/files/orchestrator_token" ]; then
        echo "# Add your orchestrator token here" > "$INSTALL_DIR/files/orchestrator_token"
    fi
}

# Pull Docker image
pull_docker_image() {
    local version="$1"
    info "Pulling Docker image..."
    docker pull "${DOCKER_IMAGE}:${version}"
}

# Create wrapper script
create_wrapper() {
    local version="$1"
    local wrapper_path="/usr/local/bin/${BINARY_NAME}"
    local temp_wrapper="/tmp/${BINARY_NAME}-wrapper"

    info "Creating wrapper script..."

    cat > "$temp_wrapper" << 'EOF'
#!/bin/bash
# Spot Deployer wrapper script

INSTALL_DIR="$HOME/.amauo"
DOCKER_IMAGE="ghcr.io/bacalhau-project/aws-amauo"
VERSION="VERSION_PLACEHOLDER"

# Ensure directories exist
mkdir -p "$INSTALL_DIR"/{config,files,output}

# Check if we're in a terminal
if [ -t 0 ]; then
    DOCKER_FLAGS="-it"
else
    DOCKER_FLAGS=""
fi

# Run the Docker container
docker run --rm $DOCKER_FLAGS \
    -v "$INSTALL_DIR/config:/app/config" \
    -v "$INSTALL_DIR/files:/app/files" \
    -v "$INSTALL_DIR/output:/app/output" \
    -v "$HOME/.aws:/root/.aws:ro" \
    -v "$HOME/.ssh:/root/.ssh:ro" \
    -e AWS_PROFILE="${AWS_PROFILE:-}" \
    -e AWS_REGION="${AWS_REGION:-}" \
    -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
    -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
    -e AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN:-}" \
    "${DOCKER_IMAGE}:${VERSION}" "$@"
EOF

    # Replace version placeholder
    sed -i.bak "s/VERSION_PLACEHOLDER/${version}/" "$temp_wrapper" && rm "${temp_wrapper}.bak"

    # Install wrapper script
    if command -v sudo &> /dev/null; then
        sudo mv "$temp_wrapper" "$wrapper_path"
        sudo chmod +x "$wrapper_path"
    else
        warning "sudo not found. Installing to ~/bin instead"
        mkdir -p "$HOME/bin"
        mv "$temp_wrapper" "$HOME/bin/${BINARY_NAME}"
        chmod +x "$HOME/bin/${BINARY_NAME}"
        wrapper_path="$HOME/bin/${BINARY_NAME}"
    fi

    success "Wrapper script installed at: $wrapper_path"
}

# Run setup command
run_setup() {
    info "Running: ${BINARY_NAME} setup"
    "${BINARY_NAME}" setup
}

# Main installation flow
main() {
    echo "🚀 Spot Deployer Installer"
    echo "========================="

    # Parse command line arguments
    local command="${1:-install}"
    local version="${2:-latest}"

    # Check prerequisites
    check_docker
    check_aws

    case "$command" in
        install)
            setup_directories
            version=$(get_version "$version")
            info "Using version: $version"
            pull_docker_image "$version"
            create_wrapper "$version"

            echo ""
            success "Installation complete!"
            echo ""
            echo "Next steps:"
            echo "1. Configure your AWS credentials (if not already done)"
            echo "2. Run: ${BINARY_NAME} setup"
            echo "3. Edit: $INSTALL_DIR/config/config.yaml"
            echo "4. Add orchestrator credentials to: $INSTALL_DIR/files/"
            echo "5. Run: ${BINARY_NAME} create"
            ;;

        setup)
            setup_directories
            version=$(get_version "$version")
            info "Using version: $version"
            pull_docker_image "$version"
            create_wrapper "$version"
            run_setup
            ;;

        update)
            version=$(get_version "$version")
            info "Updating to version: $version"
            pull_docker_image "$version"
            create_wrapper "$version"
            success "Update complete!"
            ;;

        uninstall)
            warning "This will remove Spot Deployer but preserve your config and data"
            read -p "Continue? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                if command -v sudo &> /dev/null; then
                    sudo rm -f "/usr/local/bin/${BINARY_NAME}"
                else
                    rm -f "$HOME/bin/${BINARY_NAME}"
                fi
                success "Spot Deployer uninstalled"
                info "Config and data preserved at: $INSTALL_DIR"
            fi
            ;;

        *)
            error "Unknown command: $command"
            echo "Usage: $0 [install|setup|update|uninstall] [version]"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
