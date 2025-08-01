#!/usr/bin/env python3
"""Unit tests for UIManager."""

from unittest.mock import MagicMock, patch

from rich.layout import Layout
from rich.table import Table

from spot_deployer.utils.ui_manager import UIManager


class TestUIManager:
    """Test cases for UIManager."""

    def test_initialization(self):
        """Test UIManager initialization."""
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
            mock_print.assert_called_with("[cyan]ℹ️  Processing[/cyan]")

    def test_create_progress_bar(self):
        """Test progress bar creation."""
        ui = UIManager()

        with ui.create_progress_bar("Testing", total=100) as progress:
            assert progress is not None
            # Progress context manager should work
            task = progress.add_task("Test task", total=100)
            progress.update(task, advance=50)

    def test_create_live_display(self):
        """Test live display creation."""
        ui = UIManager()
        table = Table(title="Test Table")
        layout = Layout(table)

        with ui.create_live_display(layout) as live:
            assert live is not None
            # Should be able to update
            live.update(layout)

    def test_create_confirm_prompt(self):
        """Test confirmation prompt."""
        ui = UIManager()

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = True
            result = ui.create_confirm_prompt("Continue?")
            assert result is True
            mock_ask.assert_called_once_with("[yellow]Continue?[/yellow]", default=False)

            mock_ask.return_value = False
            result = ui.create_confirm_prompt("Delete?", default=True)
            assert result is False
            mock_ask.assert_called_with("[yellow]Delete?[/yellow]", default=True)

    def test_print_table(self):
        """Test table printing."""
        ui = UIManager()

        table = Table(title="Test")
        table.add_column("Col1")
        table.add_row("Data1")

        with patch.object(ui.console, "print") as mock_print:
            ui.print_table(table)
            mock_print.assert_called_once_with(table)

    def test_clear_screen(self):
        """Test screen clearing."""
        ui = UIManager()

        with patch.object(ui.console, "clear") as mock_clear:
            ui.clear_screen()
            mock_clear.assert_called_once()

    def test_print_json(self):
        """Test JSON printing."""
        ui = UIManager()

        data = {"key": "value", "number": 42}

        with patch.object(ui.console, "print_json") as mock_print_json:
            ui.print_json(data)
            mock_print_json.assert_called_once_with(data=data, indent=2)

            ui.print_json(data, indent=4)
            mock_print_json.assert_called_with(data=data, indent=4)

    def test_print_separator(self):
        """Test separator printing."""
        ui = UIManager()

        with patch.object(ui.console, "rule") as mock_rule:
            ui.print_separator()
            mock_rule.assert_called_once_with()

            ui.print_separator("Section Title")
            mock_rule.assert_called_with("Section Title")

    def test_get_console_size(self):
        """Test getting console dimensions."""
        ui = UIManager()

        # Mock console size
        ui.console.width = 120
        ui.console.height = 40

        width, height = ui.get_console_size()
        assert width == 120
        assert height == 40

    def test_print_panel(self):
        """Test panel printing."""
        ui = UIManager()

        with patch.object(ui.console, "print") as mock_print:
            ui.print_panel("Panel content", title="Test Panel")

            # Should have created and printed a panel
            assert mock_print.called
            call_args = mock_print.call_args[0][0]
            # Check that it's a Panel (we can't easily check the exact type due to imports)
            assert hasattr(call_args, "title")

    def test_measure_text(self):
        """Test text measurement."""
        ui = UIManager()

        # Simple test - just ensure method exists and returns something
        width = ui.measure_text("Test string")
        assert isinstance(width, int)
        assert width > 0

    def test_print_status(self):
        """Test status printing."""
        ui = UIManager()

        with patch.object(ui.console, "status") as mock_status:
            mock_context = MagicMock()
            mock_status.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_status.return_value.__exit__ = MagicMock(return_value=None)

            with ui.print_status("Processing...") as status:
                assert status == mock_context

            mock_status.assert_called_once_with("Processing...", spinner="dots")

    def test_print_exception(self):
        """Test exception printing."""
        ui = UIManager()

        with patch.object(ui.console, "print_exception") as mock_print_exc:
            try:
                raise ValueError("Test error")
            except ValueError:
                ui.print_exception()

            mock_print_exc.assert_called_once()

    def test_input(self):
        """Test user input."""
        ui = UIManager()

        with patch.object(ui.console, "input") as mock_input:
            mock_input.return_value = "user response"

            result = ui.input("Enter value: ")
            assert result == "user response"
            mock_input.assert_called_once_with("[cyan]Enter value: [/cyan]")

    def test_print_markdown(self):
        """Test markdown printing."""
        ui = UIManager()

        with patch("spot_deployer.utils.ui_manager.Markdown") as mock_markdown:
            ui.print_markdown("# Header\n\nSome **bold** text")
            mock_markdown.assert_called_once_with("# Header\n\nSome **bold** text")
