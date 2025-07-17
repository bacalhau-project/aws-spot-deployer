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
AWS Spot Instance Deployer - Modular Version

A simplified tool for deploying and managing AWS EC2 spot instances.
"""

if __name__ == "__main__":
    from spot_deployer.main import main
    main()