#!/usr/bin/env python3
"""
AWS Spot Instance Deployer - Main Entry Point

This tool deploys and manages AWS EC2 spot instances with a focus on simplicity.
"""
import sys

from .core.config import SimpleConfig
from .core.state import SimpleStateManager
from .commands import cmd_create, cmd_destroy, cmd_list, cmd_setup, cmd_help


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        cmd_help()
        return
    
    command = sys.argv[1]
    config = SimpleConfig()
    state = SimpleStateManager()
    
    if command == "setup":
        cmd_setup(config)
    elif command == "create":
        cmd_create(config, state)
    elif command == "list":
        cmd_list(state)
    elif command == "destroy":
        cmd_destroy(config, state)
    elif command == "help":
        cmd_help()
    else:
        print(f"Unknown command: {command}")
        cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()