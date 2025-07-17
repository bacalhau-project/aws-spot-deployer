#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "boto3>=1.26.0",
#     "pyyaml>=6.0",
#     "rich>=13.0.0",
# ]
# ///
"""
AWS Spot Instance Deployer

A simplified tool for deploying and managing AWS EC2 spot instances.
This is now a wrapper around the modularized code in the spot_deployer package.

Original functionality has been preserved and organized into:
- spot_deployer/commands/ - Command implementations (create, destroy, list, setup, help)
- spot_deployer/core/ - Core business logic (config, state, constants, instance management)
- spot_deployer/utils/ - Utilities (display, aws, logging, ssh, cloud_init)

Usage:
    ./deploy_spot.py setup      # Create config.yaml
    ./deploy_spot.py create     # Deploy instances
    ./deploy_spot.py list       # List instances
    ./deploy_spot.py destroy    # Terminate instances
    ./deploy_spot.py help       # Show help
"""

if __name__ == "__main__":
    from spot_deployer.main import main
    main()