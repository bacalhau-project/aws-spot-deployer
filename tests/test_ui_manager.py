#!/usr/bin/env python3
"""Unit tests for UIManager."""

from unittest.mock import patch

from rich.layout import Layout
from rich.table import Table

from spot_deployer.utils.ui_manager import UIManager


class TestUIManager:
    """Test cases for UIManager."""

    def test_initialization(self):
        """Test manager initialization."""
        ui = UIManager()
        assert ui.console is not None

    def test_print_methods(self):
        """Test all print methods work correctly."""
        ui = UIManager()

        with patch.object(ui.console, "print") as mock_print:
            # Test success message
            ui.print_success("Operation completed")
            mock_print.assert_called_with("[green]✅ Operation completed[/green]")

            # Test error message
            ui.print_error("Operation failed")
            mock_print.assert_called_with("[red]❌ Operation failed[/red]")

            # Test warning message
            ui.print_warning("Be careful")
            mock_print.assert_called_with("[yellow]⚠️  Be careful[/yellow]")

            # Test info message
            ui.print_info("Processing")
            mock_print.assert_called_with("[blue]ℹ️  Processing[/blue]")

    def test_create_progress_panel(self):
        """Test progress panel creation."""
        ui = UIManager()

        content = {
            "Completed": 10,
            "Failed": 2,
            "In Progress": 5,
            "Elapsed": "30.5s",
        }

        panel = ui.create_progress_panel("Testing", content)
        assert panel is not None
        # Panel should be a Rich Panel object
        from rich.panel import Panel

        assert isinstance(panel, Panel)

    def test_create_live_display(self):
        """Test live display creation."""
        ui = UIManager()
        table = Table(title="Test Table")
        layout = Layout(table)

        with ui.start_live_display(layout) as live:
            assert live is not None
            # Should be able to update
            live.update(layout)
