#!/usr/bin/env python3
"""Clean up all disconnected Bacalhau nodes."""

import json
import os
import subprocess
import sys


def main():
    api_host = os.environ.get("BACALHAU_API_HOST")
    api_token = os.environ.get("BACALHAU_API_TOKEN") or os.environ.get("BACALHAU_API_KEY")

    if not api_host or not api_token:
        print("ERROR: Missing environment variables:")
        if not api_host:
            print("  - BACALHAU_API_HOST")
        if not api_token:
            print("  - BACALHAU_API_TOKEN or BACALHAU_API_KEY")
        sys.exit(1)

    print(f"Fetching nodes from {api_host}...")

    # Get node list
    cmd = ["bacalhau", "node", "list", "--output", "json", "--api-host", api_host]
    env = os.environ.copy()
    env["BACALHAU_API_TOKEN"] = api_token
    env["BACALHAU_API_KEY"] = api_token

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"ERROR: Failed to list nodes: {result.stderr}")
        sys.exit(1)

    try:
        nodes = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("ERROR: Failed to parse node list JSON")
        sys.exit(1)

    # Find disconnected compute nodes
    disconnected_nodes = [
        node
        for node in nodes
        if (
            node.get("Connection") == "DISCONNECTED"
            and node.get("Info", {}).get("NodeType") == "Compute"
        )
    ]

    print(f"\nFound {len(disconnected_nodes)} disconnected compute nodes")

    if not disconnected_nodes:
        print("No cleanup needed.")
        return

    # Delete each node
    deleted = 0
    failed = 0

    for node in disconnected_nodes:
        node_id = node.get("Info", {}).get("NodeID", "")
        if not node_id:
            continue

        print(f"Deleting {node_id}...", end=" ")
        cmd = ["bacalhau", "node", "delete", node_id, "--api-host", api_host]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        if result.returncode == 0:
            print("✓")
            deleted += 1
        else:
            print(f"✗ ({result.stderr.strip()})")
            failed += 1

    print(f"\nSummary: {deleted} deleted, {failed} failed")


if __name__ == "__main__":
    main()
