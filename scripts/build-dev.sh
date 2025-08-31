#!/bin/bash
# Build development version for local testing

set -e

# Get base version from pyproject.toml
BASE_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "//' | sed 's/"//')

# Create development version with timestamp
TIMESTAMP=$(date +%Y%m%d%H%M%S)
DEV_VERSION="${BASE_VERSION}.dev${TIMESTAMP}"

echo "🔧 Building development version: $DEV_VERSION"

# Backup original files
cp pyproject.toml pyproject.toml.bak
cp src/amauo/_version.py src/amauo/_version.py.bak

# Update version temporarily
sed -i.tmp "s/version = \".*\"/version = \"$DEV_VERSION\"/" pyproject.toml
echo "__version__ = \"$DEV_VERSION\"" > src/amauo/_version.py

# Build package
echo "📦 Building package..."
uv build

# Restore original files
mv pyproject.toml.bak pyproject.toml
mv src/amauo/_version.py.bak src/amauo/_version.py
rm -f pyproject.toml.tmp

echo "✅ Development build complete: $DEV_VERSION"
echo "📁 Built packages in dist/"
ls -la dist/
