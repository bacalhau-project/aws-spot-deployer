#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "pyyaml",
# ]
# ///

import os
import sys
import subprocess
import logging
import time
import yaml
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/tmp/setup_orchestrator.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class SetupOrchestrator:
    """Orchestrates the setup of spot instances through configurable stages."""

    def __init__(self, config_path: str = "/bacalhau_node/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.setup_stages = self._load_setup_stages()
        self.metadata = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def _load_setup_stages(self) -> List[Dict[str, Any]]:
        """Load setup stages from config or use defaults."""
        stages = self.config.get("setup_stages", [])

        # If no stages defined, use the default setup sequence
        if not stages:
            stages = [
                {
                    "name": "cloud_metadata",
                    "script": "cloud_metadata.py",
                    "timeout": 60,
                    "required": True,
                    "description": "Detect cloud provider and gather metadata",
                },
                {
                    "name": "docker_verification",
                    "script": "verify_docker.py",
                    "timeout": 30,
                    "required": True,
                    "description": "Verify Docker installation and service",
                },
                {
                    "name": "bacalhau_setup",
                    "script": "setup_bacalhau.py",
                    "timeout": 120,
                    "required": True,
                    "description": "Configure and start Bacalhau services",
                },
                {
                    "name": "custom_commands",
                    "script": "additional_commands.sh",
                    "timeout": 300,
                    "required": False,
                    "description": "Execute additional custom commands",
                },
            ]

        return stages

    def _run_command(
        self, command: str, timeout: int = 300, shell: bool = True
    ) -> tuple[bool, str, str]:
        """Execute a command with timeout and return success status and output."""
        try:
            logger.info(f"Executing command: {command}")
            result = subprocess.run(
                command, shell=shell, capture_output=True, text=True, timeout=timeout
            )

            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if success:
                logger.info(f"Command succeeded: {command}")
                if stdout:
                    logger.debug(f"STDOUT: {stdout}")
            else:
                logger.error(f"Command failed: {command}")
                logger.error(f"Exit code: {result.returncode}")
                if stderr:
                    logger.error(f"STDERR: {stderr}")
                if stdout:
                    logger.error(f"STDOUT: {stdout}")

            return success, stdout, stderr

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {command}")
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return False, "", str(e)

    def _execute_stage(self, stage: Dict[str, Any]) -> bool:
        """Execute a single setup stage."""
        stage_name = stage.get("name", "unknown")
        script_name = stage.get("script", "")
        timeout = stage.get("timeout", 300)
        required = stage.get("required", True)
        description = stage.get("description", "")
        env_vars = stage.get("env_vars", {})

        logger.info(f"Starting stage: {stage_name}")
        if description:
            logger.info(f"Description: {description}")

        # Check if script exists
        script_path = f"/tmp/exs/{script_name}"
        if not os.path.exists(script_path):
            if required:
                logger.error(f"Required script not found: {script_path}")
                return False
            else:
                logger.warning(f"Optional script not found, skipping: {script_path}")
                return True

        # Set up environment variables
        env = os.environ.copy()
        for key, value in env_vars.items():
            # Support template substitution
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                var_name = value[2:-1]
                env[key] = self.metadata.get(var_name, env.get(var_name, ""))
            else:
                env[key] = str(value)

        # Determine how to execute the script
        if script_name.endswith(".py"):
            command = f"python3 {script_path}"
        elif script_name.endswith(".sh"):
            command = f"bash {script_path}"
        else:
            # Make it executable and run directly
            subprocess.run(["chmod", "+x", script_path], check=False)
            command = script_path

        # Execute the stage
        start_time = time.time()
        success, stdout, stderr = self._run_command(command, timeout)
        duration = time.time() - start_time

        if success:
            logger.info(
                f"Stage '{stage_name}' completed successfully in {duration:.2f}s"
            )
            return True
        else:
            if required:
                logger.error(
                    f"Required stage '{stage_name}' failed after {duration:.2f}s"
                )
                return False
            else:
                logger.warning(
                    f"Optional stage '{stage_name}' failed after {duration:.2f}s, continuing..."
                )
                return True

    def run_setup(self) -> bool:
        """Execute all setup stages in sequence."""
        logger.info("Starting setup orchestration")
        logger.info(f"Total stages to execute: {len(self.setup_stages)}")

        start_time = time.time()
        failed_stages = []

        for i, stage in enumerate(self.setup_stages, 1):
            stage_name = stage.get("name", f"stage_{i}")
            logger.info(f"=== Stage {i}/{len(self.setup_stages)}: {stage_name} ===")

            if not self._execute_stage(stage):
                failed_stages.append(stage_name)
                if stage.get("required", True):
                    logger.error(f"Setup failed at required stage: {stage_name}")
                    return False

        total_duration = time.time() - start_time

        if failed_stages:
            logger.warning(
                f"Setup completed with {len(failed_stages)} optional stage failures: {failed_stages}"
            )
        else:
            logger.info("All setup stages completed successfully")

        logger.info(f"Total setup duration: {total_duration:.2f}s")
        return True

    def run_custom_command(self, command: str, timeout: int = 300) -> bool:
        """Execute a custom command with proper logging."""
        logger.info(f"Executing custom command: {command}")
        success, stdout, stderr = self._run_command(command, timeout)

        if success:
            logger.info("Custom command completed successfully")
            if stdout:
                print(stdout)
        else:
            logger.error("Custom command failed")
            if stderr:
                print(stderr, file=sys.stderr)

        return success


def main():
    """Main entry point for setup orchestrator."""
    # Check if running as custom command
    if len(sys.argv) > 1 and sys.argv[1] == "--custom-command":
        if len(sys.argv) < 3:
            print(
                "Usage: setup_orchestrator.py --custom-command '<command>'",
                file=sys.stderr,
            )
            sys.exit(1)

        command = " ".join(sys.argv[2:])
        orchestrator = SetupOrchestrator()
        success = orchestrator.run_custom_command(command)
        sys.exit(0 if success else 1)

    # Normal setup orchestration
    orchestrator = SetupOrchestrator()
    success = orchestrator.run_setup()

    if success:
        logger.info("Setup orchestration completed successfully")
        sys.exit(0)
    else:
        logger.error("Setup orchestration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
