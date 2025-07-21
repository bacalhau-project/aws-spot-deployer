#!/usr/bin/env python3
"""Direct Bacalhau API client for node management."""
import json
import os
import subprocess
import urllib.parse
import urllib.request
import ssl


def get_nodes():
    """Get list of nodes from Bacalhau API."""
    api_host = os.environ.get("BACALHAU_API_HOST", "")
    api_key = os.environ.get("BACALHAU_API_KEY", "")
    
    if not api_host:
        return None
        
    # Build the full URL - try different endpoints
    urls_to_try = [
        f"{api_host}/api/v1/orchestrator/nodes",  # New API endpoint
        f"{api_host}/api/v1/nodes",  # Old API endpoint
    ]
    
    # Create SSL context that doesn't verify certificates (for self-signed certs)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    for url in urls_to_try:
        # Create request with headers
        req = urllib.request.Request(url)
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Accept", "application/json")
        
        try:
            with urllib.request.urlopen(req, context=ssl_context) as response:
                data = response.read()
                return json.loads(data)
        except urllib.error.HTTPError as e:
            # Try next URL
            continue
        except Exception as e:
            # Log to stderr, not stdout
            import sys
            print(f"[DEBUG] Error fetching nodes from {url}: {e}", file=sys.stderr)
            continue
    
    return None


def delete_node(node_id):
    """Delete a node using Bacalhau API."""
    api_host = os.environ.get("BACALHAU_API_HOST", "")
    api_key = os.environ.get("BACALHAU_API_KEY", "")
    
    if not api_host:
        return False
        
    # Build the full URL - try different endpoints
    urls_to_try = [
        f"{api_host}/api/v1/orchestrator/nodes/{node_id}",  # New API endpoint
        f"{api_host}/api/v1/nodes/{node_id}",  # Old API endpoint
    ]
    
    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    for url in urls_to_try:
        # Create DELETE request
        req = urllib.request.Request(url, method='DELETE')
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
        
        try:
            with urllib.request.urlopen(req, context=ssl_context) as response:
                return response.status in [200, 204]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Try next URL
                continue
            # Log to stderr
            import sys
            print(f"[DEBUG] Error deleting node {node_id} from {url}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            import sys
            print(f"[DEBUG] Error deleting node {node_id}: {e}", file=sys.stderr)
            continue
    
    return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: bacalhau_api.py list|delete <node_id>")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "list":
        nodes = get_nodes()
        if nodes:
            print(json.dumps(nodes))
        else:
            print("[]")
    elif command == "delete" and len(sys.argv) > 2:
        node_id = sys.argv[2]
        success = delete_node(node_id)
        sys.exit(0 if success else 1)
    else:
        print("Invalid command")
        sys.exit(1)