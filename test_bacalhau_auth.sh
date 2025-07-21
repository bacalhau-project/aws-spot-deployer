#!/bin/bash

echo "=== Testing Bacalhau Authentication Methods ==="
echo ""

# Extract host without protocol
ORIGINAL_HOST="$BACALHAU_API_HOST"
HOST_WITHOUT_PROTOCOL=$(echo "$BACALHAU_API_HOST" | sed 's|https://||' | sed 's|http://||')
HOST_WITHOUT_PORT=$(echo "$HOST_WITHOUT_PROTOCOL" | cut -d: -f1)
PORT=$(echo "$HOST_WITHOUT_PROTOCOL" | cut -d: -f2)

echo "Original BACALHAU_API_HOST: $ORIGINAL_HOST"
echo "Host without protocol: $HOST_WITHOUT_PROTOCOL"
echo "Host without port: $HOST_WITHOUT_PORT"
echo "Port: $PORT"
echo ""

# Test 1: Environment variables with TLS
echo "Test 1: Using environment variables with TLS..."
export BACALHAU_API_HOST="$HOST_WITHOUT_PORT"
export BACALHAU_API_PORT="$PORT"
export BACALHAU_API_TLS_USETLS="true"
bacalhau node list --output json 2>&1 | head -5

echo ""
echo "Test 2: Using --api-host flag with host:port..."
bacalhau node list --output json --api-host="$HOST_WITHOUT_PROTOCOL" 2>&1 | head -5

echo ""
echo "Test 3: Using separate --api-host and --api-port flags..."
bacalhau node list --output json --api-host="$HOST_WITHOUT_PORT" --api-port="$PORT" 2>&1 | head -5

echo ""
echo "Test 4: Using --insecure flag..."
export BACALHAU_API_HOST="$HOST_WITHOUT_PORT"
export BACALHAU_API_PORT="$PORT"
bacalhau --insecure node list --output json 2>&1 | head -5

echo ""
echo "Test 5: Using --tls flag..."
export BACALHAU_API_HOST="$HOST_WITHOUT_PORT"
export BACALHAU_API_PORT="$PORT"
bacalhau --tls node list --output json 2>&1 | head -5