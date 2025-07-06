#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import os
import subprocess
import logging
import time
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACALHAU_NODE_DIR = os.getenv("BACALHAU_NODE_DIR", "/bacalhau_node")


class BacalhauSetup:
    """Handles Bacalhau service configuration and startup."""

    def __init__(self):
        self.node_dir = Path(BACALHAU_NODE_DIR)

    def check_config_file(self) -> bool:
        """Check if Bacalhau configuration file exists."""
        config_file = self.node_dir / "config.yaml"

        if config_file.exists():
            logger.info(f"Bacalhau config found: {config_file}")
            return True
        else:
            logger.error(f"Bacalhau config not found: {config_file}")
            return False

    def check_docker_compose_file(self) -> bool:
        """Check if Docker Compose file exists."""
        compose_file = self.node_dir / "docker-compose.yaml"

        if compose_file.exists():
            logger.info(f"Docker Compose file found: {compose_file}")
            return True
        else:
            logger.error(f"Docker Compose file not found: {compose_file}")
            return False

    def stop_existing_containers(self) -> bool:
        """Stop and remove any existing Bacalhau containers."""
        try:
            logger.info("Stopping existing Bacalhau containers...")

            # Change to the node directory
            os.chdir(self.node_dir)

            # Stop and remove containers
            result = subprocess.run(
                ["docker", "compose", "down"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("Docker Compose down completed")
            else:
                logger.warning(f"Docker Compose down had issues: {result.stderr}")

            # Check for stray containers and remove them
            result = subprocess.run(
                ["docker", "ps", "-a"], capture_output=True, text=True, timeout=10
            )

            if "bacalhau_node-bacalhau-node" in result.stdout:
                logger.info("Found stray Bacalhau containers, removing them...")
                subprocess.run(
                    "docker ps -a | grep 'bacalhau_node-bacalhau-node' | awk '{print $1}' | xargs -r docker rm -f",
                    shell=True,
                    timeout=30,
                )

            return True

        except Exception as e:
            logger.error(f"Error stopping existing containers: {e}")
            return False

    def pull_docker_images(self) -> bool:
        """Pull latest Docker images for Bacalhau."""
        try:
            logger.info("Pulling latest Docker images...")

            result = subprocess.run(
                ["docker", "compose", "pull"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout for pulling images
            )

            if result.returncode == 0:
                logger.info("Docker images pulled successfully")
                return True
            else:
                logger.error(f"Failed to pull Docker images: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error pulling Docker images: {e}")
            return False

    def start_bacalhau_services(self) -> bool:
        """Start Bacalhau services using Docker Compose."""
        try:
            logger.info("Starting Bacalhau services...")

            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                logger.info("Bacalhau services started successfully")
                return True
            else:
                logger.error(f"Failed to start Bacalhau services: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error starting Bacalhau services: {e}")
            return False

    def verify_services_running(self) -> bool:
        """Verify that Bacalhau services are running properly."""
        try:
            logger.info("Verifying Bacalhau services...")

            # Wait a moment for services to start
            time.sleep(5)

            result = subprocess.run(
                ["docker", "compose", "ps"], capture_output=True, text=True, timeout=15
            )

            if result.returncode == 0:
                output = result.stdout
                if "Up" in output:
                    logger.info("Bacalhau services are running")
                    return True
                else:
                    logger.error("Bacalhau services are not running properly")
                    logger.error(f"Service status: {output}")
                    return False
            else:
                logger.error(f"Failed to check service status: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error verifying services: {e}")
            return False

    def setup_bacalhau(self) -> bool:
        """Complete Bacalhau setup process."""
        logger.info("Starting Bacalhau setup...")

        # Check required files
        if not self.check_config_file():
            return False

        if not self.check_docker_compose_file():
            return False

        # Stop any existing containers
        if not self.stop_existing_containers():
            logger.warning("Failed to clean up existing containers, continuing...")

        # Pull latest images
        if not self.pull_docker_images():
            logger.warning("Failed to pull images, using existing ones...")

        # Start services
        if not self.start_bacalhau_services():
            return False

        # Verify services are running
        if not self.verify_services_running():
            return False

        logger.info("Bacalhau setup completed successfully")
        return True


def main():
    """Main entry point for Bacalhau setup."""
    setup = BacalhauSetup()

    if setup.setup_bacalhau():
        logger.info("Bacalhau is properly configured and running")
        return 0
    else:
        logger.error("Bacalhau setup failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
