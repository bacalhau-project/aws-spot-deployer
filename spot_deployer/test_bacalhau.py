#!/usr/bin/env python3
"""Test bacalhau node listing functionality."""
import os
import subprocess
import json

print("Testing Bacalhau node listing...")

# Get environment
api_host = os.environ.get("BACALHAU_API_HOST", "")
api_key = os.environ.get("BACALHAU_API_KEY", "")

print(f"Original API Host: {api_host}")
print(f"API Key: {'SET' if api_key else 'NOT SET'}")

# Parse the API host
if api_host.startswith("https://"):
    api_host_clean = api_host[8:]
    use_tls = "true"
elif api_host.startswith("http://"):
    api_host_clean = api_host[7:]
    use_tls = "false"
else:
    api_host_clean = api_host
    use_tls = "true"

# Split host and port
if ":" in api_host_clean:
    host_parts = api_host_clean.split(":")
    host = host_parts[0]
    port = host_parts[1]
else:
    host = api_host_clean
    port = "1234"

print(f"Parsed - Host: {host}, Port: {port}, TLS: {use_tls}")

# Build command - let bacalhau use environment variables
cmd = ["bacalhau", "node", "list", "--output", "json"]
print(f"Command: {' '.join(cmd)}")

# Set environment
env = os.environ.copy()
env["BACALHAU_API_HOST"] = host
env["BACALHAU_API_PORT"] = port
env["BACALHAU_API_TLS_USETLS"] = use_tls
if api_key:
    env["BACALHAU_API_KEY"] = api_key

# Run command
result = subprocess.run(cmd, capture_output=True, text=True, env=env)

print(f"\nExit code: {result.returncode}")
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
            print("\nFirst few disconnected nodes:")
            for n in disconnected[:3]:
                print(f"  - {n.get('Info', {}).get('NodeID', 'unknown')}")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Raw output: {result.stdout[:200]}")