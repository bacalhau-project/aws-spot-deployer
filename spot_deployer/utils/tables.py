"""Shared table utilities for spot deployer commands."""

from typing import Optional

from rich.table import Table


def create_instance_table(
    title: str,
    show_header: bool = True,
    expand: bool = True,
    show_lines: bool = False,
    padding: tuple = (0, 1),
    header_style: Optional[str] = None,
) -> Table:
    """Create a standardized instance table with common columns."""
    table = Table(
        title=title,
        show_header=show_header,
        expand=expand,
        show_lines=show_lines,
        padding=padding,
        header_style=header_style,
    )

    # Add standard columns - let Rich determine optimal widths
    table.add_column("Region", style="magenta", no_wrap=True)
    table.add_column("Instance ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="yellow", no_wrap=True)
    table.add_column("Type", style="green", no_wrap=True)
    table.add_column("Public IP", style="blue", no_wrap=True)
    table.add_column("Created", style="dim", no_wrap=True)

    return table


def add_instance_row(
    table: Table,
    region: str,
    instance_id: str,
    status: str,
    instance_type: str,
    public_ip: str,
    created: str,
) -> None:
    """Add a row to an instance table with proper string conversion."""
    table.add_row(
        str(region),
        str(instance_id),
        str(status),
        str(instance_type),
        str(public_ip),
        str(created),
    )


def add_destroy_row(
    table: Table,
    region: str,
    instance_id: str,
    status: str,
    details: str,
) -> None:
    """Add a row to a destroy table with proper string conversion."""
    table.add_row(
        str(region),
        str(instance_id),
        str(status),
        "",  # Type column (empty for destroy)
        "",  # Public IP column (empty for destroy)
        "",  # Created column (empty for destroy)
    )
