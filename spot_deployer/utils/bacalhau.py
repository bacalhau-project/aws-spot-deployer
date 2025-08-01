"""Bacalhau utilities."""

import json
import os
import subprocess


def remove_bacalhau_node(instance_id: str) -> bool:
    """Remove a Bacalhau node."""
    try:
        api_host = os.environ.get("BACALHAU_API_HOST")
        api_key = os.environ.get("BACALHAU_API_KEY")

        if not api_host or not api_key:
            return False

        cmd = ["bacalhau", "node", "list", "--output", "json", "--api-host", api_host]
        env = os.environ.copy()
        if api_key:
            env["BACALHAU_API_KEY"] = api_key

        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
        if result.returncode != 0:
            return False

        nodes = json.loads(result.stdout)
        node_id_to_remove = None
        for node in nodes:
            node_id = node.get("Info", {}).get("NodeID", "")
            if instance_id in node_id:
                node_id_to_remove = node_id
                break

        if not node_id_to_remove:
            return True

        cmd = ["bacalhau", "node", "delete", node_id_to_remove, "--api-host", api_host]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def cleanup_all_disconnected_nodes() -> int:
    """Clean up all disconnected Bacalhau nodes."""
    try:
        api_host = os.environ.get("BACALHAU_API_HOST")
        api_key = os.environ.get("BACALHAU_API_KEY")

        if not api_host:
            return 0

        cmd = ["bacalhau", "node", "list", "--output", "json", "--api-host", api_host]
        env = os.environ.copy()
        if api_key:
            env["BACALHAU_API_KEY"] = api_key

        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        if result.returncode != 0:
            return 0

        try:
            nodes = json.loads(result.stdout)
        except json.JSONDecodeError:
            return 0

        disconnected_nodes = [
            node
            for node in nodes
            if (
                node.get("Connection") == "DISCONNECTED"
                and node.get("Info", {}).get("NodeType") == "Compute"
            )
        ]

        if not disconnected_nodes:
            return 0

        deleted_count = 0
        for node in disconnected_nodes:
            node_id = node.get("Info", {}).get("NodeID", "")
            if node_id:
                cmd = ["bacalhau", "node", "delete", node_id, "--api-host", api_host]
                result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
                if result.returncode == 0:
                    deleted_count += 1
        return deleted_count
    except Exception:
        return 0
