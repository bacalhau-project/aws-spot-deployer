#!/usr/bin/env bash
# Helper script to show current version and suggest next version

set -e

# Fetch all tags
echo "Fetching latest tags..."
git fetch --all --tags --force >/dev/null 2>&1

# Get latest tag
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "Current latest tag: $LATEST_TAG"

# Show recent tags
echo -e "\nRecent tags:"
git tag -l | sort -V | tail -5

# Calculate next version
if [[ $LATEST_TAG =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    MAJOR=${BASH_REMATCH[1]}
    MINOR=${BASH_REMATCH[2]}
    PATCH=${BASH_REMATCH[3]}
    
    NEXT_PATCH=$((PATCH + 1))
    NEXT_MINOR=$((MINOR + 1))
    NEXT_MAJOR=$((MAJOR + 1))
    
    echo -e "\nSuggested next versions:"
    echo "  Patch release: v${MAJOR}.${MINOR}.${NEXT_PATCH}"
    echo "  Minor release: v${MAJOR}.${NEXT_MINOR}.0"
    echo "  Major release: v${NEXT_MAJOR}.0.0"
    
    echo -e "\nTo create a new release:"
    echo "  git tag v${MAJOR}.${MINOR}.${NEXT_PATCH}"
    echo "  git push origin v${MAJOR}.${MINOR}.${NEXT_PATCH}"
else
    echo "Warning: Latest tag doesn't follow semantic versioning pattern"
fi