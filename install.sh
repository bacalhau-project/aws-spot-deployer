#!/bin/bash

# AWS Spot Instance Deployment Tool - Installation Script
# This script automates the setup process for new users

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install UV if not present
install_uv() {
    if command_exists uv; then
        print_success "UV is already installed"
        uv --version
        return 0
    fi
    
    print_status "Installing UV package manager..."
    if command_exists curl; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
        if command_exists uv; then
            print_success "UV installed successfully"
            uv --version
        else
            print_error "UV installation failed"
            return 1
        fi
    else
        print_error "curl is required but not installed"
        return 1
    fi
}

# Check AWS CLI
check_aws_cli() {
    if command_exists aws; then
        print_success "AWS CLI is installed"
        aws --version
        
        # Check if credentials are configured
        if aws sts get-caller-identity >/dev/null 2>&1; then
            print_success "AWS credentials are configured"
        else
            print_warning "AWS credentials not configured. Run 'aws configure' to set them up"
        fi
    else
        print_warning "AWS CLI not found. Please install from: https://aws.amazon.com/cli/"
    fi
}

# Check SSH keys
check_ssh_keys() {
    print_status "Checking SSH keys..."
    
    SSH_DIR="$HOME/.ssh"
    PRIVATE_KEY="$SSH_DIR/id_ed25519"
    PUBLIC_KEY="$SSH_DIR/id_ed25519.pub"
    
    if [[ -f "$PRIVATE_KEY" && -f "$PUBLIC_KEY" ]]; then
        print_success "SSH keys found at $PRIVATE_KEY and $PUBLIC_KEY"
    else
        print_warning "SSH keys not found. Generating new Ed25519 key pair..."
        
        mkdir -p "$SSH_DIR"
        chmod 700 "$SSH_DIR"
        
        ssh-keygen -t ed25519 -f "$PRIVATE_KEY" -N "" -C "bacalhau-spot-deployment"
        
        if [[ -f "$PRIVATE_KEY" && -f "$PUBLIC_KEY" ]]; then
            print_success "SSH keys generated successfully"
            chmod 600 "$PRIVATE_KEY"
            chmod 644 "$PUBLIC_KEY"
        else
            print_error "Failed to generate SSH keys"
            return 1
        fi
    fi
}

# Download deployment script if not present
download_deployment_script() {
    SCRIPT_NAME="deploy_spot_portable.py"
    
    if [[ -f "$SCRIPT_NAME" ]]; then
        print_success "Deployment script already exists"
        return 0
    fi
    
    print_status "Deployment script not found in current directory"
    
    # If we're in a git repository, assume script is available
    if [[ -d ".git" ]]; then
        if [[ -f "$SCRIPT_NAME" ]]; then
            print_success "Found deployment script in repository"
        else
            print_error "Deployment script not found in repository"
            return 1
        fi
    else
        print_error "Please ensure $SCRIPT_NAME is in the current directory"
        return 1
    fi
}

# Create configuration from template
setup_configuration() {
    print_status "Setting up configuration..."
    
    if [[ -f "config.yaml" ]]; then
        print_warning "config.yaml already exists, skipping configuration setup"
        return 0
    fi
    
    if [[ -f "deploy_spot_portable.py" ]]; then
        print_status "Running environment setup to generate configuration template..."
        ./deploy_spot_portable.py --action setup
        
        if [[ -f "config.yaml_example" ]]; then
            print_success "Configuration template created"
            print_warning "Please copy config.yaml_example to config.yaml and customize it:"
            print_warning "  1. Set your Bacalhau orchestrator URLs"
            print_warning "  2. Set your Bacalhau network token"
            print_warning "  3. Adjust SSH key paths if needed"
            print_warning "  4. Modify instance counts and types as needed"
        else
            print_error "Failed to create configuration template"
            return 1
        fi
    else
        print_error "Deployment script not found"
        return 1
    fi
}

# Validate installation
validate_installation() {
    print_status "Validating installation..."
    
    if [[ -f "deploy_spot_portable.py" && -f "config.yaml" ]]; then
        ./deploy_spot_portable.py --action validate
        return $?
    else
        print_error "Installation incomplete - missing deployment script or configuration"
        return 1
    fi
}

# Main installation process
main() {
    print_status "Starting AWS Spot Instance Deployment Tool installation..."
    echo
    
    # Check system requirements
    print_status "Checking system requirements..."
    
    # Install UV
    if ! install_uv; then
        print_error "Failed to install UV"
        exit 1
    fi
    echo
    
    # Check AWS CLI
    check_aws_cli
    echo
    
    # Check/generate SSH keys
    if ! check_ssh_keys; then
        print_error "Failed to setup SSH keys"
        exit 1
    fi
    echo
    
    # Download/check deployment script
    if ! download_deployment_script; then
        print_error "Failed to setup deployment script"
        exit 1
    fi
    echo
    
    # Setup configuration
    if ! setup_configuration; then
        print_error "Failed to setup configuration"
        exit 1
    fi
    echo
    
    # Final validation
    print_status "Running final validation..."
    if validate_installation; then
        print_success "Installation completed successfully!"
        echo
        print_status "Next steps:"
        echo "  1. Edit config.yaml with your Bacalhau settings"
        echo "  2. Run: ./deploy_spot_portable.py --action verify"
        echo "  3. Run: ./deploy_spot_portable.py --action create"
    else
        print_warning "Installation completed with warnings"
        echo
        print_status "Please resolve any issues before proceeding"
    fi
}

# Run main function
main "$@"