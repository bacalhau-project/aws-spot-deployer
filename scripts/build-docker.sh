#!/bin/bash
# Local Docker build script for testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configuration
REGISTRY="ghcr.io"
IMAGE_NAME="bacalhau-project/spot-deployer"
VERSION="${1:-dev}"

echo "🔨 Building Spot Deployer Docker Image"
echo "====================================="
echo "Registry: ${REGISTRY}"
echo "Image: ${IMAGE_NAME}"
echo "Version: ${VERSION}"
echo ""

# Change to project root
cd "${PROJECT_ROOT}"

# Build the image
echo "Building image..."
docker build \
    -t "${IMAGE_NAME}:${VERSION}" \
    -t "${IMAGE_NAME}:latest" \
    .

echo ""
echo "✅ Build complete!"
echo ""
echo "To test the image locally:"
echo ""
echo "1. Show help:"
echo "   docker run --rm ${IMAGE_NAME}:${VERSION} help"
echo ""
echo "2. Create config:"
echo "   docker run --rm -v \$(pwd):/app/output ${IMAGE_NAME}:${VERSION} setup"
echo ""
echo "3. Deploy (with AWS credentials):"
echo "   docker run --rm \\"
echo "     -v ~/.aws:/root/.aws:ro \\"
echo "     -v \$(pwd)/config.yaml:/app/config/config.yaml:ro \\"
echo "     -v \$(pwd)/files:/app/files:ro \\"
echo "     ${IMAGE_NAME}:${VERSION} create"
echo ""
echo "To push to registry (requires authentication):"
echo "   docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
echo "   docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
