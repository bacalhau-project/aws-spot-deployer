#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "boto3>=1.26.0",
#   "rich>=13.0.0",
# ]
# ///

"""
Check for default VPCs across all AWS regions.
Helps identify which regions have default VPCs and which need configuration.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from rich.consoleemer_console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def get_all_regions():
    """Get all available AWS regions."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    response = ec2.describe_regions(AllRegions=True)
    return sorted([region["RegionName"] for region in response["Regions"]])


def check_default_vpc(region):
    """Check if a region has a default VPC."""
    try:
        ec2 = boto3.client("ec2", region_name=region)

        # Check for default VPC
        response = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])

        vpcs = response.get("Vpcs", [])

        if vpcs:
            vpc = vpcs[0]
            vpc_id = vpc["VpcId"]
            cidr = vpc["CidrBlock"]

            # Get subnet count
            subnet_response = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
            subnet_count = len(subnet_response.get("Subnets", []))

            # Get availability zones
            azs = set()
            for subnet in subnet_response.get("Subnets", []):
                azs.add(subnet["AvailabilityZone"])

            return {
                "region": region,
                "has_default": True,
                "vpc_id": vpc_id,
                "cidr": cidr,
                "subnet_count": subnet_count,
                "availability_zones": len(azs),
                "status": "✅ Default VPC exists",
                "error": None,
            }
        else:
            # No default VPC, check if region has any VPCs
            all_vpcs = ec2.describe_vpcs()
            vpc_count = len(all_vpcs.get("Vpcs", []))

            return {
                "region": region,
                "has_default": False,
                "vpc_id": None,
                "cidr": None,
                "subnet_count": 0,
                "availability_zones": 0,
                "status": f"❌ No default VPC ({vpc_count} custom VPCs)",
                "error": None,
            }

    except Exception as e:
        error_msg = str(e)
        if "UnauthorizedOperation" in error_msg:
            status = "⚠️  No access"
        elif "InvalidRegion" in error_msg:
            status = "⚠️  Invalid region"
        else:
            status = "⚠️  Error"

        return {
            "region": region,
            "has_default": False,
            "vpc_id": None,
            "cidr": None,
            "subnet_count": 0,
            "availability_zones": 0,
            "status": status,
            "error": error_msg,
        }


def main():
    """Main function to check all regions."""
    console.print("\n[bold cyan]AWS Default VPC Scanner[/bold cyan]")
    console.print("Checking all AWS regions for default VPCs...\n")

    # Get all regions
    try:
        regions = get_all_regions()
        console.print(f"Found [bold]{len(regions)}[/bold] AWS regions to check\n")
    except Exception as e:
        console.print(f"[bold red]Error getting regions: {e}[/bold red]")
        return

    # Check each region in parallel
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning regions...", total=len(regions))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_default_vpc, region): region for region in regions}

            for future in as_completed(futures):
                region = futures[future]
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception as e:
                    results.append(
                        {
                            "region": region,
                            "has_default": False,
                            "vpc_id": None,
                            "cidr": None,
                            "subnet_count": 0,
                            "availability_zones": 0,
                            "status": "⚠️  Timeout/Error",
                            "error": str(e),
                        }
                    )
                progress.update(task, advance=1)

    # Sort results
    results.sort(key=lambda x: (not x["has_default"], x["region"]))

    # Create summary tables
    console.print("\n[bold]Summary[/bold]\n")

    # Stats
    with_default = [r for r in results if r["has_default"]]
    without_default = [r for r in results if not r["has_default"] and not r["error"]]
    with_errors = [r for r in results if r["error"]]

    stats_table = Table(show_header=False, box=None)
    stats_table.add_row("✅ Regions with default VPC:", f"[green]{len(with_default)}[/green]")
    stats_table.add_row("❌ Regions without default VPC:", f"[red]{len(without_default)}[/red]")
    stats_table.add_row("⚠️  Regions with errors:", f"[yellow]{len(with_errors)}[/yellow]")
    stats_table.add_row("[bold]Total regions checked:[/bold]", f"[bold]{len(results)}[/bold]")
    console.print(stats_table)

    # Detailed table
    console.print("\n[bold]Detailed Results[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Region", style="cyan", width=20)
    table.add_column("Status", width=30)
    table.add_column("VPC ID", style="dim", width=25)
    table.add_column("CIDR Block", style="dim", width=18)
    table.add_column("Subnets", justify="center", width=8)
    table.add_column("AZs", justify="center", width=5)

    for result in results:
        style = "green" if result["has_default"] else "red" if not result["error"] else "yellow"
        table.add_row(
            result["region"],
            result["status"],
            result["vpc_id"] or "-",
            result["cidr"] or "-",
            str(result["subnet_count"]) if result["subnet_count"] > 0 else "-",
            str(result["availability_zones"]) if result["availability_zones"] > 0 else "-",
            style=style,
        )

    console.print(table)

    # Recommendations
    if without_default:
        console.print("\n[bold yellow]⚠️  Recommendations[/bold yellow]")
        console.print("\nRegions without default VPCs:")
        for region in without_default:
            console.print(f"  • {region['region']}")

        console.print("\n[bold]To create default VPCs:[/bold]")
        for region in without_default[:3]:  # Show first 3 as examples
            console.print(f"  aws ec2 create-default-vpc --region {region['region']}")
        if len(without_default) > 3:
            console.print(f"  ... and {len(without_default) - 3} more regions")

        console.print("\n[bold]Or use dedicated VPCs in config.yaml:[/bold]")
        console.print("  aws:")
        console.print("    use_dedicated_vpc: true")

    # Good regions for deployment
    console.print("\n[bold green]✅ Best Regions for Deployment[/bold green]")
    console.print("(Have default VPCs and good spot capacity):\n")

    preferred_regions = [
        "us-west-2",
        "us-east-2",
        "eu-central-1",
        "ap-southeast-1",
        "eu-west-2",
        "ap-northeast-1",
        "us-west-1",
        "ca-central-1",
    ]

    available_preferred = [
        r for r in results if r["region"] in preferred_regions and r["has_default"]
    ]

    for region in available_preferred[:6]:
        console.print(f"  • {region['region']:<15} - {region['vpc_id']}")

    # Export option
    console.print("\n[dim]To export results to JSON, run with:[/dim]")
    console.print("[dim]  python check-default-vpcs.py > vpc-report.json[/dim]")


if __name__ == "__main__":
    main()
