#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import logging
import subprocess
import sys
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DockerVerifier:
    """Verifies Docker installation and ensures service is running."""

    def __init__(self):
        pass

    def check_docker_command(self) -> bool:
        """Check if docker command is available."""
        try:
            result = subprocess.run(
                ["which", "docker"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                logger.info("Docker command found")
                return True
            else:
                logger.error("Docker command not found")
                return False

        except Exception as e:
            logger.error(f"Error checking docker command: {e}")
            return False

    def check_docker_service(self) -> bool:
        """Check if Docker service is running."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "--quiet", "docker"], timeout=10
            )

            if result.returncode == 0:
                logger.info("Docker service is active")
                return True
            else:
                logger.warning("Docker service is not active")
                return False

        except Exception as e:
            logger.error(f"Error checking docker service: {e}")
            return False

    def start_docker_service(self) -> bool:
        """Start Docker service if not running."""
        try:
            logger.info("Starting Docker service...")
            result = subprocess.run(
                ["systemctl", "start", "docker"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("Docker service started successfully")
                # Wait a moment for the service to be ready
                time.sleep(3)
                return True
            else:
                logger.error(f"Failed to start Docker service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error starting docker service: {e}")
            return False

    def test_docker_functionality(self) -> bool:
        """Test basic Docker functionality."""
        try:
            logger.info("Testing Docker functionality...")
            result = subprocess.run(
                ["docker", "version"], capture_output=True, text=True, timeout=15
            )

            if result.returncode == 0:
                logger.info("Docker version check successful")

                # Test docker info
                result = subprocess.run(
                    ["docker", "info"], capture_output=True, text=True, timeout=15
                )

                if result.returncode == 0:
                    logger.info("Docker info check successful")
                    return True
                else:
                    logger.error(f"Docker info failed: {result.stderr}")
                    return False
            else:
                logger.error(f"Docker version failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error testing docker functionality: {e}")
            return False

    def check_docker_compose(self) -> bool:
        """Check Docker Compose availability."""
        try:
            logger.info("Checking Docker Compose...")
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.info("Docker Compose is available")
                return True
            else:
                logger.warning("Docker Compose not available or not working")
                return False

        except Exception as e:
            logger.warning(f"Error checking docker compose: {e}")
            return False

    def verify_docker_setup(self) -> bool:
        """Complete Docker verification process."""
        logger.info("Starting Docker verification...")

        # Check if docker command exists
        if not self.check_docker_command():
            logger.error("Docker is not installed")
            return False

        # Check if service is running
        if not self.check_docker_service():
            # Try to start the service
            if not self.start_docker_service():
                logger.error("Cannot start Docker service")
                return False

            # Verify service is now running
            if not self.check_docker_service():
                logger.error("Docker service failed to start properly")
                return False

        # Test Docker functionality
        if not self.test_docker_functionality():
            logger.error("Docker functionality test failed")
            return False

        # Check Docker Compose (optional)
        self.check_docker_compose()

        logger.info("Docker verification completed successfully")
        return True


def main():
    """Main entry point for Docker verification."""
    verifier = DockerVerifier()

    if verifier.verify_docker_setup():
        logger.info("Docker is properly configured and running")
        return 0
    else:
        logger.error("Docker verification failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
