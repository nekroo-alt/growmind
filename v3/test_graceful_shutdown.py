"""
Unit tests for Graceful Shutdown Handler
"""

import signal
import sys
import threading
import time
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from v2.core.graceful_shutdown import (
    GracefulShutdown,
    ShutdownState,
    init_graceful_shutdown,
    get_shutdown_handler,
    is_shutdown_requested,
    register_cleanup,
    critical_operation,
    _global_shutdown_handler,
)


@pytest.fixture(autouse=True)
def reset_global_handler():
    """Reset global handler before and after each test"""
    global _global_shutdown_handler
    _global_shutdown_handler = None
    yield
    _global_shutdown_handler = None


@pytest.fixture
def mock_checkpoint_manager():
    """Mock checkpoint manager"""
    manager = Mock()
    manager.create.return_value = "test_checkpoint_id"
    return manager


@pytest.fixture
def shutdown_handler(mock_checkpoint_manager):
    """Create a fresh shutdown handler for each test"""
    return GracefulShutdown(checkpoint_manager=mock_checkpoint_manager)


class TestShutdownState:
    """Test ShutdownState dataclass"""

    def test_shutdown_state_initialization(self):
        """Test that ShutdownState initializes correctly"""
        state = ShutdownState()
        assert not state.shutdown_requested
        assert not state.in_critical_operation
        assert state.critical_operation_name is None
        assert state.cleanup_functions == []
        assert type(state.cleanup_lock).__name__ == "RLock"

    def test_shutdown_state_with_values(self):
        """Test ShutdownState with custom values"""
        cleanup_func = Mock()
        state = ShutdownState(
            shutdown_requested=True,
            in_critical_operation=True,
            critical_operation_name="test_operation",
            cleanup_functions=[cleanup_func],
        )
        assert state.shutdown_requested
        assert state.in_critical_operation
        assert state.critical_operation_name == "test_operation"
        assert len(state.cleanup_functions) == 1


class TestGracefulShutdown:
    """Test GracefulShutdown class"""

    def test_initialization(self, mock_checkpoint_manager):
        """Test that GracefulShutdown initializes correctly"""
        handler = GracefulShutdown(checkpoint_manager=mock_checkpoint_manager)

        assert handler.checkpoint_manager == mock_checkpoint_manager
        assert not handler.is_shutdown_requested()
        assert not handler.is_in_critical_operation()
        assert type(handler.state.cleanup_lock).__name__ == "RLock"

    def test_signal_registration(self, shutdown_handler):
        """Test that signal handlers are registered"""
        # Handlers should be registered for SIGINT and SIGTERM
        assert signal.SIGINT in shutdown_handler.shutdown_handlers
        assert signal.SIGTERM in shutdown_handler.shutdown_handlers

    def test_register_cleanup_function(self, shutdown_handler):
        """Test registering cleanup functions"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        assert len(shutdown_handler.state.cleanup_functions) == 1
        assert cleanup_func in shutdown_handler.state.cleanup_functions

    def test_register_multiple_cleanup_functions(self, shutdown_handler):
        """Test registering multiple cleanup functions"""
        cleanup1 = Mock()
        cleanup2 = Mock()
        cleanup3 = Mock()

        shutdown_handler.register_cleanup(cleanup1)
        shutdown_handler.register_cleanup(cleanup2)
        shutdown_handler.register_cleanup(cleanup3)

        assert len(shutdown_handler.state.cleanup_functions) == 3

    def test_unregister_cleanup_function(self, shutdown_handler):
        """Test unregistering cleanup functions"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        assert len(shutdown_handler.state.cleanup_functions) == 1

        shutdown_handler.unregister_cleanup(cleanup_func)
        assert len(shutdown_handler.state.cleanup_functions) == 0

    def test_perform_cleanup(self, shutdown_handler):
        """Test that cleanup functions are executed"""
        cleanup1 = Mock()
        cleanup2 = Mock()

        shutdown_handler.register_cleanup(cleanup1)
        shutdown_handler.register_cleanup(cleanup2)

        shutdown_handler.perform_cleanup()

        cleanup1.assert_called_once()
        cleanup2.assert_called_once()

    def test_perform_cleanup_handles_errors(self, shutdown_handler):
        """Test that errors in cleanup functions are handled gracefully"""
        cleanup_success = Mock()
        cleanup_error = Mock(side_effect=Exception("Cleanup failed"))

        shutdown_handler.register_cleanup(cleanup_success)
        shutdown_handler.register_cleanup(cleanup_error)

        # Should not raise exception
        shutdown_handler.perform_cleanup()

        cleanup_success.assert_called_once()
        cleanup_error.assert_called_once()

    def test_is_shutdown_requested(self, shutdown_handler):
        """Test shutdown request detection"""
        assert not shutdown_handler.is_shutdown_requested()

        shutdown_handler.state.shutdown_requested = True
        assert shutdown_handler.is_shutdown_requested()

    def test_is_in_critical_operation(self, shutdown_handler):
        """Test critical operation detection"""
        assert not shutdown_handler.is_in_critical_operation()

        shutdown_handler.state.in_critical_operation = True
        shutdown_handler.state.critical_operation_name = "test"

        assert shutdown_handler.is_in_critical_operation()

    def test_get_state(self, shutdown_handler):
        """Test getting shutdown state"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        state = shutdown_handler.get_state()

        assert isinstance(state, dict)
        assert "shutdown_requested" in state
        assert "in_critical_operation" in state
        assert "critical_operation_name" in state
        assert "cleanup_functions_count" in state
        assert state["cleanup_functions_count"] == 1

    def test_reset_shutdown(self, shutdown_handler):
        """Test resetting shutdown state"""
        shutdown_handler.state.shutdown_requested = True
        assert shutdown_handler.is_shutdown_requested()

        shutdown_handler.reset_shutdown()
        assert not shutdown_handler.is_shutdown_requested()

    def test_critical_operation_context_manager(self, shutdown_handler):
        """Test critical operation context manager"""
        assert not shutdown_handler.is_in_critical_operation()

        with shutdown_handler.critical_operation("test_operation"):
            assert shutdown_handler.is_in_critical_operation()
            assert shutdown_handler.state.critical_operation_name == "test_operation"

        assert not shutdown_handler.is_in_critical_operation()
        assert shutdown_handler.state.critical_operation_name is None

    def test_critical_operation_preserves_state_on_exception(self, shutdown_handler):
        """Test that critical operation state is preserved on exception"""
        assert not shutdown_handler.is_in_critical_operation()

        with pytest.raises(ValueError):
            with shutdown_handler.critical_operation("test_operation"):
                assert shutdown_handler.is_in_critical_operation()
                raise ValueError("Test error")

        # State should still be reset after exception
        assert not shutdown_handler.is_in_critical_operation()

    def test_context_manager_exit(self, shutdown_handler):
        """Test GracefulShutdown as context manager"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        with shutdown_handler:
            pass

        # Cleanup should not be called on normal exit
        cleanup_func.assert_not_called()

    def test_context_manager_exit_with_exception(self, shutdown_handler):
        """Test context manager exit with exception"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        with pytest.raises(ValueError):
            with shutdown_handler:
                raise ValueError("Test error")

        # Cleanup should be called on exception
        cleanup_func.assert_called_once()


class TestSignalHandling:
    """Test signal handling"""

    def test_handle_sigint(self, shutdown_handler, mock_checkpoint_manager):
        """Test handling SIGINT signal"""
        # Mock sys.exit to prevent actual exit
        with patch("sys.exit") as mock_exit:
            # Send SIGINT signal
            shutdown_handler._handle_signal(signal.SIGINT, None)

            # Shutdown should be requested
            assert shutdown_handler.is_shutdown_requested()

            # Reset for next test
            shutdown_handler.reset_shutdown()

            # If in critical operation, checkpoint should be created
            with shutdown_handler.critical_operation("test"):
                shutdown_handler._handle_signal(signal.SIGINT, None)
                mock_checkpoint_manager.create.assert_called()

    def test_handle_sigterm(self, shutdown_handler, mock_checkpoint_manager):
        """Test handling SIGTERM signal"""
        with patch("sys.exit"):
            shutdown_handler._handle_signal(signal.SIGTERM, None)

            assert shutdown_handler.is_shutdown_requested()

    def test_double_ctrl_c_forces_shutdown(self, shutdown_handler):
        """Test that double Ctrl+C forces immediate shutdown"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        with patch("sys.exit") as mock_exit:
            # First Ctrl+C
            shutdown_handler._handle_signal(signal.SIGINT, None)

            # Second Ctrl+C should force exit
            shutdown_handler._handle_signal(signal.SIGINT, None)

            # Should call sys.exit with 130
            mock_exit.assert_called_with(130)

    def test_force_shutdown_performs_cleanup(self, shutdown_handler):
        """Test that forced shutdown performs cleanup"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        with patch("sys.exit"):
            shutdown_handler._force_shutdown()

            cleanup_func.assert_called_once()

    def test_create_shutdown_checkpoint(
        self, shutdown_handler, mock_checkpoint_manager
    ):
        """Test creating checkpoint during shutdown"""
        shutdown_handler.state.in_critical_operation = True
        shutdown_handler.state.critical_operation_name = "test_operation"

        shutdown_handler._create_shutdown_checkpoint()

        mock_checkpoint_manager.create.assert_called_once_with(
            reason="interrupt_shutdown", operation_name="test_operation"
        )

    def test_create_checkpoint_without_manager(self, shutdown_handler):
        """Test handling shutdown without checkpoint manager"""
        shutdown_handler.checkpoint_manager = None
        shutdown_handler.state.in_critical_operation = True

        # Should not raise exception
        shutdown_handler._create_shutdown_checkpoint()

    def test_create_checkpoint_handles_errors(
        self, shutdown_handler, mock_checkpoint_manager
    ):
        """Test handling checkpoint creation errors"""
        mock_checkpoint_manager.create.side_effect = Exception("Checkpoint failed")
        shutdown_handler.state.in_critical_operation = True

        # Should not raise exception
        shutdown_handler._create_shutdown_checkpoint()


class TestGlobalFunctions:
    """Test global convenience functions"""

    def test_init_graceful_shutdown(self, mock_checkpoint_manager):
        """Test initializing global shutdown handler"""
        handler = init_graceful_shutdown(checkpoint_manager=mock_checkpoint_manager)

        assert isinstance(handler, GracefulShutdown)
        assert handler.checkpoint_manager == mock_checkpoint_manager

    def test_get_shutdown_handler(self):
        """Test getting global shutdown handler"""
        # Initialize and verify
        init_graceful_shutdown()
        handler = get_shutdown_handler()
        assert isinstance(handler, GracefulShutdown)

        # Can get the same handler multiple times
        handler2 = get_shutdown_handler()
        assert handler is handler2  # Same instance

    def test_is_shutdown_requested_global(self):
        """Test global is_shutdown_requested function"""
        assert not is_shutdown_requested()

        handler = init_graceful_shutdown()
        handler.state.shutdown_requested = True

        assert is_shutdown_requested()

    def test_register_cleanup_global(self):
        """Test global register_cleanup function"""
        cleanup_func = Mock()

        # Should not raise error even without handler
        register_cleanup(cleanup_func)

        handler = init_graceful_shutdown()
        register_cleanup(cleanup_func)

        assert cleanup_func in handler.state.cleanup_functions

    def test_critical_operation_global(self):
        """Test global critical_operation context manager"""
        handler = init_graceful_shutdown()

        assert not handler.is_in_critical_operation()

        with patch("sys.exit"):
            with critical_operation("test_operation"):
                assert handler.is_in_critical_operation()

        assert not handler.is_in_critical_operation()


class TestThreadSafety:
    """Test thread safety of graceful shutdown"""

    def test_concurrent_cleanup_registration(self, shutdown_handler):
        """Test concurrent cleanup function registration"""

        def register_cleanup():
            cleanup = Mock()
            shutdown_handler.register_cleanup(cleanup)

        threads = [threading.Thread(target=register_cleanup) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All 10 cleanup functions should be registered
        assert len(shutdown_handler.state.cleanup_functions) == 10

    def test_concurrent_shutdown_checks(self, shutdown_handler):
        """Test concurrent shutdown status checks"""

        def check_shutdown():
            for _ in range(100):
                _ = shutdown_handler.is_shutdown_requested()

        threads = [threading.Thread(target=check_shutdown) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors
        assert True

    def test_concurrent_critical_operations(self, shutdown_handler):
        """Test concurrent critical operations"""

        def perform_critical_op(op_name):
            with shutdown_handler.critical_operation(op_name):
                time.sleep(0.01)

        threads = [
            threading.Thread(target=perform_critical_op, args=(f"op_{i}",))
            for i in range(5)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors
        assert True


class TestIntegrationScenarios:
    """Test integration scenarios"""

    def test_shutdown_during_critical_operation(
        self, shutdown_handler, mock_checkpoint_manager
    ):
        """Test shutdown during critical operation creates checkpoint"""
        with patch("sys.exit"):
            with shutdown_handler.critical_operation("test_operation"):
                # Simulate shutdown signal
                shutdown_handler._handle_signal(signal.SIGINT, None)

                # Checkpoint should be created
                mock_checkpoint_manager.create.assert_called_once()

    def test_shutdown_after_critical_operation(
        self, shutdown_handler, mock_checkpoint_manager
    ):
        """Test shutdown after critical operation doesn't create checkpoint"""
        with patch("sys.exit"):
            # Perform critical operation
            with shutdown_handler.critical_operation("test_operation"):
                pass

            # Clear previous calls
            mock_checkpoint_manager.reset_mock()

            # Signal shutdown
            shutdown_handler._handle_signal(signal.SIGINT, None)

            # Checkpoint should not be created (not in critical operation)
            mock_checkpoint_manager.create.assert_not_called()

    def test_cleanup_on_exception_in_critical_operation(self, shutdown_handler):
        """Test cleanup on exception in critical operation"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        with patch("sys.exit"):
            with pytest.raises(ValueError):
                with shutdown_handler.critical_operation("test_operation"):
                    shutdown_handler.state.shutdown_requested = True
                    raise ValueError("Test error")

        # Cleanup should be called
        cleanup_func.assert_called_once()

    def test_multiple_shutdown_attempts(self, shutdown_handler):
        """Test multiple shutdown attempts"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        with patch("sys.exit") as mock_exit:
            # First shutdown
            shutdown_handler._handle_signal(signal.SIGINT, None)
            assert shutdown_handler.is_shutdown_requested()
            assert mock_exit.call_count == 0

            # Second shutdown (should force)
            shutdown_handler._handle_signal(signal.SIGINT, None)
            assert mock_exit.call_count == 1
            assert mock_exit.call_args == call(130)

    def test_normal_operation_flow(self, shutdown_handler):
        """Test normal operation flow without shutdown"""
        cleanup_func = Mock()
        shutdown_handler.register_cleanup(cleanup_func)

        # Simulate normal operation
        with shutdown_handler.critical_operation("task_implementation"):
            # Perform work
            time.sleep(0.01)

        # Cleanup should not be called
        cleanup_func.assert_not_called()

        # Shutdown should not be requested
        assert not shutdown_handler.is_shutdown_requested()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
