#!/bin/bash
# Test if environment variables are passed to Docker container

echo "=== Testing Environment Variables ==="
echo ""
echo "Host environment:"
echo "BACALHAU_API_HOST: ${BACALHAU_API_HOST:-NOT SET}"
echo "BACALHAU_API_TOKEN: ${BACALHAU_API_TOKEN:+SET}"
echo "BACALHAU_API_KEY: ${BACALHAU_API_KEY:+SET}"
echo ""

echo "Running container with spot-dev..."
./spot-dev bash -c 'echo "Container environment:"; echo "BACALHAU_API_HOST: ${BACALHAU_API_HOST:-NOT SET}"; echo "BACALHAU_API_TOKEN: ${BACALHAU_API_TOKEN:+SET}"; echo "BACALHAU_API_KEY: ${BACALHAU_API_KEY:+SET}"'