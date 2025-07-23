#!/usr/bin/env uv run
"""
AWS Spot Instance Deployer - Main Entry Point

This tool deploys and manages AWS EC2 spot instances with a focus on simplicity.
"""

import os
import sys

from .commands import cmd_create, cmd_destroy, cmd_help, cmd_list, cmd_setup
from .core.config import SimpleConfig
from .core.state import SimpleStateManager
from .version import __version__


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        cmd_help()
        return

    command = sys.argv[1]

    # Handle version flag
    if command in ["--version", "-V", "version"]:
        print(f"spot-deployer {__version__}")
        return

    # Handle help command early to avoid config loading
    if command == "help":
        cmd_help()
        return

    # Check for verbose flag
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    # Use paths from environment variables if set (for Docker)
    config_path = os.environ.get("SPOT_CONFIG_PATH", "config.yaml")
    state_path = os.environ.get("SPOT_STATE_PATH", "instances.json")

    config = SimpleConfig(config_path)
    state = SimpleStateManager(state_path)

    if command == "setup":
        cmd_setup(config)
    elif command == "create":
        cmd_create(config, state)
    elif command == "list":
        cmd_list(state)
    elif command == "destroy":
        cmd_destroy(config, state, verbose=verbose)
    else:
        print(f"Unknown command: {command}")
        cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
