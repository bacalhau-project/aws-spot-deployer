#!/usr/bin/env bash
# Simplified run script for spot-deployer container

set -e

# Default values
IMAGE=${SPOT_IMAGE:-"ghcr.io/yourusername/spot-deployer:latest"}
CONFIG_FILE=${SPOT_CONFIG_FILE:-"./config.yaml"}
FILES_DIR=${SPOT_FILES_DIR:-"./files"}
OUTPUT_DIR=${SPOT_OUTPUT_DIR:-"./output"}

# Create directories if they don't exist
mkdir -p "$FILES_DIR" "$OUTPUT_DIR"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    echo "Please create a config.yaml file or set SPOT_CONFIG_FILE"
    exit 1
fi

# Pull latest image
echo "Pulling latest image..."
docker pull "$IMAGE"

# Run the container
docker run --rm -it \
    -v "$HOME/.ssh:/root/.ssh:ro" \
    -v "$(realpath "$CONFIG_FILE"):/app/config/config.yaml:ro" \
    -v "$(realpath "$FILES_DIR"):/app/files:ro" \
    -v "$(realpath "$OUTPUT_DIR"):/app/output" \
    -e AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY \
    -e AWS_SESSION_TOKEN \
    -e AWS_DEFAULT_REGION \
    -e AWS_REGION \
    -e BACALHAU_API_HOST \
    -e BACALHAU_API_TOKEN \
    -e BACALHAU_API_KEY \
    -e TERM \
    "$IMAGE" "$@"
