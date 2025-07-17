"""Display utilities for rich terminal output."""

# Try to import Rich components
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table
    
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


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


def create_progress_bar(description: str, total: int = 100) -> Progress:
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