"""Display utilities for rich terminal output."""

# Try to import Rich components
try:
    from rich.console import Console
    from rich.layout import Layout  # noqa: F401 - Re-exported for other modules
    from rich.live import Live  # noqa: F401 - Re-exported for other modules
    from rich.panel import Panel  # noqa: F401 - Re-exported for other modules
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table  # noqa: F401 - Re-exported for other modules
    import os

    RICH_AVAILABLE = True
    # Configure console for better Docker compatibility
    console = Console(
        force_terminal=True,
        force_interactive=True,
        width=120 if os.environ.get("TERM") else None,
        legacy_windows=False,
        color_system="auto"
    )
except ImportError:
    RICH_AVAILABLE = False
    console = None
    # Define placeholders for type hints when Rich is not available
    Layout = None
    Live = None
    Panel = None
    Table = None


def rich_print(message: str, style: str = None) -> None:
    """Print with Rich styling if available, fallback to regular print."""
    if RICH_AVAILABLE and console:
        if style:
            console.print(f"[{style}]{message}[/{style}]")
        else:
            console.print(message)
    else:
        print(message)


def rich_status(message: str) -> None:
    """Print status message with Rich styling."""
    rich_print(f"ℹ️  {message}", "blue")


def rich_success(message: str) -> None:
    """Print success message with Rich styling."""
    rich_print(f"✅ {message}", "green")


def rich_error(message: str) -> None:
    """Print error message with Rich styling."""
    rich_print(f"❌ {message}", "red")


def rich_warning(message: str) -> None:
    """Print warning message with Rich styling."""
    rich_print(f"⚠️  {message}", "yellow")


def create_progress_bar(description: str, total: int = 100):
    """Create a Rich progress bar."""
    if not RICH_AVAILABLE:
        return None

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="green", finished_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )

    task = progress.add_task(description, total=total)
    return progress, task
