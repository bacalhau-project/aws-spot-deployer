#!/usr/bin/env python3
import os
import subprocess
import json

print("Testing Bacalhau node listing...")

# Get environment
api_host = os.environ.get("BACALHAU_API_HOST", "")
api_key = os.environ.get("BACALHAU_API_KEY", "")

print(f"API Host: {api_host}")
print(f"API Key: {'SET' if api_key else 'NOT SET'}")

# Build command - let bacalhau use environment variables
cmd = ["bacalhau", "node", "list", "--output", "json"]
print(f"Command: {' '.join(cmd)}")

# Set environment
env = os.environ.copy()
env["BACALHAU_API_TLS_USETLS"] = "true"
# Bacalhau will use BACALHAU_API_HOST and BACALHAU_API_KEY from environment

# Run command
result = subprocess.run(cmd, capture_output=True, text=True, env=env)

print(f"Exit code: {result.returncode}")
if result.returncode != 0:
    print(f"Error: {result.stderr[:500]}")
    print(f"Output: {result.stdout[:500]}")
else:
    try:
        nodes = json.loads(result.stdout)
        print(f"Successfully parsed {len(nodes)} nodes")
        disconnected = [n for n in nodes if n.get('Connection') == 'DISCONNECTED' and n.get('Info', {}).get('NodeType') == 'Compute']
        print(f"Found {len(disconnected)} disconnected compute nodes")
        if disconnected:
            print("First few:")
            for n in disconnected[:3]:
                print(f"  - {n.get('Info', {}).get('NodeID', 'unknown')}")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Raw output: {result.stdout[:200]}")