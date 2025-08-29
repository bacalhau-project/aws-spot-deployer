#!/bin/bash

# Test actual upload to TestPyPI to debug 400 error
# This helps us understand what's failing without waiting for GitHub Actions

set -euo pipefail

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

echo "🧪 Testing TestPyPI upload with detailed debugging..."
echo "=================================================="

# Check if we have build artifacts
if [ ! -d "dist" ] || [ -z "$(ls -A dist 2>/dev/null)" ]; then
    log_info "No build artifacts found. Building package first..."
    uv build
    log_success "Package built"
fi

# Check what we're uploading
log_info "Package information:"
ls -la dist/
echo ""

# Show package metadata
log_info "Package metadata:"
uv run twine check dist/*

echo ""
log_info "Attempting upload to TestPyPI with verbose output..."
echo "Note: This will fail if you don't have TestPyPI API key configured"
echo "But it will show us the exact error message"
echo ""

# Try to upload with maximum verbosity
# This will likely fail due to auth, but should show us what's wrong
log_warning "This will prompt for TestPyPI credentials or fail with auth error"
echo "Username should be: __token__"
echo "If you have a TestPyPI API key, paste it when prompted"
echo "If you don't have one, just press Ctrl+C to see the error details"
echo ""

set +e  # Don't exit on error so we can capture it
uv run twine upload --repository testpypi dist/* --verbose --non-interactive || {
    echo ""
    log_info "Upload failed as expected (likely auth issue)"
    echo ""
    log_info "Let's check the package details that would be uploaded:"

    # Show detailed package info
    echo ""
    echo "=== PACKAGE DETAILS ==="
    for file in dist/*; do
        echo "File: $(basename "$file")"
        echo "Size: $(stat -f%z "$file") bytes"
        echo "Type: $(file "$file")"
        echo ""
    done

    # Check if the package name might be causing issues
    echo "=== PACKAGE NAME CHECK ==="
    echo "Checking if 'amauo' follows PyPI naming rules..."

    # PyPI naming rules check
    package_name="amauo"
    if [[ "$package_name" =~ ^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$ ]]; then
        log_success "Package name '$package_name' follows PyPI naming rules"
    else
        log_error "Package name '$package_name' violates PyPI naming rules"
    fi

    # Check for potential conflicts or reserved names
    echo ""
    echo "=== TESTPYPI AVAILABILITY CHECK ==="
    log_info "Checking TestPyPI API for package availability..."

    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "https://test.pypi.org/pypi/${package_name}/json")
    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)

    if [ "$http_status" = "404" ]; then
        log_success "Package name is available on TestPyPI (404 response)"
    elif [ "$http_status" = "200" ]; then
        log_warning "Package already exists on TestPyPI"
        echo "Response preview:"
        echo "$response" | head -5
    else
        log_warning "Unexpected HTTP status: $http_status"
    fi

    echo ""
    echo "=== DEBUGGING TIPS ==="
    echo "1. If the error was 'HTTP Error 400', it could be:"
    echo "   - Package already exists"
    echo "   - Invalid package metadata"
    echo "   - OIDC token issues (if using trusted publishing)"
    echo "   - File corruption or invalid format"
    echo ""
    echo "2. To test with API key authentication:"
    echo "   - Create TestPyPI account at https://test.pypi.org/account/register/"
    echo "   - Generate API token at https://test.pypi.org/manage/account/token/"
    echo "   - Run: uv run twine upload --repository testpypi dist/* --verbose"
    echo ""
    echo "3. To test trusted publishing (OIDC):"
    echo "   - Set up trusted publisher at https://test.pypi.org/manage/account/publishing/"
    echo "   - Use GitHub Actions with proper OIDC permissions"
    echo ""
}
set -e

echo ""
log_success "TestPyPI upload test completed!"
echo ""
log_info "Next steps based on the output above:"
echo "1. If upload succeeded: Great! The package is valid"
echo "2. If 400 error: Check package metadata or naming issues"
echo "3. If auth error: Set up TestPyPI API key or trusted publishing"
echo "4. If package exists: Version is auto-generated from git tags"
