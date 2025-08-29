#!/bin/bash
# Clean up disconnected nodes from Bacalhau cluster
# Requires: BACALHAU_API_HOST environment variable and bacalhau CLI installed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧹 Bacalhau Node Cleanup${NC}"

# Check if BACALHAU_API_HOST is set
if [ -z "$BACALHAU_API_HOST" ]; then
    echo -e "${RED}ERROR: BACALHAU_API_HOST environment variable is not set${NC}"
    echo "Please set it to your Bacalhau orchestrator endpoint"
    echo "Example: export BACALHAU_API_HOST=your-orchestrator.example.com"
    exit 1
fi

# Check if bacalhau CLI is installed
if ! command -v bacalhau &> /dev/null; then
    echo -e "${RED}ERROR: bacalhau CLI is not installed${NC}"
    echo "Please install bacalhau first: https://docs.bacalhau.org/getting-started/installation"
    exit 1
fi

# Get all nodes and their status
echo "Fetching nodes from ${BACALHAU_API_HOST}..."
NODES_JSON=$(bacalhau node list --output json 2>/dev/null || echo "[]")

if [ "$NODES_JSON" = "[]" ]; then
    echo -e "${YELLOW}No nodes found or unable to connect to API${NC}"
    exit 1
fi

# Parse nodes and find disconnected ones
echo "$NODES_JSON" | python3 -c "
import json
import sys
from datetime import datetime

data = json.load(sys.stdin)
if not data:
    print('No nodes found')
    sys.exit(0)

connected_count = 0
disconnected_nodes = []

print('\\n🔍 Scanning nodes...')

for node in data:
    node_info = node.get('Info', {})
    node_id = node_info.get('NodeID', 'Unknown')
    node_type = node_info.get('NodeType', 'Unknown')

    # Check connection status from the Connection field
    connection_status = node.get('Connection', 'Unknown')
    connection_state = node.get('ConnectionState', {})

    # Determine if connected
    is_connected = connection_status == 'CONNECTED'

    # Get last heartbeat
    last_heartbeat = connection_state.get('LastHeartbeat', 'Unknown')
    if last_heartbeat != 'Unknown':
        try:
            # Parse and format the timestamp
            dt = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
            last_heartbeat = dt.strftime('%Y-%m-%d %H:%M')
        except:
            pass

    # Count and collect disconnected nodes
    if is_connected:
        connected_count += 1
    else:
        disconnected_nodes.append(node_id)

print(f'📊 Found {len(data)} total nodes: {connected_count} connected, {len(disconnected_nodes)} disconnected')

if disconnected_nodes:
    print(f'🗑️  Will remove {len(disconnected_nodes)} disconnected nodes')

    # Write disconnected node IDs to temp file
    with open('/tmp/disconnected_nodes.txt', 'w') as f:
        for node_id in disconnected_nodes:
            f.write(f'{node_id}\\n')
else:
    print('✅ All nodes connected - no cleanup needed')
    # Create empty file to indicate no cleanup needed
    open('/tmp/disconnected_nodes.txt', 'w').close()
"

# Check if there are nodes to remove
if [ ! -s /tmp/disconnected_nodes.txt ]; then
    rm -f /tmp/disconnected_nodes.txt
    exit 0
fi

# Remove disconnected nodes (no confirmation)
echo "🗑️  Removing disconnected nodes..."
REMOVED_COUNT=0
FAILED_COUNT=0

# Create arrays to track results
REMOVED_NODES=()
FAILED_NODES=()

while IFS= read -r node_id; do
    if [ -n "$node_id" ]; then
        if bacalhau node delete "$node_id" >/dev/null 2>&1; then
            REMOVED_NODES+=("$(echo "$node_id" | cut -c1-12)...")
            ((REMOVED_COUNT++))
        else
            FAILED_NODES+=("$(echo "$node_id" | cut -c1-12)...")
            ((FAILED_COUNT++))
        fi
    fi
done < /tmp/disconnected_nodes.txt

# Display results in a compact table
if [ ${#REMOVED_NODES[@]} -gt 0 ]; then
    echo "┌─────────────────┐"
    echo "│ Removed Nodes   │"
    echo "├─────────────────┤"
    for node in "${REMOVED_NODES[@]}"; do
        printf "│ ✓ %-13s │\n" "$node"
    done
    echo "└─────────────────┘"
fi

if [ ${#FAILED_NODES[@]} -gt 0 ]; then
    echo "┌─────────────────┐"
    echo "│ Failed Nodes    │"
    echo "├─────────────────┤"
    for node in "${FAILED_NODES[@]}"; do
        printf "│ ✗ %-13s │\n" "$node"
    done
    echo "└─────────────────┘"
fi

# Cleanup
rm -f /tmp/disconnected_nodes.txt

# Final summary
if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "${GREEN}✅ Cleanup complete: ${REMOVED_COUNT} removed, ${RED}${FAILED_COUNT} failed${NC}"
else
    echo -e "${GREEN}✅ Cleanup complete: ${REMOVED_COUNT} removed${NC}"
fi

# Show brief updated status
FINAL_COUNT=$(bacalhau node list --output json 2>/dev/null | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data)) if data else print('0')" 2>/dev/null || echo "?")
echo "📊 Active nodes: $FINAL_COUNT"
