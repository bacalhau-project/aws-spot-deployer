#!/bin/bash
# Debug script to test Bacalhau commands

echo "=== Testing Bacalhau Commands ==="
echo ""

echo "1. Environment variables:"
echo "BACALHAU_API_HOST: ${BACALHAU_API_HOST:-NOT SET}"
echo "BACALHAU_API_TOKEN: ${BACALHAU_API_TOKEN:+SET}"
echo "BACALHAU_API_KEY: ${BACALHAU_API_KEY:+SET}"
echo ""

echo "2. Testing bacalhau node list directly:"
bacalhau node list --output json > /tmp/nodes.json 2>&1
echo "Exit code: $?"
echo "Output size: $(wc -c < /tmp/nodes.json) bytes"
echo "First 500 chars:"
head -c 500 /tmp/nodes.json
echo ""
echo ""

echo "3. Testing with explicit environment:"
env BACALHAU_API_HOST="$BACALHAU_API_HOST" BACALHAU_API_TOKEN="${BACALHAU_API_TOKEN:-$BACALHAU_API_KEY}" bacalhau node list --output json > /tmp/nodes2.json 2>&1
echo "Exit code: $?"
echo "Output size: $(wc -c < /tmp/nodes2.json) bytes"
echo ""

echo "4. Parsing JSON to count nodes:"
if command -v jq > /dev/null; then
    echo "Total nodes: $(jq 'length' < /tmp/nodes.json 2>/dev/null || echo 'JSON parse failed')"
    echo "Disconnected compute nodes: $(jq '[.[] | select(.Connection == "DISCONNECTED" and .Info.NodeType == "Compute")] | length' < /tmp/nodes.json 2>/dev/null || echo 'JSON parse failed')"
else
    echo "jq not installed, trying Python:"
    python3 -c "
import json
try:
    with open('/tmp/nodes.json') as f:
        nodes = json.load(f)
    print(f'Total nodes: {len(nodes)}')
    disconnected = [n for n in nodes if n.get('Connection') == 'DISCONNECTED' and n.get('Info', {}).get('NodeType') == 'Compute']
    print(f'Disconnected compute nodes: {len(disconnected)}')
except Exception as e:
    print(f'Error: {e}')
"
fi