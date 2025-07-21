#!/bin/bash
# Test the destroy command with Bacalhau cleanup inside Docker

echo "=== Testing destroy command with Bacalhau cleanup in Docker ==="
echo ""

# Check environment
echo "Environment variables:"
echo "BACALHAU_API_HOST: ${BACALHAU_API_HOST:-NOT SET}"
echo "BACALHAU_API_KEY: ${BACALHAU_API_KEY:+SET}"
echo ""

# Test 1: Run destroy in verbose mode
echo "Test 1: Running destroy command in verbose mode..."
./spot-dev destroy -v

echo ""
echo "Test 2: Testing node list directly in container..."
./spot-dev bash -c "BACALHAU_API_TLS_USETLS=true bacalhau node list --output json | head -c 200"

echo ""
echo "Test 3: Running Python test script in container..."
./spot-dev bash -c "python /app/test_bacalhau_in_docker.py"