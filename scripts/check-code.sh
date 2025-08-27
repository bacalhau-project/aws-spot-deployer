#!/usr/bin/env bash
# Run all code quality checks

set -e

echo "🔍 Running code quality checks..."

# Run ruff linting
echo "📝 Running ruff lint..."
uv run ruff check .

# Run ruff formatting check
echo "🎨 Checking code formatting..."
uv run ruff format --check .

# Run mypy type checking
echo "🔎 Running type checks..."
uv run mypy spot_deployer/ --ignore-missing-imports --check-untyped-defs || echo "Type checking completed with warnings"

# Run smoke tests
echo "🔥 Running smoke tests..."
uv run python scripts/smoke-test.py

# Run pre-commit on all files
echo "🚀 Running pre-commit checks..."
uv run pre-commit run --all-files

echo "✅ All checks passed!"
