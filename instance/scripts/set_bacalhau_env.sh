#!/bin/bash
# Simple script to read orchestrator credentials and create environment file for docker-compose

ENDPOINT_FILE="/opt/uploaded_files/orchestrator_endpoint"
TOKEN_FILE="/opt/uploaded_files/orchestrator_token"
ENV_FILE="/opt/uploaded_files/scripts/.bacalhau.env"

# Check if credential files exist
if [ ! -f "$ENDPOINT_FILE" ] || [ ! -f "$TOKEN_FILE" ]; then
    echo "WARNING: Orchestrator credential files not found"
    echo "BACALHAU_COMPUTE_ORCHESTRATORS=" > "$ENV_FILE"
    echo "BACALHAU_COMPUTE_AUTH_TOKEN=" >> "$ENV_FILE"
    exit 0
fi

# Read credentials
ENDPOINT=$(cat "$ENDPOINT_FILE" | tr -d '\n')
TOKEN=$(cat "$TOKEN_FILE" | tr -d '\n')

# Write environment file for docker-compose
# Viper uses underscore-separated uppercase for nested config
echo "BACALHAU_COMPUTE_ORCHESTRATORS=$ENDPOINT" > "$ENV_FILE"
echo "BACALHAU_COMPUTE_AUTH_TOKEN=$TOKEN" >> "$ENV_FILE"

echo "Created Bacalhau environment file with orchestrator configuration"