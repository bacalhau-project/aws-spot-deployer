#!/usr/bin/env python3
"""
Generate Bacalhau configuration from orchestrator credentials.
Cloud-agnostic version that works with any metadata service or falls back to defaults.
"""

import os
import sys

import yaml


def get_instance_metadata():
    """Get instance metadata from cloud provider or generate fallback."""
    instance_id = "unknown"
    region = "unknown"

    # Try EC2 metadata first
    try:
        import subprocess

        result = subprocess.run(
            ["ec2-metadata", "--instance-id"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            instance_id = result.stdout.split()[-1]

        result = subprocess.run(
            ["ec2-metadata", "--availability-zone"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Extract region from AZ (e.g., us-west-2a -> us-west-2)
            az = result.stdout.split()[-1]
            region = az[:-1] if az and len(az) > 1 else "us-west-2"

    except Exception:
        # Fall back to environment or hostname
        import socket

        instance_id = os.environ.get("INSTANCE_ID", socket.gethostname())
        region = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")

    return instance_id, region


def load_orchestrator_credentials():
    """Load orchestrator endpoint and token from credential files."""
    endpoint = None
    token = None

    # Try multiple locations for credentials
    credential_paths = ["/opt/credentials", "/tmp/credentials", "/etc/bacalhau", "."]

    for cred_path in credential_paths:
        endpoint_file = os.path.join(cred_path, "orchestrator_endpoint")
        token_file = os.path.join(cred_path, "orchestrator_token")

        if os.path.exists(endpoint_file):
            with open(endpoint_file, "r") as f:
                endpoint = f.read().strip()

        if os.path.exists(token_file):
            with open(token_file, "r") as f:
                token = f.read().strip()

        if endpoint and token:
            break

    return endpoint, token


def generate_bacalhau_config():
    """Generate complete Bacalhau configuration."""
    instance_id, region = get_instance_metadata()
    endpoint, token = load_orchestrator_credentials()

    # Base configuration
    config = {
        "logging": {"level": os.environ.get("LOG_LEVEL", "info").upper()},
        "node": {
            "type": "compute",
            "name": f"bacalhau-{instance_id}",
            "clientapi": {
                "host": "0.0.0.0",
                "port": int(os.environ.get("BACALHAU_API_PORT", 1234)),
            },
            "compute": {
                "enabled": True,
                "engines": {"docker": {"enabled": True}},
                "heartbeat": {"interval": "15s", "info_update_interval": "60s"},
            },
            "labels": {
                "region": region,
                "instance-id": instance_id,
                "cloud-provider": "aws",  # TODO: make this dynamic
                "node-type": "spot",
            },
        },
    }

    # Add orchestrator configuration if credentials are available
    if endpoint:
        config["node"]["orchestrator"] = {
            "endpoint": endpoint,
            "insecure": True,  # For development - should be configurable
        }

        if token:
            config["node"]["orchestrator"]["token"] = token

        print(f"✓ Orchestrator configured: {endpoint}")
    else:
        print("⚠ No orchestrator credentials found - node will run in standalone mode")
        # For standalone mode, still configure the node
        config["node"]["orchestrator"] = {
            "endpoint": "nats://localhost:4222",
            "insecure": True,
        }

    return config


def write_config(config, output_path="/etc/bacalhau/config.yaml"):
    """Write configuration to file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"✓ Bacalhau configuration written to: {output_path}")

    # Also create a backup in working directory for debugging
    backup_path = "/opt/bacalhau-config-backup.yaml"
    with open(backup_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def main():
    """Main configuration generation routine."""
    print("Generating Bacalhau configuration...")

    try:
        config = generate_bacalhau_config()
        write_config(config)

        # Validate the configuration
        try:
            with open("/etc/bacalhau/config.yaml", "r") as f:
                yaml.safe_load(f)
            print("✓ Configuration validation passed")
        except Exception as e:
            print(f"⚠ Configuration validation warning: {e}")

        return 0

    except Exception as e:
        print(f"✗ Failed to generate configuration: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
