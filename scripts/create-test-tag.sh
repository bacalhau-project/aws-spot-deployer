#!/bin/bash
# Create a test tag for triggering PyPI/Pages deployment

set -e

# Get base version from pyproject.toml
BASE_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "//' | sed 's/"//')

# Create test tag with timestamp
TIMESTAMP=$(date +%m%d%H%M)
TEST_TAG="v${BASE_VERSION}-test${TIMESTAMP}"

echo "🏷️  Creating test tag: $TEST_TAG"

# Create and push tag
git tag "$TEST_TAG"
git push origin "$TEST_TAG"

echo "✅ Test tag created and pushed: $TEST_TAG"
echo "🚀 This will trigger PyPI and Pages deployment workflows"
echo "🗑️  Remember to delete test tag later: git tag -d $TEST_TAG && git push origin :refs/tags/$TEST_TAG"
