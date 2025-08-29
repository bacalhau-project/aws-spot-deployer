"""Unit tests for ShutdownHandler."""

import signal
from unittest.mock import MagicMock, patch

from spot_deployer.utils.shutdown_handler import (
    ShutdownContext,
    ShutdownHandler,
    handle_shutdown_in_operation,
)


class TestShutdownHandler:
    """Test cases for ShutdownHandler."""

    def test_initialization(self):
        """Test handler initialization."""
        handler = ShutdownHandler()
        assert handler._shutdown_requested is False
        assert handler._cleanup_callbacks == []

    def test_register_unregister_signals(self):
        """Test signal registration and unregistration."""
        handler = ShutdownHandler()

        with patch("signal.signal") as mock_signal:
            # Mock original handlers
            original_sigint = MagicMock()
            original_sigterm = MagicMock()
            mock_signal.side_effect = [original_sigint, original_sigterm]

            # Register
            handler.register()

            # Should have registered both signals
            assert mock_signal.call_count == 2
            mock_signal.assert_any_call(signal.SIGINT, handler._handle_shutdown)
            mock_signal.assert_any_call(signal.SIGTERM, handler._handle_shutdown)

            # Reset mock
            mock_signal.reset_mock()
            mock_signal.side_effect = None

            # Unregister
            handler.unregister()

            # Should restore original handlers
            assert mock_signal.call_count == 2
            mock_signal.assert_any_call(signal.SIGINT, original_sigint)
            mock_signal.assert_any_call(signal.SIGTERM, original_sigterm)

    def test_add_remove_cleanup_callback(self):
        """Test adding and removing cleanup callbacks."""
        handler = ShutdownHandler()

        callback1 = MagicMock()
        callback2 = MagicMock()

        # Add callbacks
        handler.add_cleanup_callback(callback1)
        handler.add_cleanup_callback(callback2)
        assert len(handler._cleanup_callbacks) == 2

        # Remove one callback
        handler.remove_cleanup_callback(callback1)
        assert len(handler._cleanup_callbacks) == 1
        assert callback2 in handler._cleanup_callbacks

        # Try to remove non-existent callback (should not raise)
        handler.remove_cleanup_callback(callback1)
        assert len(handler._cleanup_callbacks) == 1

    def test_is_shutdown_requested(self):
        """Test shutdown request status."""
        handler = ShutdownHandler()

        assert handler.is_shutdown_requested() is False

        handler._shutdown_requested = True
        assert handler.is_shutdown_requested() is True

    def test_handle_shutdown_first_signal(self):
        """Test handling first shutdown signal."""
        handler = ShutdownHandler()

        # Add cleanup callbacks
        callback1 = MagicMock()
        callback2 = MagicMock()
        handler.add_cleanup_callback(callback1)
        handler.add_cleanup_callback(callback2)

        with patch.object(handler, "unregister") as mock_unregister:
            with patch.object(handler.ui.console, "print") as mock_print:
                # Simulate SIGINT
                handler._handle_shutdown(signal.SIGINT, None)

                # Should set shutdown flag
                assert handler._shutdown_requested is True

                # Should print messages
                assert mock_print.call_count == 2
                assert "SIGINT" in mock_print.call_args_list[0][0][0]

                # Should call cleanup callbacks
                callback1.assert_called_once()
                callback2.assert_called_once()

                # Should unregister handlers
                mock_unregister.assert_called_once()

    def test_handle_shutdown_second_signal(self):
        """Test handling second shutdown signal (force exit)."""
        handler = ShutdownHandler()
        handler._shutdown_requested = True  # Already requested

        with patch("sys.exit") as mock_exit:
            with patch.object(handler.ui, "print_error") as mock_print_error:
                handler._handle_shutdown(signal.SIGINT, None)

                # Should force exit
                mock_print_error.assert_called_once()
                mock_exit.assert_called_once_with(1)

    def test_cleanup_callback_error_handling(self):
        """Test error handling in cleanup callbacks."""
        handler = ShutdownHandler()

        # Add callback that raises exception
        bad_callback = MagicMock(side_effect=Exception("Cleanup failed"))
        good_callback = MagicMock()

        handler.add_cleanup_callback(bad_callback)
        handler.add_cleanup_callback(good_callback)

        with patch.object(handler.ui, "print_error") as mock_print_error:
            with patch.object(handler, "unregister"):
                handler._handle_shutdown(signal.SIGINT, None)

                # Should handle error and continue
                bad_callback.assert_called_once()
                good_callback.assert_called_once()
                mock_print_error.assert_called_once()
                assert "Cleanup failed" in str(mock_print_error.call_args)


class TestShutdownContext:
    """Test cases for ShutdownContext."""

    def test_context_manager(self):
        """Test context manager functionality."""
        cleanup_called = []

        def cleanup_func():
            cleanup_called.append(True)

        with patch("signal.signal"):
            with ShutdownContext("Test cleanup") as ctx:
                ctx.add_cleanup(cleanup_func)

                # Should be able to check shutdown status
                assert ctx.shutdown_requested is False

        # Cleanup not called unless shutdown requested
        assert len(cleanup_called) == 0

    def test_context_with_shutdown(self):
        """Test context manager with shutdown signal."""
        cleanup_called = []

        def cleanup_func():
            cleanup_called.append(True)

        with patch("signal.signal"):
            with ShutdownContext("Test cleanup") as ctx:
                ctx.add_cleanup(cleanup_func)

                # Simulate shutdown
                ctx.handler._shutdown_requested = True

                # Trigger cleanup manually (normally done by signal)
                with patch.object(ctx.handler.ui, "print_warning"):
                    with patch("sys.exit") as mock_exit:
                        ctx.handler._handle_shutdown(signal.SIGINT, None)
                        mock_exit.assert_called_once_with(1)

        # Cleanup should have been called
        assert len(cleanup_called) == 1

    def test_multiple_cleanup_functions(self):
        """Test multiple cleanup functions in context."""
        cleanup_order = []

        def cleanup1():
            cleanup_order.append(1)

        def cleanup2():
            cleanup_order.append(2)

        with patch("signal.signal"):
            with ShutdownContext() as ctx:
                ctx.add_cleanup(cleanup1)
                ctx.add_cleanup(cleanup2)

                # Manually trigger cleanup
                for func in ctx._cleanup_functions:
                    func()

        # Should execute in order
        assert cleanup_order == [1, 2]

    def test_cleanup_error_handling(self):
        """Test error handling in cleanup functions."""
        successful_cleanup = []

        def bad_cleanup():
            raise Exception("Cleanup error")

        def good_cleanup():
            successful_cleanup.append(True)

        with patch("signal.signal"):
            with patch("spot_deployer.utils.shutdown_handler.UIManager") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui

                with ShutdownContext() as ctx:
                    ctx.add_cleanup(bad_cleanup)
                    ctx.add_cleanup(good_cleanup)

                    # Manually trigger cleanup callback
                    ctx.handler._cleanup_callbacks[0]()

        # Good cleanup should still run despite bad cleanup error
        assert len(successful_cleanup) == 1


class TestShutdownDecorator:
    """Test cases for handle_shutdown_in_operation decorator."""

    def test_decorator_basic(self):
        """Test basic decorator functionality."""
        cleanup_called = []

        def cleanup():
            cleanup_called.append(True)

        @handle_shutdown_in_operation("test operation", cleanup)
        def test_func():
            return "success"

        with patch("signal.signal"):
            result = test_func()

        assert result == "success"
        # Cleanup not called without shutdown
        assert len(cleanup_called) == 0

    def test_decorator_with_shutdown_context_param(self):
        """Test decorator passing shutdown context to function."""
        context_received = []

        @handle_shutdown_in_operation("test operation")
        def test_func(arg1, shutdown_context=None):
            context_received.append(shutdown_context)
            return arg1

        with patch("signal.signal"):
            result = test_func("test")

        assert result == "test"
        assert len(context_received) == 1
        assert context_received[0] is not None
        assert hasattr(context_received[0], "shutdown_requested")

    def test_decorator_without_shutdown_context_param(self):
        """Test decorator with function that doesn't accept shutdown_context."""

        @handle_shutdown_in_operation("test operation")
        def test_func(arg1, arg2):
            return arg1 + arg2

        with patch("signal.signal"):
            result = test_func(1, 2)

        assert result == 3
