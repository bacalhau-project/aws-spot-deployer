#!/bin/bash
# Generate Bacalhau configuration with credentials from files

ENDPOINT_FILE="/opt/uploaded_files/orchestrator_endpoint"
TOKEN_FILE="/opt/uploaded_files/orchestrator_token"
TEMPLATE_FILE="/opt/uploaded_files/config/bacalhau-config.yaml"
OUTPUT_FILE="/bacalhau_node/config.yaml"

# Check if credential files exist
if [ ! -f "$ENDPOINT_FILE" ] || [ ! -f "$TOKEN_FILE" ]; then
    echo "WARNING: Orchestrator credential files not found, using template as-is"
    cp "$TEMPLATE_FILE" "$OUTPUT_FILE"
    exit 0
fi

# Read credentials
ENDPOINT=$(cat "$ENDPOINT_FILE" | tr -d '\n')
TOKEN=$(cat "$TOKEN_FILE" | tr -d '\n')

# Ensure endpoint has nats:// prefix and port
if [[ ! "$ENDPOINT" =~ ^nats:// ]]; then
    # Add nats:// prefix if missing
    if [[ ! "$ENDPOINT" =~ :[0-9]+$ ]]; then
        # Add default port if missing
        ENDPOINT="nats://${ENDPOINT}:4222"
    else
        ENDPOINT="nats://${ENDPOINT}"
    fi
fi

# Create the config file with credentials embedded
cat > "$OUTPUT_FILE" << EOF
# Bacalhau Compute Node Configuration
# Generated from template with credentials

# Node name provider - uses hostname for unique identification
NameProvider: hostname

# Data directory for Bacalhau
DataDir: /bacalhau_data

# API Configuration
API:
  Host: 0.0.0.0
  Port: 1234

# Compute node configuration
Compute:
  Enabled: true
  Orchestrators:
    - ${ENDPOINT}
  Auth:
    Token: "${TOKEN}"
  TLS:
    RequireTLS: true
  # Network port range for compute jobs
  Network:
    PortRangeStart: 20000
    PortRangeEnd: 30000
  # Heartbeat settings
  Heartbeat:
    InfoUpdateInterval: 1m0s
    Interval: 15s
  # Resource allocation - conservative for spot instances
  AllocatedCapacity:
    CPU: "70%"
    Memory: "70%"
    Disk: "50%"
    GPU: "0%"
  # Allow access to sensor data directories
  AllowListedLocalPaths:
    - "/opt/sensor/data:ro"
    - "/opt/sensor/exports:rw"
    - "/tmp:rw"
    - "/bacalhau_data:rw"

# Disable orchestrator mode
Orchestrator:
  Enabled: false

# Job admission control
JobAdmissionControl:
  Locality: anywhere

# Logging configuration
Logging:
  Level: info
  Mode: default
  LogDebugInfoInterval: 30s
EOF

echo "Generated Bacalhau configuration with orchestrator credentials"