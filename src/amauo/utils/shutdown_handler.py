"""Graceful shutdown handler for spot deployer operations."""

import signal
import sys
import threading
from typing import Callable, List, Optional

from ..utils.ui_manager import UIManager


class ShutdownHandler:
    """Handles graceful shutdown on SIGTERM/SIGINT signals."""

    def __init__(self):
        """Initialize the shutdown handler."""
        self.ui = UIManager()
        self._shutdown_requested = False
        self._cleanup_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._original_sigint = None
        self._original_sigterm = None

    def register(self) -> None:
        """Register signal handlers for graceful shutdown."""
        self._original_sigint = signal.signal(signal.SIGINT, self._handle_shutdown)
        self._original_sigterm = signal.signal(signal.SIGTERM, self._handle_shutdown)

    def unregister(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigint is not None:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm)

    def add_cleanup_callback(self, callback: Callable) -> None:
        """Add a cleanup callback to be called on shutdown."""
        with self._lock:
            self._cleanup_callbacks.append(callback)

    def remove_cleanup_callback(self, callback: Callable) -> None:
        """Remove a cleanup callback."""
        with self._lock:
            if callback in self._cleanup_callbacks:
                self._cleanup_callbacks.remove(callback)

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        if self._shutdown_requested:
            # Force exit on second signal
            self.ui.print_error("\nForced shutdown!")
            sys.exit(1)

        self._shutdown_requested = True
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"

        self.ui.console.print(
            f"\n[yellow]Received {signal_name}, initiating graceful shutdown...[/yellow]"
        )
        self.ui.console.print("[dim]Press Ctrl+C again to force shutdown[/dim]")

        # Run cleanup callbacks
        with self._lock:
            callbacks = self._cleanup_callbacks.copy()

        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                self.ui.print_error(f"Error in cleanup callback: {e}")

        # Restore original handlers
        self.unregister()


class ShutdownContext:
    """Context manager for graceful shutdown handling."""

    def __init__(self, cleanup_message: Optional[str] = None):
        """
        Initialize shutdown context.

        Args:
            cleanup_message: Optional message to display during cleanup
        """
        self.handler = ShutdownHandler()
        self.cleanup_message = cleanup_message
        self._cleanup_functions: List[Callable] = []

    def add_cleanup(self, func: Callable) -> None:
        """Add a cleanup function to be called on shutdown."""
        self._cleanup_functions.append(func)

    def __enter__(self):
        """Enter the context and register signal handlers."""
        self.handler.register()

        def cleanup():
            if self.cleanup_message:
                self.handler.ui.print_warning(self.cleanup_message)

            for func in self._cleanup_functions:
                try:
                    func()
                except Exception as e:
                    self.handler.ui.print_error(f"Cleanup error: {e}")

        self.handler.add_cleanup_callback(cleanup)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and unregister signal handlers."""
        self.handler.unregister()
        return False

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.handler.is_shutdown_requested()


def handle_shutdown_in_operation(operation_name: str, cleanup_func: Optional[Callable] = None):
    """
    Decorator to add shutdown handling to long-running operations.

    Args:
        operation_name: Name of the operation for logging
        cleanup_func: Optional cleanup function to call on shutdown
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            with ShutdownContext(f"Cleaning up {operation_name}...") as ctx:
                if cleanup_func:
                    ctx.add_cleanup(cleanup_func)

                # Pass shutdown context to the function if it accepts it
                import inspect

                sig = inspect.signature(func)
                if "shutdown_context" in sig.parameters:
                    kwargs["shutdown_context"] = ctx

                return func(*args, **kwargs)

        return wrapper

    return decorator
