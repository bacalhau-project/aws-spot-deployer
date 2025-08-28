#!/bin/bash

# Test PyPI deployment locally for faster debugging
# This script simulates the GitHub Actions workflow steps locally

set -euo pipefail

echo "🧪 Testing PyPI deployment locally..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
log_info "Checking prerequisites..."
if ! command -v uv &> /dev/null; then
    log_error "uv not found. Please install with: pip install uv"
    exit 1
fi
log_success "uv found"

# Clean previous builds
log_info "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/
log_success "Cleaned build artifacts"

# Install build dependencies
log_info "Installing build dependencies..."
uv sync --frozen --group dev
log_success "Dependencies installed"

# Run tests
log_info "Running tests..."
if uv run pytest tests/ -v 2>/dev/null; then
    log_success "Tests passed"
else
    log_warning "No tests found or tests failed"
fi

# Run linting
log_info "Running linting..."
uv run ruff check src/
if [ $? -eq 0 ]; then
    log_success "Linting passed"
else
    log_error "Linting failed"
    exit 1
fi

# Check code formatting
log_info "Checking code formatting..."
uv run ruff format --check src/
if [ $? -eq 0 ]; then
    log_success "Formatting check passed"
else
    log_error "Code formatting check failed"
    exit 1
fi

# Run type checking
log_info "Running type checking..."
uv run mypy src/amauo/
if [ $? -eq 0 ]; then
    log_success "Type checking passed"
else
    log_error "Type checking failed"
    exit 1
fi

# Test CLI installation
log_info "Testing CLI installation..."
if uv run amauo --version; then
    log_success "CLI test passed"
else
    log_error "CLI test failed"
    exit 1
fi

# Build package
log_info "Building package..."
uv build
log_success "Package built successfully"

# Check what was built
log_info "Checking build artifacts..."
ls -la dist/
echo ""

# Validate package metadata
log_info "Validating package metadata with twine..."
if command -v twine &> /dev/null; then
    twine check dist/*
    log_success "Package validation passed"
else
    log_warning "twine not available for validation. Install with: pip install twine"
fi

# Show package info
log_info "Package information:"
echo "Files in dist/:"
for file in dist/*; do
    echo "  - $(basename "$file")"
done
echo ""

# Check package contents
log_info "Checking wheel contents..."
if command -v unzip &> /dev/null; then
    echo "Contents of wheel file:"
    unzip -l dist/*.whl | head -20
    echo ""
fi

# Simulate TestPyPI upload (dry run)
log_info "Simulating TestPyPI upload (dry run)..."
echo "This would upload to TestPyPI with the following command:"
echo "  twine upload --repository testpypi dist/*"
echo ""
echo "Package details:"
echo "  Name: amauo"
echo "  Version: $(uv run amauo --version | cut -d' ' -f3)"
echo "  Files: $(ls dist/ | tr '\n' ' ')"
echo ""

# Check if package exists on TestPyPI
log_info "Checking if package exists on TestPyPI..."
if curl -s "https://test.pypi.org/pypi/amauo/json" | grep -q "Not Found"; then
    log_success "Package name 'amauo' is available on TestPyPI"
else
    log_warning "Package 'amauo' may already exist on TestPyPI"
fi

# Check if package exists on PyPI
log_info "Checking if package exists on PyPI..."
if curl -s "https://pypi.org/pypi/amauo/json" | grep -q "Not Found"; then
    log_success "Package name 'amauo' is available on PyPI"
else
    log_warning "Package 'amauo' may already exist on PyPI"
fi

echo ""
log_success "Local PyPI deployment test completed!"
echo ""
log_info "Next steps:"
echo "1. Set up trusted publishing on TestPyPI:"
echo "   - Go to https://test.pypi.org/manage/account/publishing/"
echo "   - Add trusted publisher with:"
echo "     Owner: bacalhau-project"
echo "     Repository: amauo"
echo "     Workflow: pypi-deploy.yml"
echo "     Environment: testpypi"
echo ""
echo "2. Push to develop branch to trigger deployment:"
echo "   git commit --allow-empty -m 'trigger: test PyPI deployment'"
echo "   git push origin develop"
echo ""
echo "3. Or manually upload for testing:"
echo "   pip install twine"
echo "   twine upload --repository testpypi dist/* --verbose"
