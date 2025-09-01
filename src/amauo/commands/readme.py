"""Readme command implementation."""

from ..utils.display import console


def cmd_readme() -> None:
    """Display the README content for the files directory."""
    if console:
        console.print("""
[bold cyan]Spot Deployer Files Directory[/bold cyan]
==================================================

[bold]Overview:[/bold]
The files directory is where you place files to upload to your spot instances.
These files will be deployed directly to their target locations on each instance (e.g., /etc/bacalhau/, /opt/compose/).

[bold]Directory Structure (in current directory):[/bold]
./
├── config.yaml                  # Your deployment configuration
├── files/                       # Files to upload to instances
│   ├── orchestrator_endpoint    # NATS endpoint URL
│   └── orchestrator_token       # Authentication token
└── output/
    ├── instances.json           # Current deployment state
    └── deployment_*.log         # Deployment logs

[bold]Required Credential Files:[/bold]

[yellow]1. ./files/orchestrator_endpoint[/yellow]
   Contents: Endpoint URL for the orchestrator
   Example content:
   ```
   nats://orchestrator.example.com:4222
   ```

[yellow]2. ./files/orchestrator_token[/yellow]
   Contents: Authentication token for the orchestrator
   Example content:
   ```
   bac-your-secret-token-here
   ```

[bold]How It Works:[/bold]
1. Place your credential files in ./files/
2. Run 'spot-deployer create' to deploy instances
3. Files are automatically uploaded to /opt/uploaded_files/ on each instance
4. Services read credentials and connect to the orchestrator

[bold]Security Best Practices:[/bold]
• Store credentials securely - never commit them to version control
• Set appropriate file permissions (600) on credential files
• Rotate tokens regularly according to your security policy
• The .gitignore already excludes orchestrator_endpoint and orchestrator_token

[bold]Troubleshooting:[/bold]
• If nodes don't connect, check ./output/deployment_*.log
• Verify credential files exist and contain valid data
• Ensure the orchestrator endpoint is reachable from AWS regions""")
