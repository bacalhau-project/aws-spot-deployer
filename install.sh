#!/bin/bash
set -e

# SkyPilot Spot Deployer - One-command installation script
# Usage: curl -sSL https://tada.wang/install.sh | bash

SCRIPT_NAME="SkyPilot Spot Deployer Installer"
PACKAGE_NAME="amauo"
MIN_PYTHON_VERSION="3.9"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo ""
    echo -e "${BLUE}🌍 $1${NC}"
    echo ""
}

check_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 not found. Please install Python 3.9 or later."
        return 1
    fi

    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

    if [ "$(echo "$python_version" | cut -d. -f1)" -lt 3 ] || \
       [ "$(echo "$python_version" | cut -d. -f2)" -lt 9 ]; then
        log_error "Python $python_version found, but $MIN_PYTHON_VERSION or later is required."
        return 1
    fi

    log_success "Python $python_version found"
    return 0
}

install_uv() {
    if command -v uv >/dev/null 2>&1; then
        log_success "uv is already installed"
        return 0
    fi

    log_info "Installing uv (fast Python package manager)..."

    # Install uv
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        log_error "Neither curl nor wget found. Please install one of them."
        return 1
    fi

    # Source the environment to get uv in PATH
    if [ -f "$HOME/.cargo/env" ]; then
        # shellcheck source=/dev/null
        source "$HOME/.cargo/env"
    fi

    # Add uv to PATH for current session
    if [ -f "$HOME/.local/bin/uv" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi

    if command -v uv >/dev/null 2>&1; then
        local uv_version
        uv_version=$(uv --version 2>/dev/null || echo "unknown")
        log_success "uv installed: $uv_version"
        return 0
    else
        log_error "Failed to install uv. Please check the installation."
        return 1
    fi
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        log_warning "Docker not found. Docker is required for SkyPilot operations."
        log_info "Please install Docker from: https://docs.docker.com/get-docker/"
        return 1
    fi

    if ! docker info >/dev/null 2>&1; then
        log_warning "Docker daemon is not running. Please start Docker."
        return 1
    fi

    log_success "Docker is available and running"
    return 0
}

install_package() {
    log_info "Installing $PACKAGE_NAME using uv..."

    # Install the package using uv with tool support
    if uv tool install "$PACKAGE_NAME"; then
        log_success "$PACKAGE_NAME installed successfully!"
        return 0
    else
        log_error "Failed to install $PACKAGE_NAME using uv tool install"

        # Fallback to uvx for systems where tool install doesn't work
        log_info "Trying alternative installation method..."
        if command -v pip >/dev/null 2>&1; then
            pip install "$PACKAGE_NAME"
            log_success "$PACKAGE_NAME installed via pip"
            return 0
        else
            log_error "Failed to install $PACKAGE_NAME"
            return 1
        fi
    fi
}

show_usage() {
    cat << EOF

🎉 Installation Complete!

USAGE:
  # Deploy a global cluster
  uvx run $PACKAGE_NAME create

  # Check cluster status
  uvx run $PACKAGE_NAME status

  # List all nodes
  uvx run $PACKAGE_NAME list

  # SSH to cluster
  uvx run $PACKAGE_NAME ssh

  # Clean up
  uvx run $PACKAGE_NAME destroy

GETTING STARTED:
  1. Ensure AWS credentials are configured in ~/.aws/
  2. Create a cluster.yaml config file
  3. Run: uvx run $PACKAGE_NAME create
  4. Wait 5-10 minutes for global deployment

For help: uvx run $PACKAGE_NAME --help

EOF
}

main() {
    log_header "$SCRIPT_NAME"

    # Check Python
    if ! check_python; then
        exit 1
    fi

    # Install uv
    if ! install_uv; then
        exit 1
    fi

    # Check Docker (warning only)
    check_docker || log_warning "Docker issues detected - may affect cluster deployment"

    # Install the package
    if ! install_package; then
        exit 1
    fi

    # Show usage instructions
    show_usage

    log_success "Ready to deploy! Run: uvx run $PACKAGE_NAME create"
}

# Check if script is being sourced or executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
