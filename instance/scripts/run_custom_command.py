#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import sys
import subprocess
import logging
import os
import json
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("/tmp/custom_command.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class CustomCommandRunner:
    """Executes arbitrary commands with proper security controls and logging."""

    def __init__(self):
        self.allowed_commands = self._load_allowed_commands()

    def _load_allowed_commands(self) -> Dict[str, Any]:
        """Load allowed commands configuration."""
        config_path = "/usr/local/etc/allowed_commands.json"

        # Default configuration if file doesn't exist
        default_config = {
            "allow_all": True,  # Set to False for strict mode
            "allowed_commands": [
                "docker",
                "systemctl",
                "curl",
                "wget",
                "apt",
                "yum",
                "dnf",
                "pip",
                "pip3",
                "python",
                "python3",
                "bash",
                "sh",
                "ls",
                "ps",
                "netstat",
                "ss",
                "lsof",
            ],
            "forbidden_patterns": [
                "rm -rf /",
                "sudo rm",
                "format",
                "mkfs",
                "dd if=",
                "> /dev/sd",
                "shutdown",
                "reboot",
                "halt",
            ],
            "max_execution_time": 600,  # 10 minutes
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                return default_config

        except Exception as e:
            logger.warning(
                f"Error loading allowed commands config: {e}, using defaults"
            )
            return default_config

    def _is_command_allowed(self, command: str) -> tuple[bool, str]:
        """Check if a command is allowed to be executed."""

        # Check forbidden patterns first
        for pattern in self.allowed_commands.get("forbidden_patterns", []):
            if pattern.lower() in command.lower():
                return False, f"Command contains forbidden pattern: {pattern}"

        # If allow_all is True, allow anything not explicitly forbidden
        if self.allowed_commands.get("allow_all", True):
            return True, "Command allowed (allow_all mode)"

        # Check against whitelist
        command_parts = command.strip().split()
        if not command_parts:
            return False, "Empty command"

        base_command = command_parts[0]

        # Check if base command is in allowed list
        allowed_cmds = self.allowed_commands.get("allowed_commands", [])
        for allowed_cmd in allowed_cmds:
            if base_command == allowed_cmd or base_command.endswith(f"/{allowed_cmd}"):
                return True, f"Command allowed: {allowed_cmd}"

        return False, f"Command not in allowed list: {base_command}"

    def execute_command(
        self, command: str, timeout: int = None
    ) -> tuple[bool, str, str]:
        """Execute a command with security checks and proper logging."""

        # Security check
        allowed, reason = self._is_command_allowed(command)
        if not allowed:
            logger.error(f"Command blocked: {command} - {reason}")
            return False, "", f"Security check failed: {reason}"

        logger.info(f"Executing command: {command} - {reason}")

        # Use configured timeout or default
        execution_timeout = timeout or self.allowed_commands.get(
            "max_execution_time", 600
        )

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=execution_timeout,
            )

            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if success:
                logger.info(f"Command completed successfully: {command}")
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
            error_msg = f"Command timed out after {execution_timeout}s"
            logger.error(f"{error_msg}: {command}")
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Error executing command: {e}"
            logger.error(f"{error_msg}: {command}")
            return False, "", error_msg

    def execute_script_file(
        self, script_path: str, args: List[str] = None
    ) -> tuple[bool, str, str]:
        """Execute a script file with arguments."""

        if not os.path.exists(script_path):
            error_msg = f"Script file not found: {script_path}"
            logger.error(error_msg)
            return False, "", error_msg

        # Make script executable
        try:
            os.chmod(script_path, 0o755)
        except Exception as e:
            logger.warning(f"Could not make script executable: {e}")

        # Build command
        command_parts = [script_path]
        if args:
            command_parts.extend(args)

        command = " ".join(command_parts)
        return self.execute_command(command)


def print_usage():
    """Print usage information."""
    print("""
Custom Command Runner

Usage:
    run_custom_command.py --command "<command>"
    run_custom_command.py --script "<script_path>" [arg1 arg2 ...]
    run_custom_command.py --help

Examples:
    run_custom_command.py --command "docker ps"
    run_custom_command.py --command "systemctl status docker"
    run_custom_command.py --script "/tmp/my_script.sh" arg1 arg2

Options:
    --command    Execute a shell command
    --script     Execute a script file with optional arguments
    --help       Show this help message

Security:
    Commands are checked against security policies before execution.
    See /usr/local/etc/allowed_commands.json for configuration.
""")


def main():
    """Main entry point for custom command runner."""

    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print_usage()
        return 0

    runner = CustomCommandRunner()

    if sys.argv[1] == "--command":
        if len(sys.argv) < 3:
            print("Error: --command requires a command argument", file=sys.stderr)
            return 1

        command = " ".join(sys.argv[2:])
        success, stdout, stderr = runner.execute_command(command)

        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)

        return 0 if success else 1

    elif sys.argv[1] == "--script":
        if len(sys.argv) < 3:
            print("Error: --script requires a script path argument", file=sys.stderr)
            return 1

        script_path = sys.argv[2]
        script_args = sys.argv[3:] if len(sys.argv) > 3 else []

        success, stdout, stderr = runner.execute_script_file(script_path, script_args)

        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)

        return 0 if success else 1

    else:
        print(f"Error: Unknown option '{sys.argv[1]}'", file=sys.stderr)
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
