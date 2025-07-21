#!/usr/bin/env python3
"""Test script to verify Bacalhau node cleanup works correctly."""

import os
import subprocess
import json
import sys

def test_bacalhau_cleanup():
    """Test the Bacalhau node cleanup functionality."""
    api_host = os.environ.get("BACALHAU_API_HOST")
    api_token = os.environ.get("BACALHAU_API_TOKEN") or os.environ.get("BACALHAU_API_KEY")
    
    if not api_host or not api_token:
        print("ERROR: Missing environment variables:")
        if not api_host:
            print("  - BACALHAU_API_HOST")
        if not api_token:
            print("  - BACALHAU_API_TOKEN or BACALHAU_API_KEY")
        return
    
    print(f"Using API host: {api_host}")
    print(f"API token found: {'Yes' if api_token else 'No'}")
    
    # Test 1: List nodes
    print("\n1. Testing node list command...")
    cmd = ["bacalhau", "node", "list", "--output", "json", "--api-host", api_host]
    env = os.environ.copy()
    env["BACALHAU_API_TOKEN"] = api_token
    env["BACALHAU_API_KEY"] = api_token
    
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    print(f"Command: {' '.join(cmd)}")
    print(f"Return code: {result.returncode}")
    
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        print(f"STDOUT: {result.stdout}")
        return
    
    # Test 2: Parse JSON
    print("\n2. Parsing node list JSON...")
    try:
        nodes = json.loads(result.stdout)
        print(f"Successfully parsed {len(nodes)} nodes")
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        print(f"First 500 chars of output: {result.stdout[:500]}")
        return
    
    # Test 3: Find disconnected nodes
    print("\n3. Finding disconnected compute nodes...")
    disconnected_nodes = []
    for node in nodes:
        print(f"Node: ID={node.get('ID', 'N/A')}, "
              f"Type={node.get('Type', 'N/A')}, "
              f"Connection={node.get('Connection', 'N/A')}, "
              f"NodeType={node.get('Info', {}).get('NodeType', 'N/A')}")
        
        if (node.get("Connection") == "DISCONNECTED" 
            and node.get("Type") == "Compute"):
            disconnected_nodes.append(node)
    
    print(f"\nFound {len(disconnected_nodes)} disconnected compute nodes")
    
    # Test 4: Show delete commands (dry run)
    if disconnected_nodes:
        print("\n4. Commands to delete disconnected nodes:")
        for node in disconnected_nodes[:5]:  # Show first 5
            node_id = node.get("ID", "")
            if node_id:
                cmd = ["bacalhau", "node", "delete", node_id, "--api-host", api_host]
                print(f"  {' '.join(cmd)}")
        
        if len(disconnected_nodes) > 5:
            print(f"  ... and {len(disconnected_nodes) - 5} more")

if __name__ == "__main__":
    test_bacalhau_cleanup()