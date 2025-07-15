#!/usr/bin/env uv run -s
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "pyyaml",
# ]
# ///

import logging
import os
import subprocess
from typing import Dict

import requests  # type: ignore
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACALHAU_NODE_DIR = os.getenv("BACALHAU_NODE_DIR", "/bacalhau_node")


class CloudMetadataDetector:
    """Detects cloud provider and gathers metadata for instance configuration."""

    def __init__(self):
        self.metadata = {}

    def detect_cloud_provider(self) -> str:
        """Detect the cloud provider using cloud-init."""
        try:
            cloud = subprocess.getoutput("cloud-init query cloud-name")
            logger.info(f"Detected cloud provider: {cloud}")
            return cloud
        except Exception as e:
            logger.error(f"Error detecting cloud provider: {e}")
            return "unknown"

    def get_aws_metadata(self) -> Dict[str, str]:
        """Get AWS instance metadata."""
        try:
            logger.info("Gathering AWS metadata")
            # Get IMDSv2 token
            token = requests.put(
                "http://169.254.169.254/latest/api/token",
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
                timeout=5,
            ).text

            headers = {"X-aws-ec2-metadata-token": token}

            metadata = {
                "CLOUD_PROVIDER": "AWS",
                "REGION": requests.get(
                    "http://169.254.169.254/latest/meta-data/placement/region",
                    headers=headers,
                    timeout=5,
                ).text,
                "ZONE": requests.get(
                    "http://169.254.169.254/latest/meta-data/placement/availability-zone",
                    headers=headers,
                    timeout=5,
                ).text,
                "PUBLIC_IP": requests.get(
                    "http://169.254.169.254/latest/meta-data/public-ipv4",
                    headers=headers,
                    timeout=5,
                ).text,
                "PRIVATE_IP": requests.get(
                    "http://169.254.169.254/latest/meta-data/local-ipv4",
                    headers=headers,
                    timeout=5,
                ).text,
                "INSTANCE_ID": requests.get(
                    "http://169.254.169.254/latest/meta-data/instance-id",
                    headers=headers,
                    timeout=5,
                ).text,
                "INSTANCE_TYPE": requests.get(
                    "http://169.254.169.254/latest/meta-data/instance-type",
                    headers=headers,
                    timeout=5,
                ).text,
            }

            logger.info(f"AWS metadata gathered: {metadata}")
            return metadata

        except Exception as e:
            logger.error(f"Error gathering AWS metadata: {e}")
            return {}

    def get_gcp_metadata(self) -> Dict[str, str]:
        """Get GCP instance metadata."""
        try:
            logger.info("Gathering GCP metadata")
            headers = {"Metadata-Flavor": "Google"}

            zone_info = requests.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/zone",
                headers=headers,
                timeout=5,
            ).text

            metadata = {
                "CLOUD_PROVIDER": "GCP",
                "REGION": zone_info.split("/")[3],
                "ZONE": zone_info.split("/")[3],
                "PUBLIC_IP": requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip",
                    headers=headers,
                    timeout=5,
                ).text,
                "PRIVATE_IP": requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip",
                    headers=headers,
                    timeout=5,
                ).text,
                "INSTANCE_ID": requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/id",
                    headers=headers,
                    timeout=5,
                ).text,
                "INSTANCE_TYPE": requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/machine-type",
                    headers=headers,
                    timeout=5,
                ).text.split("/")[-1],
                "PROJECT_ID": requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/project/project-id",
                    headers=headers,
                    timeout=5,
                ).text,
            }

            logger.info(f"GCP metadata gathered: {metadata}")
            return metadata

        except Exception as e:
            logger.error(f"Error gathering GCP metadata: {e}")
            return {}

    def get_azure_metadata(self) -> Dict[str, str]:
        """Get Azure instance metadata."""
        try:
            logger.info("Gathering Azure metadata")
            azure_metadata = requests.get(
                "http://169.254.169.254/metadata/instance?api-version=2021-02-01",
                headers={"Metadata": "true"},
                timeout=5,
            ).json()

            metadata = {
                "CLOUD_PROVIDER": "AZURE",
                "REGION": azure_metadata["compute"]["location"],
                "ZONE": azure_metadata["compute"]["zone"],
                "PUBLIC_IP": requests.get("https://ip.me", timeout=5).text.strip(),
                "PRIVATE_IP": azure_metadata["network"]["interface"][0]["ipv4"][
                    "ipAddress"
                ][0]["privateIpAddress"],
                "INSTANCE_ID": azure_metadata["compute"]["vmId"],
                "INSTANCE_TYPE": azure_metadata["compute"]["vmSize"],
            }

            logger.info(f"Azure metadata gathered: {metadata}")
            return metadata

        except Exception as e:
            logger.error(f"Error gathering Azure metadata: {e}")
            return {}

    def gather_metadata(self) -> Dict[str, str]:
        """Gather metadata based on detected cloud provider."""
        cloud_provider = self.detect_cloud_provider()

        if cloud_provider == "aws":
            return self.get_aws_metadata()
        elif cloud_provider == "gce":
            return self.get_gcp_metadata()
        elif cloud_provider == "azure":
            return self.get_azure_metadata()
        else:
            logger.warning(f"Unknown cloud provider: {cloud_provider}")
            return {"CLOUD_PROVIDER": "UNKNOWN"}

    def save_metadata(self, metadata: Dict[str, str]) -> None:
        """Save metadata to node-info file."""
        try:
            os.makedirs(BACALHAU_NODE_DIR, exist_ok=True)

            with open(os.path.join(BACALHAU_NODE_DIR, "node-info"), "w") as f:
                for key, value in metadata.items():
                    f.write(f"{key}={value}\n")

            logger.info(f"Metadata saved to {BACALHAU_NODE_DIR}/node-info")

        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def add_labels_to_config(self, metadata: Dict[str, str]) -> None:
        """Add metadata as labels to Bacalhau configuration."""
        try:
            config_file = os.path.join(BACALHAU_NODE_DIR, "config.yaml")

            if not os.path.exists(config_file):
                logger.warning(f"Config file not found: {config_file}")
                return

            with open(config_file, "r") as f:
                config = yaml.safe_load(f) or {}

            # Initialize Labels section if not exists
            if "Labels" not in config:
                config["Labels"] = {}

            # Add metadata as labels
            for key, value in metadata.items():
                if key and value:
                    config["Labels"][key] = value
                    logger.info(f"Added label: {key}={value}")

            # Save updated config
            with open(config_file, "w") as f:
                yaml.dump(config, f, default_flow_style=False)

            logger.info("Labels added to Bacalhau configuration")

        except Exception as e:
            logger.error(f"Error adding labels to config: {e}")


def main():
    """Main entry point for cloud metadata detection."""
    detector = CloudMetadataDetector()

    # Gather metadata
    metadata = detector.gather_metadata()

    if not metadata:
        logger.error("Failed to gather cloud metadata")
        return 1

    # Save metadata
    detector.save_metadata(metadata)

    # Add labels to Bacalhau config
    detector.add_labels_to_config(metadata)

    logger.info("Cloud metadata detection completed successfully")
    return 0


if __name__ == "__main__":
    exit(main())
