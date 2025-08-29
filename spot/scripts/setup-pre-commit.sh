#!/bin/bash
# Setup pre-commit hooks for the spot deployer project

set -e

echo "Setting up pre-commit hooks..."

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    uv pip install pre-commit
fi

# Check if user has a global hooks path
HOOKS_PATH=$(git config --get core.hooksPath || echo "")

if [ -n "$HOOKS_PATH" ]; then
    echo "⚠️  You have a global git hooks path set: $HOOKS_PATH"
    echo "Pre-commit needs to install hooks in the local .git/hooks directory."
    echo ""
    echo "You have two options:"
    echo "1. Temporarily unset the global hooks path:"
    echo "   git config --unset-all core.hooksPath"
    echo "   uv run pre-commit install"
    echo "   git config --global core.hooksPath $HOOKS_PATH"
    echo ""
    echo "2. Manually run pre-commit before each commit:"
    echo "   uv run pre-commit run --all-files"
    echo ""
    echo "Or add this alias to your shell configuration:"
    echo "   alias spot-check='uv run pre-commit run --all-files'"
else
    # Install pre-commit hooks
    uv run pre-commit install
    echo "✅ Pre-commit hooks installed successfully!"
fi

echo ""
echo "To manually run all checks:"
echo "  uv run pre-commit run --all-files"
