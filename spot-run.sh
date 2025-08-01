#!/usr/bin/env bash
# Simplified run script for spot-deployer using uvx

set -e

# Default values
GITHUB_REPO=${SPOT_GITHUB_REPO:-"bacalhau-project/aws-spot-deployer"}
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

# Set environment variables for spot-deployer
export SPOT_CONFIG_FILE="$CONFIG_FILE"
export SPOT_FILES_DIR="$FILES_DIR"
export SPOT_OUTPUT_DIR="$OUTPUT_DIR"

# Run spot-deployer using uvx
exec uvx --from git+https://github.com/${GITHUB_REPO} spot-deployer "$@"
