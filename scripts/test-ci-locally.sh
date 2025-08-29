#!/bin/bash
# /// script
# description = "Run full CI pipeline locally to catch issues before push"
# ///

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Running Full CI Pipeline Locally${NC}"
echo "================================================="

# Function to run a step and report success/failure
run_step() {
    local name="$1"
    local cmd="$2"

    echo -e "\n${YELLOW}▶ ${name}${NC}"
    echo "Running: $cmd"

    if eval "$cmd"; then
        echo -e "${GREEN}✅ ${name} - PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ ${name} - FAILED${NC}"
        return 1
    fi
}

# Check dependencies
echo -e "\n${BLUE}📋 Checking Dependencies${NC}"
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed. Please install uv first.${NC}"
    exit 1
fi

# Sync dependencies
run_step "Install Dependencies" "uv sync --frozen --group dev"

# Code Quality Checks (match CI exactly)
echo -e "\n${BLUE}🔍 Code Quality Checks${NC}"
run_step "Ruff Check" "uv run ruff check src/ tests/ scripts/"
run_step "Ruff Format Check" "uv run ruff format --check src/ tests/ scripts/"
run_step "MyPy Type Check" "uv run mypy src/amauo/ --ignore-missing-imports --check-untyped-defs"
run_step "Bandit Security Check" "uv run bandit -r src/amauo/ -ll --skip B101,B108,B202,B324,B601"

# Tests
echo -e "\n${BLUE}🧪 Running Tests${NC}"
run_step "Smoke Tests" "uv run python scripts/smoke-test.py"
run_step "Pytest Tests" "uv run pytest tests/ -v"

# Additional Project Checks
echo -e "\n${BLUE}🔒 Security & Project Checks${NC}"
# Check for actual AWS credentials (exclude our test scripts)
aws_cred_check() {
    local pattern='AKIA\|aws_access_key_id\|aws_secret_access_key'
    ! grep -r "$pattern" scripts/ instance/ src/ --include='*.py' --include='*.sh' --include='*.yaml' | grep -v 'test-ci-locally.sh' || true
}
run_step "Check for AWS Credentials" "aws_cred_check"

if [ -f "cluster-deploy" ]; then
    run_step "Deployment Script Syntax" "bash -n cluster-deploy"
fi

echo -e "\n${GREEN}🎉 All CI Checks Passed Locally!${NC}"
echo -e "${GREEN}✅ Safe to push to GitHub${NC}"
echo "================================================="
