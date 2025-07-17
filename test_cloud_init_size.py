#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
#     "rich",
#     "boto3",
# ]
# ///

"""Test cloud-init size to ensure it's within AWS limits."""

import os
import sys
from deploy_spot import SimpleConfig, generate_full_cloud_init
from rich.console import Console
from rich.table import Table

console = Console()

# AWS user data size limit
AWS_USER_DATA_LIMIT = 16384  # 16KB base64 encoded
AWS_USER_DATA_RAW_LIMIT = 16384 * 3 / 4  # ~12KB raw data

def main():
    """Check cloud-init size."""
    # Load config
    config = SimpleConfig("config.yaml")
    
    # Generate cloud-init
    console.print("Generating cloud-init user data...", style="bold blue")
    user_data = generate_full_cloud_init(config)
    
    # Calculate sizes
    raw_size = len(user_data.encode('utf-8'))
    base64_size = len(user_data.encode('utf-8')) * 4 / 3  # Approximate base64 size
    
    # Create results table
    table = Table(title="Cloud-Init Size Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Status", style="yellow")
    
    # Raw size
    raw_status = "✅ OK" if raw_size < AWS_USER_DATA_RAW_LIMIT else "❌ TOO LARGE"
    table.add_row(
        "Raw Size", 
        f"{raw_size:,} bytes ({raw_size/1024:.1f} KB)",
        raw_status
    )
    
    # Base64 size
    base64_status = "✅ OK" if base64_size < AWS_USER_DATA_LIMIT else "❌ TOO LARGE"
    table.add_row(
        "Base64 Size (approx)", 
        f"{int(base64_size):,} bytes ({base64_size/1024:.1f} KB)",
        base64_status
    )
    
    # Limits
    table.add_row(
        "AWS Limit (base64)", 
        f"{AWS_USER_DATA_LIMIT:,} bytes ({AWS_USER_DATA_LIMIT/1024:.1f} KB)",
        "—"
    )
    
    # Usage percentage
    usage_pct = (base64_size / AWS_USER_DATA_LIMIT) * 100
    usage_status = "✅ Good" if usage_pct < 80 else "⚠️  High" if usage_pct < 100 else "❌ Over"
    table.add_row(
        "Usage", 
        f"{usage_pct:.1f}%",
        usage_status
    )
    
    console.print(table)
    
    # Show breakdown by file type
    console.print("\n[bold]File Breakdown:[/bold]")
    
    # Count different sections
    script_count = user_data.count('- path: /opt/uploaded_files/scripts/')
    config_count = user_data.count('- path: /opt/uploaded_files/config/')
    service_count = user_data.count('- path: /etc/systemd/system/')
    
    console.print(f"  Scripts: {script_count} files")
    console.print(f"  Configs: {config_count} files")
    console.print(f"  Services: {service_count} files")
    
    # Warning if close to limit
    if usage_pct > 80:
        console.print("\n[bold yellow]⚠️  WARNING: Cloud-init is using >80% of AWS limit![/bold yellow]")
        console.print("Consider reducing embedded files or using S3/HTTP for larger files.")
    
    # Critical if over limit
    if base64_size > AWS_USER_DATA_LIMIT:
        console.print("\n[bold red]❌ ERROR: Cloud-init exceeds AWS user data limit![/bold red]")
        console.print("Deployment will fail. You must reduce the size.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())