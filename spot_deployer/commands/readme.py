"""Readme command implementation."""

from ..utils.display import console


def cmd_readme() -> None:
    """Display the README content for the files directory."""
    if console:
        console.print("""
[bold cyan]Spot Deployer Files Directory[/bold cyan]
==================================================

[bold]Overview:[/bold]
Place files here that you want to upload to your spot instances.
These files will be copied to /opt/uploaded_files/ on each instance.

[bold]Required files for Bacalhau compute nodes:[/bold]
• orchestrator_endpoint: Contains the NATS endpoint URL
  Example: nats://orchestrator.example.com:4222
• orchestrator_token: Contains the authentication token
  Example: your-secret-token-here

[bold]Directory Structure:[/bold]
~/.spot-deployer/
├── config/
│   └── config.yaml      # Your deployment configuration
├── files/               # Files to upload to instances
│   ├── orchestrator_endpoint
│   └── orchestrator_token
└── output/
    └── instances.json  # Current deployment state

[bold]Security Notes:[/bold]
• Never commit credential files to version control
• These files should be listed in .gitignore
• Keep your tokens secure and rotate them regularly""")
