"""Display utilities for rich terminal output."""

from typing import Any, Optional

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

    RICH_AVAILABLE = True
    # Force Rich to use full width regardless of terminal detection
    import os
    import sys

    # Clear any environment variables that might affect width detection
    os.environ.pop("COLUMNS", None)
    os.environ.pop("LINES", None)

    console = Console(
        force_terminal=True,
        force_interactive=True,
        legacy_windows=False,
        color_system="auto",
        width=140,  # Fixed width of 140 as requested
        # Remove height constraint to allow full display
        file=sys.stdout,
        _environ={},  # Empty environment to avoid detection
    )
except ImportError:
    RICH_AVAILABLE = False
    console = None  # type: ignore
    # Define placeholders for type hints when Rich is not available
    Layout = None  # type: ignore
    Live = None  # type: ignore
    Panel = None  # type: ignore
    Table = None  # type: ignore


def rich_print(message: str, style: Optional[str] = None) -> None:
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
    if RICH_AVAILABLE:
        from .ui_manager import UIManager

        UIManager().print_info(message)
    else:
        print(f"ℹ️  {message}")


def rich_success(message: str) -> None:
    """Print success message with Rich styling."""
    if RICH_AVAILABLE:
        from .ui_manager import UIManager

        UIManager().print_success(message)
    else:
        print(f"✅ {message}")


def rich_error(message: str) -> None:
    """Print error message with Rich styling."""
    if RICH_AVAILABLE:
        from .ui_manager import UIManager

        UIManager().print_error(message)
    else:
        print(f"❌ {message}")


def rich_warning(message: str) -> None:
    """Print warning message with Rich styling."""
    if RICH_AVAILABLE:
        from .ui_manager import UIManager

        UIManager().print_warning(message)
    else:
        print(f"⚠️  {message}")


def create_progress_bar(description: str, total: int = 100) -> Any:
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
