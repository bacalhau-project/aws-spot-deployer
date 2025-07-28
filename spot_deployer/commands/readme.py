"""Readme command implementation."""

import os

from ..utils.display import console


def cmd_readme() -> None:
    """Display the README content for the files directory."""
    if console:
        # Determine if we're in Docker
        in_docker = os.path.exists("/.dockerenv")

        if in_docker:
            base_path = "$HOME/.spot-deployer"
        else:
            base_path = "~/.spot-deployer"

        console.print(f"""
[bold cyan]Spot Deployer Files Directory[/bold cyan]
==================================================

[bold]Overview:[/bold]
The files directory is where you place files to upload to your spot instances.
These files will be copied to /opt/uploaded_files/ on each instance during deployment.

[bold]Directory Structure:[/bold]
{base_path}/
├── config/
│   └── config.yaml              # Your deployment configuration
├── files/                       # Files to upload to instances
│   ├── orchestrator_endpoint    # NATS endpoint URL
│   └── orchestrator_token       # Authentication token
└── output/
    ├── instances.json           # Current deployment state
    └── deployment_*.log         # Deployment logs

[bold]Required Credential Files:[/bold]

[yellow]1. {base_path}/files/orchestrator_endpoint[/yellow]
   Contents: NATS endpoint URL for the Bacalhau orchestrator
   Example content:
   ```
   nats://orchestrator.example.com:4222
   ```

[yellow]2. {base_path}/files/orchestrator_token[/yellow]
   Contents: Authentication token for the orchestrator
   Example content:
   ```
   bac-your-secret-token-here
   ```

[bold]How It Works:[/bold]
1. Place your credential files in {base_path}/files/
2. Run 'spot-deployer create' to deploy instances
3. Files are automatically uploaded to /opt/uploaded_files/ on each instance
4. Bacalhau services read credentials and connect to the orchestrator

[bold]Security Best Practices:[/bold]
• Store credentials securely - never commit them to version control
• Set appropriate file permissions (600) on credential files
• Rotate tokens regularly according to your security policy
• The .gitignore already excludes orchestrator_endpoint and orchestrator_token

[bold]Troubleshooting:[/bold]
• If nodes don't connect, check {base_path}/output/deployment_*.log
• Verify credential files exist and contain valid data
• Ensure the orchestrator endpoint is reachable from AWS regions""")
