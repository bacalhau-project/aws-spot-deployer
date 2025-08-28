#!/bin/bash

# Complete project rename to Amauo
# This script handles ALL files, directories, and references

set -euo pipefail

# We need to handle the current mixed state
OLD_NAME_1="amauo"
OLD_CLI_NAME_1="amauo"
OLD_PKG_NAME_1="spot_deployer"
OLD_SCRIPT_NAME_1="amauo"

OLD_NAME_2="amauo"
OLD_CLI_NAME_2="amauo"
OLD_PKG_NAME_2="sky_trout"
OLD_SCRIPT_NAME_2="amauo"

NEW_NAME="amauo"
NEW_CLI_NAME="amauo"
NEW_PKG_NAME="amauo"
NEW_SCRIPT_NAME="amauo"

echo "🌟 Renaming project to Amauo 🌟"
echo "================================"

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

# Step 1: Rename the source directory (from whatever it currently is)
log_info "Step 1: Renaming source directory..."
if [ -d "src/${OLD_PKG_NAME_2}" ]; then
    mv "src/${OLD_PKG_NAME_2}" "src/${NEW_PKG_NAME}"
    log_success "Renamed src/${OLD_PKG_NAME_2} → src/${NEW_PKG_NAME}"
elif [ -d "src/${OLD_PKG_NAME_1}" ]; then
    mv "src/${OLD_PKG_NAME_1}" "src/${NEW_PKG_NAME}"
    log_success "Renamed src/${OLD_PKG_NAME_1} → src/${NEW_PKG_NAME}"
else
    log_warning "No source directory found to rename"
fi

# Step 2: Update all Python imports and references
log_info "Step 2: Updating Python imports..."
find . -name "*.py" -type f -exec sed -i '' "s/from ${OLD_PKG_NAME_1}/from ${NEW_PKG_NAME}/g" {} \; 2>/dev/null || true
find . -name "*.py" -type f -exec sed -i '' "s/from ${OLD_PKG_NAME_2}/from ${NEW_PKG_NAME}/g" {} \; 2>/dev/null || true
find . -name "*.py" -type f -exec sed -i '' "s/import ${OLD_PKG_NAME_1}/import ${NEW_PKG_NAME}/g" {} \; 2>/dev/null || true
find . -name "*.py" -type f -exec sed -i '' "s/import ${OLD_PKG_NAME_2}/import ${NEW_PKG_NAME}/g" {} \; 2>/dev/null || true
find . -name "*.py" -type f -exec sed -i '' "s/${OLD_PKG_NAME_1}\./${NEW_PKG_NAME}./g" {} \; 2>/dev/null || true
find . -name "*.py" -type f -exec sed -i '' "s/${OLD_PKG_NAME_2}\./${NEW_PKG_NAME}./g" {} \; 2>/dev/null || true
log_success "Updated Python imports"

# Step 3: Update pyproject.toml
log_info "Step 3: Updating pyproject.toml..."
sed -i '' "s/name = \"${OLD_CLI_NAME_1}\"/name = \"${NEW_CLI_NAME}\"/g" pyproject.toml
sed -i '' "s/name = \"${OLD_CLI_NAME_2}\"/name = \"${NEW_CLI_NAME}\"/g" pyproject.toml
sed -i '' "s/${OLD_SCRIPT_NAME_1} = \"${OLD_PKG_NAME_1}\.cli:cli\"/${NEW_SCRIPT_NAME} = \"${NEW_PKG_NAME}.cli:cli\"/g" pyproject.toml
sed -i '' "s/${OLD_SCRIPT_NAME_2} = \"${OLD_PKG_NAME_2}\.cli:cli\"/${NEW_SCRIPT_NAME} = \"${NEW_PKG_NAME}.cli:cli\"/g" pyproject.toml
sed -i '' "s/version(\"${OLD_CLI_NAME_1}\")/version(\"${NEW_CLI_NAME}\")/g" "src/${NEW_PKG_NAME}/__init__.py" 2>/dev/null || true
sed -i '' "s/version(\"${OLD_CLI_NAME_2}\")/version(\"${NEW_CLI_NAME}\")/g" "src/${NEW_PKG_NAME}/__init__.py" 2>/dev/null || true
sed -i '' "s/version-file = \"src\/${OLD_PKG_NAME_1}/version-file = \"src\/${NEW_PKG_NAME}/g" pyproject.toml
sed -i '' "s/version-file = \"src\/${OLD_PKG_NAME_2}/version-file = \"src\/${NEW_PKG_NAME}/g" pyproject.toml
log_success "Updated pyproject.toml"

# Step 4: Update README.md with Amauo branding
log_info "Step 4: Updating README.md..."
sed -i '' "s/${OLD_CLI_NAME_1}/${NEW_CLI_NAME}/g" README.md
sed -i '' "s/${OLD_CLI_NAME_2}/${NEW_CLI_NAME}/g" README.md
sed -i '' "s/${OLD_NAME_1}/${NEW_NAME}/g" README.md
sed -i '' "s/${OLD_NAME_2}/${NEW_NAME}/g" README.md
sed -i '' "s/${OLD_SCRIPT_NAME_1}/${NEW_SCRIPT_NAME}/g" README.md
sed -i '' "s/${OLD_SCRIPT_NAME_2}/${NEW_SCRIPT_NAME}/g" README.md
sed -i '' "s/Sky Trout/Amauo/g" README.md
sed -i '' "s/Deploy clusters like a trout through clouds/Deploy clusters effortlessly across the cloud/g" README.md
sed -i '' "s/🌍 Sky Trout/🌟 Amauo/g" README.md
sed -i '' "s/🐟☁️ Sky Trout/🌟 Amauo/g" README.md
log_success "Updated README.md"

# Step 5: Update GitHub Actions workflow
log_info "Step 5: Updating GitHub Actions..."
if [ -f ".github/workflows/pypi-deploy.yml" ]; then
    sed -i '' "s/${OLD_CLI_NAME_1}/${NEW_CLI_NAME}/g" .github/workflows/pypi-deploy.yml
    sed -i '' "s/${OLD_CLI_NAME_2}/${NEW_CLI_NAME}/g" .github/workflows/pypi-deploy.yml
    sed -i '' "s/${OLD_PKG_NAME_1}/${NEW_PKG_NAME}/g" .github/workflows/pypi-deploy.yml
    sed -i '' "s/${OLD_PKG_NAME_2}/${NEW_PKG_NAME}/g" .github/workflows/pypi-deploy.yml
    log_success "Updated GitHub Actions workflow"
fi

# Step 6: Update all shell scripts
log_info "Step 6: Updating shell scripts..."
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_CLI_NAME_1}/${NEW_CLI_NAME}/g" {} \;
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_CLI_NAME_2}/${NEW_CLI_NAME}/g" {} \;
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_NAME_1}/${NEW_NAME}/g" {} \;
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_NAME_2}/${NEW_NAME}/g" {} \;
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_SCRIPT_NAME_1}/${NEW_SCRIPT_NAME}/g" {} \;
find . -name "*.sh" -type f -exec sed -i '' "s/${OLD_SCRIPT_NAME_2}/${NEW_SCRIPT_NAME}/g" {} \;
log_success "Updated shell scripts"

# Step 7: Update test files
log_info "Step 7: Updating test files..."
find tests/ -name "*.py" -type f -exec sed -i '' "s/${OLD_PKG_NAME_1}/${NEW_PKG_NAME}/g" {} \; 2>/dev/null || true
find tests/ -name "*.py" -type f -exec sed -i '' "s/${OLD_PKG_NAME_2}/${NEW_PKG_NAME}/g" {} \; 2>/dev/null || true
log_success "Updated test files"

# Step 8: Update documentation files
log_info "Step 8: Updating documentation files..."
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_CLI_NAME_1}/${NEW_CLI_NAME}/g" {} \;
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_CLI_NAME_2}/${NEW_CLI_NAME}/g" {} \;
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_NAME_1}/${NEW_NAME}/g" {} \;
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_NAME_2}/${NEW_NAME}/g" {} \;
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_SCRIPT_NAME_1}/${NEW_SCRIPT_NAME}/g" {} \;
find . -name "*.md" -type f -exec sed -i '' "s/${OLD_SCRIPT_NAME_2}/${NEW_SCRIPT_NAME}/g" {} \;
log_success "Updated documentation files"

# Step 9: Update author and email info
log_info "Step 9: Updating author information..."
sed -i '' 's/Sky Trout Team/Amauo Team/g' "src/${NEW_PKG_NAME}/__init__.py" 2>/dev/null || true
sed -i '' 's/SkyPilot Deployer Team/Amauo Team/g' "src/${NEW_PKG_NAME}/__init__.py" 2>/dev/null || true
sed -i '' 's/hello@skytrout.dev/hello@amauo.dev/g' "src/${NEW_PKG_NAME}/__init__.py" 2>/dev/null || true
sed -i '' 's/deployer@skypilot.co/hello@amauo.dev/g' "src/${NEW_PKG_NAME}/__init__.py" 2>/dev/null || true
sed -i '' 's/Sky Trout Team/Amauo Team/g' pyproject.toml
sed -i '' 's/SkyPilot Deployer Team/Amauo Team/g' pyproject.toml
sed -i '' 's/hello@skytrout.dev/hello@amauo.dev/g' pyproject.toml
sed -i '' 's/deployer@skypilot.co/hello@amauo.dev/g' pyproject.toml
log_success "Updated author information"

# Step 10: Update CLI help text and descriptions
log_info "Step 10: Updating CLI descriptions..."
sed -i '' 's/🐟☁️ Sky Trout/🌟 Amauo/g' "src/${NEW_PKG_NAME}/cli.py" 2>/dev/null || true
sed -i '' 's/🌍 SkyPilot Spot Deployer/🌟 Amauo/g' "src/${NEW_PKG_NAME}/cli.py" 2>/dev/null || true
sed -i '' 's/Deploy clusters like a trout through clouds/Deploy clusters effortlessly across the cloud/g' "src/${NEW_PKG_NAME}/cli.py" 2>/dev/null || true
sed -i '' 's/Deploy global clusters with one command/Deploy clusters effortlessly across the cloud/g' "src/${NEW_PKG_NAME}/cli.py" 2>/dev/null || true
log_success "Updated CLI descriptions"

echo ""
log_success "🌟 Project renamed to Amauo! 🌟"
echo ""
log_info "Summary of changes:"
echo "  • Package name: ${OLD_CLI_NAME_2} → ${NEW_CLI_NAME}"
echo "  • Python module: ${OLD_PKG_NAME_2} → ${NEW_PKG_NAME}"
echo "  • CLI command: ${OLD_SCRIPT_NAME_2} → ${NEW_SCRIPT_NAME}"
echo "  • Author: Sky Trout Team → Amauo Team"
echo "  • Email: hello@skytrout.dev → hello@amauo.dev"
echo ""
log_warning "EXTERNAL CHANGES STILL NEEDED:"
echo "1. GitHub repository name (optional)"
echo "2. TestPyPI trusted publisher settings:"
echo "   - Package name: amauo"
echo "   - Owner: bacalhau-project"
echo "   - Repository: aws-amauo (or new name)"
echo "   - Workflow: pypi-deploy.yml"
echo "   - Environment: testpypi"
echo "3. PyPI trusted publisher settings (same as above)"
echo "4. Update repository URLs in pyproject.toml if repo is renamed"
echo ""
log_info "Test the changes with:"
echo "  uv run python -m ${NEW_PKG_NAME} --version"
echo "  uv build"
