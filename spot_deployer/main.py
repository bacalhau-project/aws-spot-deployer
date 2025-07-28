#!/usr/bin/env uv run
"""
AWS Spot Instance Deployer - Main Entry Point

This tool deploys and manages AWS EC2 spot instances with a focus on simplicity.
"""

import argparse
import os
import sys

from .commands import cmd_create, cmd_destroy, cmd_help, cmd_list, cmd_nuke, cmd_readme, cmd_setup
from .core.config import SimpleConfig
from .core.constants import DEFAULT_CONFIG_FILE, DEFAULT_FILES_DIR, DEFAULT_OUTPUT_DIR
from .core.state import SimpleStateManager
from .version import __version__


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AWS Spot Instance Deployer",
        add_help=False,  # We handle help ourselves
    )

    # Add command as first positional argument
    parser.add_argument("command", nargs="?", help="Command to run")

    # Add optional flags
    parser.add_argument("--config", "-c", help="Path to config file")
    parser.add_argument("--files", "-f", help="Path to files directory")
    parser.add_argument("--output", "-o", help="Path to output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--version", "-V", action="store_true", help="Show version")

    # Parse known args to allow command-specific args to pass through
    args, remaining = parser.parse_known_args()

    # Handle version flag
    if args.version or args.command == "version":
        print(f"spot-deployer {__version__}")
        return

    # Handle missing command
    if not args.command:
        cmd_help()
        return

    # Handle help command
    if args.command == "help":
        cmd_help()
        return

    # Determine paths with priority: CLI flag > env var > default
    config_path = (
        args.config
        or os.environ.get("SPOT_CONFIG_PATH")
        or os.environ.get("SPOT_CONFIG", DEFAULT_CONFIG_FILE)
    )

    files_dir = (
        args.files
        or os.environ.get("SPOT_FILES_DIR")
        or os.environ.get("SPOT_FILES", DEFAULT_FILES_DIR)
    )

    output_dir = (
        args.output
        or os.environ.get("SPOT_OUTPUT_DIR")
        or os.environ.get("SPOT_OUTPUT", DEFAULT_OUTPUT_DIR)
    )

    # For backwards compatibility with Docker
    state_path = os.environ.get("SPOT_STATE_PATH")
    if not state_path:
        state_path = os.path.join(output_dir, "instances.json")

    # Set environment variables for child processes
    os.environ["SPOT_CONFIG_PATH"] = config_path
    os.environ["SPOT_FILES_DIR"] = files_dir
    os.environ["SPOT_OUTPUT_DIR"] = output_dir

    config = SimpleConfig(config_path, files_dir=files_dir, output_dir=output_dir)
    state = SimpleStateManager(state_path)

    if args.command == "setup":
        cmd_setup(config)
    elif args.command == "create":
        cmd_create(config, state)
    elif args.command == "list":
        cmd_list(state)
    elif args.command == "destroy":
        cmd_destroy(config, state, verbose=args.verbose)
    elif args.command == "nuke":
        # Check for --force flag in remaining args
        force = "--force" in remaining or "-f" in remaining
        cmd_nuke(state, config, force=force)
    elif args.command == "readme":
        cmd_readme()
    else:
        print(f"Unknown command: {args.command}")
        cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
