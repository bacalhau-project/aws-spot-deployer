#!/bin/bash

# Complete project rename from amauo to amauo
# This script handles ALL files, directories, and references

set -euo pipefail

OLD_NAME="amauo"
OLD_CLI_NAME="amauo"
OLD_PKG_NAME="spot_deployer"
OLD_SCRIPT_NAME="amauo"

NEW_NAME="amauo"
NEW_CLI_NAME="amauo"
NEW_PKG_NAME="sky_trout"
NEW_SCRIPT_NAME="amauo"

echo "🐟☁️ Renaming project from ${OLD_CLI_NAME} to ${NEW_CLI_NAME} ☁️🐟"
echo "========================================================"

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

# Step 1: Rename the main source directory
log_info "Step 1: Renaming source directory..."
if [ -d "src/${OLD_PKG_NAME}" ]; then
    mv "src/${OLD_PKG_NAME}" "src/${NEW_PKG_NAME}"
    log_success "Renamed src/${OLD_PKG_NAME} → src/${NEW_PKG_NAME}"
else
    log_warning "Directory src/${OLD_PKG_NAME} not found"
fi

# Step 2: Update all Python imports and references
log_info "Step 2: Updating Python imports..."
find . -name "*.py" -type f -exec sed -i '' "s/from ${OLD_PKG_NAME}/from ${NEW_PKG_NAME}/g" {} \;
find . -name "*.py" -type f -exec sed -i '' "s/import ${OLD_PKG_NAME}/import ${NEW_PKG_NAME}/g" {} \;
find . -name "*.py" -type f -exec sed -i '' "s/${OLD_PKG_NAME}\./${NEW_PKG_NAME}./g" {} \;
log_success "Updated Python imports"

# Step 3: Update pyproject.toml
log_info "Step 3: Updating pyproject.toml..."
sed -i '' "s/name = \"${OLD_CLI_NAME}\"/name = \"${NEW_CLI_NAME}\"/g" pyproject.toml
sed -i '' "s/${OLD_SCRIPT_NAME} = \"${OLD_PKG_NAME}\.cli:cli\"/${NEW_SCRIPT_NAME} = \"${NEW_PKG_NAME}.cli:cli\"/g" pyproject.toml
sed -i '' "s/version(\"${OLD_CLI_NAME}\")/version(\"${NEW_CLI_NAME}\")/g" "src/${NEW_PKG_NAME}/__init__.py"
log_success "Updated pyproject.toml"

# Step 4: Update README.md
log_info "Step 4: Updating README.md..."
sed -i '' "s/${OLD_CLI_NAME}/${NEW_CLI_NAME}/g" README.md
sed -i '' "s/${OLD_NAME}/${NEW_NAME}/g" README.md
sed -i '' "s/${OLD_SCRIPT_NAME}/${NEW_SCRIPT_NAME}/g" README.md
sed -i '' "s/SkyPilot Spot Deployer/Sky Trout/g" README.md
sed -i '' "s/Deploy SkyPilot clusters globally/Deploy clusters like a trout through clouds/g" README.md
log_success "Updated README.md"

# Step 5: Update GitHub Actions workflow
log_info "Step 5: Updating GitHub Actions..."
if [ -f ".github/workflows/pypi-deploy.yml" ]; then
    sed -i '' "s/${OLD_CLI_NAME}/${NEW_CLI_NAME}/g" .github/workflows/pypi-deploy.yml
    sed -i '' "s/${OLD_PKG_NAME}/${NEW_PKG_NAME}/g" .github/workflows/pypi-deploy.yml
    log_success "Updated GitHub Actions workflow"
fi

# Step 6: Update all shell scripts
log_info "Step 6: Updating shell scripts..."
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_CLI_NAME}/${NEW_CLI_NAME}/g" {} \;
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_NAME}/${NEW_NAME}/g" {} \;
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_SCRIPT_NAME}/${NEW_SCRIPT_NAME}/g" {} \;
log_success "Updated shell scripts"

# Step 7: Update test files
log_info "Step 7: Updating test files..."
find tests/ -name "*.py" -type f -exec sed -i '' "s/${OLD_PKG_NAME}/${NEW_PKG_NAME}/g" {} \; 2>/dev/null || true
log_success "Updated test files"

# Step 8: Update documentation files
log_info "Step 8: Updating documentation files..."
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_CLI_NAME}/${NEW_CLI_NAME}/g" {} \;
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_NAME}/${NEW_NAME}/g" {} \;
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_SCRIPT_NAME}/${NEW_SCRIPT_NAME}/g" {} \;
log_success "Updated documentation files"

# Step 9: Update author and email info
log_info "Step 9: Updating author information..."
sed -i '' 's/SkyPilot Deployer Team/Sky Trout Team/g' "src/${NEW_PKG_NAME}/__init__.py"
sed -i '' 's/deployer@skypilot.co/hello@skytrout.dev/g' "src/${NEW_PKG_NAME}/__init__.py"
sed -i '' 's/SkyPilot Deployer Team/Sky Trout Team/g' pyproject.toml
sed -i '' 's/deployer@skypilot.co/hello@skytrout.dev/g' pyproject.toml
log_success "Updated author information"

# Step 10: Update CLI help text and descriptions
log_info "Step 10: Updating CLI descriptions..."
sed -i '' 's/🌍 SkyPilot Spot Deployer/🐟☁️ Sky Trout/g' "src/${NEW_PKG_NAME}/cli.py"
sed -i '' 's/Deploy global clusters with one command/Deploy clusters like a trout through clouds/g' "src/${NEW_PKG_NAME}/cli.py"
log_success "Updated CLI descriptions"

echo ""
log_success "🐟☁️ Project rename completed! ☁️🐟"
echo ""
log_info "Summary of changes:"
echo "  • Package name: ${OLD_CLI_NAME} → ${NEW_CLI_NAME}"
echo "  • Python module: ${OLD_PKG_NAME} → ${NEW_PKG_NAME}"
echo "  • CLI command: ${OLD_SCRIPT_NAME} → ${NEW_SCRIPT_NAME}"
echo "  • Author: SkyPilot Deployer Team → Sky Trout Team"
echo "  • Email: deployer@skypilot.co → hello@skytrout.dev"
echo ""
log_warning "EXTERNAL CHANGES STILL NEEDED:"
echo "1. GitHub repository name (if desired)"
echo "2. TestPyPI trusted publisher settings"
echo "3. PyPI trusted publisher settings"
echo "4. Any external documentation or links"
echo ""
log_info "Test the changes with:"
echo "  uv run python -m ${NEW_PKG_NAME} --version"
echo "  uv build"
