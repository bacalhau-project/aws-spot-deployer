#!/usr/bin/env python3
"""
UI Display Module

This module handles all rich-based UI components including:
- Progress tables
- Live status updates
- Layout management
- Progress bars
"""

import asyncio
import logging
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TaskID
from rich.table import Table

from core.status_manager import format_elapsed_time, status_manager

logger = logging.getLogger(__name__)

# Global console instance
console = Console()

# Global progress tracking
task_name = "TASK NAME"
task_total = 10000
task_count = 0
events_to_progress = []
events_to_progress_lock = asyncio.Lock()

# Table update control
table_update_running = False
table_update_event = asyncio.Event()


def make_progress_table() -> Table:
    """Create the main progress table showing instance statuses."""
    table = Table(title="Instance Creation Progress")
    table.add_column("Region", style="cyan", no_wrap=True)
    table.add_column("Instance ID", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Public IP", style="blue")
    table.add_column("Private IP", style="white")
    table.add_column("Elapsed", style="red")
    table.add_column("Error", style="bright_red")

    # Get all statuses from status manager
    all_statuses = status_manager.get_all_statuses()

    # Sort by region, then by instance ID
    sorted_items = sorted(
        all_statuses.items(), key=lambda x: (x[1]["region"], x[1]["instance_id"])
    )

    for key, status_data in sorted_items:
        # Format status with appropriate styling
        status = status_data["status"]
        if status == "running":
            status_display = "[green]running[/green]"
        elif status == "pending":
            status_display = "[yellow]pending[/yellow]"
        elif status in ["terminated", "stopped"]:
            status_display = "[red]terminated[/red]"
        elif "error" in status.lower() or "failed" in status.lower():
            status_display = f"[red]{status}[/red]"
        else:
            status_display = status

        # Format elapsed time
        elapsed_display = format_elapsed_time(status_data["elapsed_seconds"])

        # Format error message (truncate if too long)
        error_msg = status_data.get("error_message", "")
        if len(error_msg) > 50:
            error_msg = error_msg[:47] + "..."

        table.add_row(
            status_data["region"],
            status_data["instance_id"][:12]
            if status_data["instance_id"]
            else "",  # Truncate long IDs
            status_data["instance_type"],
            status_display,
            status_data["public_ip"],
            status_data["private_ip"],
            elapsed_display,
            error_msg,
        )

    return table


def make_operations_log_panel() -> Panel:
    """Create the operations log panel."""
    logs = status_manager.get_operations_logs()

    if not logs:
        log_content = "[dim]No operations logged yet...[/dim]"
    else:
        # Show last 10 logs
        log_content = "\n".join(logs[-10:])

    return Panel(log_content, title="Recent Operations", border_style="blue", height=12)


def make_summary_panel() -> Panel:
    """Create the summary statistics panel."""
    summary = status_manager.get_summary()

    summary_text = f"""
[green]Running:[/green] {summary["running"]}
[yellow]Pending:[/yellow] {summary["pending"]}
[blue]Completed:[/blue] {summary["done"]}
[red]Failed:[/red] {summary["failed"]}
[white]Total:[/white] {summary["total"]}
"""

    return Panel(summary_text.strip(), title="Summary", border_style="green", width=25)


def create_layout(progress: Progress, table: Table) -> Layout:
    """Create the main layout for the live display."""
    layout = Layout()

    # Split into top and bottom
    layout.split_column(Layout(name="top", size=3), Layout(name="main"))

    # Top section for progress bars
    layout["top"].update(Panel(progress, title="Progress", border_style="green"))

    # Main section split between table and logs
    layout["main"].split_row(
        Layout(name="table", ratio=3), Layout(name="sidebar", ratio=1)
    )

    # Table section
    layout["table"].update(Panel(table, title="Instances", border_style="cyan"))

    # Sidebar split between summary and logs
    layout["sidebar"].split_column(
        Layout(make_summary_panel(), name="summary", size=8),
        Layout(make_operations_log_panel(), name="logs"),
    )

    return layout


async def update_table(live: Live):
    """Continuously update the live table display."""
    global table_update_running, table_update_event

    table_update_running = True

    try:
        # Create progress bar
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("{task.completed}/{task.total}"),
        )

        # Add main task
        main_task = progress.add_task(task_name, total=task_total)

        while table_update_running:
            try:
                # Update progress bar
                progress.update(main_task, completed=task_count, description=task_name)

                # Process any pending progress events
                async with events_to_progress_lock:
                    for event in events_to_progress:
                        if event["action"] == "add_task":
                            event["task_id"] = progress.add_task(
                                event["description"], total=event.get("total", 100)
                            )
                        elif event["action"] == "update_task":
                            progress.update(
                                event["task_id"],
                                completed=event.get("completed", 0),
                                description=event.get("description", ""),
                            )
                        elif event["action"] == "remove_task":
                            progress.remove_task(event["task_id"])

                    events_to_progress.clear()

                # Create new table
                table = make_progress_table()

                # Create layout
                layout = create_layout(progress, table)

                # Update the live display
                live.update(layout)

                # Wait for next update
                try:
                    await asyncio.wait_for(table_update_event.wait(), timeout=2.0)
                    table_update_event.clear()
                except asyncio.TimeoutError:
                    # Regular update every 2 seconds
                    pass

            except Exception as e:
                logger.error(f"Error updating table: {e}")
                await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error in update_table: {e}")
    finally:
        table_update_running = False


def trigger_table_update():
    """Trigger an immediate table update."""
    if table_update_event:
        table_update_event.set()


async def add_progress_task(description: str, total: int = 100) -> TaskID:
    """Add a new progress task."""
    event = {"action": "add_task", "description": description, "total": total}

    async with events_to_progress_lock:
        events_to_progress.append(event)

    trigger_table_update()

    # Wait for the task to be created
    await asyncio.sleep(0.1)

    # Return the task ID (this is a simplified approach)
    return len(events_to_progress) - 1


async def update_progress_task(
    task_id: TaskID, completed: int, description: Optional[str] = None
):
    """Update a progress task."""
    event = {"action": "update_task", "task_id": task_id, "completed": completed}

    if description:
        event["description"] = description

    async with events_to_progress_lock:
        events_to_progress.append(event)

    trigger_table_update()


async def remove_progress_task(task_id: TaskID):
    """Remove a progress task."""
    event = {"action": "remove_task", "task_id": task_id}

    async with events_to_progress_lock:
        events_to_progress.append(event)

    trigger_table_update()


def set_main_task(name: str, total: int, current: int = 0):
    """Set the main task progress."""
    global task_name, task_total, task_count
    task_name = name
    task_total = total
    task_count = current
    trigger_table_update()


def update_main_task(current: int, name: Optional[str] = None):
    """Update the main task progress."""
    global task_name, task_count
    task_count = current
    if name:
        task_name = name
    trigger_table_update()


def stop_table_updates():
    """Stop the table update loop."""
    global table_update_running
    table_update_running = False
    trigger_table_update()


class LiveDisplay:
    """Context manager for live display."""

    def __init__(self):
        self.live = None
        self.update_task = None

    async def __aenter__(self):
        """Start the live display."""
        # Create initial table
        table = make_progress_table()
        progress = Progress()
        layout = create_layout(progress, table)

        # Start live display
        self.live = Live(layout, console=console, refresh_per_second=2)
        self.live.start()

        # Start update task
        self.update_task = asyncio.create_task(update_table(self.live))

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop the live display."""
        # Stop the update task
        stop_table_updates()

        if self.update_task:
            try:
                await asyncio.wait_for(self.update_task, timeout=2.0)
            except asyncio.TimeoutError:
                self.update_task.cancel()

        # Stop live display
        if self.live:
            self.live.stop()


# Convenience functions for backward compatibility
def print_status_table():
    """Print the current status table (non-live version)."""
    table = make_progress_table()
    console.print(table)


def print_summary():
    """Print the summary panel."""
    summary_panel = make_summary_panel()
    console.print(summary_panel)


def print_operations_log():
    """Print the operations log panel."""
    log_panel = make_operations_log_panel()
    console.print(log_panel)
