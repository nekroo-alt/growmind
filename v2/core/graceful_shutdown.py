"""
Graceful Shutdown Handler for L4D V3

Handles SIGINT (Ctrl+C) and SIGTERM signals to ensure:
- State is saved before shutdown
- In-progress operations are cancelled cleanly
- Database connections are closed properly
- Logs and telemetry are flushed
- Checkpoints are created if in critical operation
- System can resume from checkpoint on next start
"""

import signal
import threading
import sys
import logging
from contextlib import contextmanager
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ShutdownState:
    """Tracks the current shutdown state"""
    shutdown_requested: bool = False
    in_critical_operation: bool = False
    critical_operation_name: Optional[str] = None
    cleanup_functions: list = None
    cleanup_lock: threading.RLock = None
    
    def __post_init__(self):
        if self.cleanup_functions is None:
            self.cleanup_functions = []
        if self.cleanup_lock is None:
            self.cleanup_lock = threading.RLock()


class GracefulShutdown:
    """
    Handles graceful shutdown for L4D system.
    
    Usage:
        # Initialize at startup
        shutdown_handler = GracefulShutdown()
        
        # Register cleanup function
        shutdown_handler.register_cleanup(close_database_connections)
        
        # Mark critical operation
        with shutdown_handler.critical_operation("implement_task"):
            # ... perform critical operation ...
            pass
            
        # Check if shutdown requested
        if shutdown_handler.is_shutdown_requested():
            logger.info("Shutdown requested, stopping gracefully...")
            shutdown_handler.perform_cleanup()
            sys.exit(0)
    """
    
    def __init__(self, checkpoint_manager=None):
        """
        Initialize graceful shutdown handler.
        
        Args:
            checkpoint_manager: Optional CheckpointManager instance for state saving
        """
        self.state = ShutdownState()
        self.checkpoint_manager = checkpoint_manager
        self.shutdown_handlers: Dict[int, Callable] = {}
        self.shutdown_lock = threading.RLock()
        
        # Register signal handlers
        self._register_signal_handlers()
        
        logger.info("Graceful shutdown handler initialized")
    
    def _register_signal_handlers(self):
        """Register signal handlers for SIGINT and SIGTERM"""
        try:
            # Register SIGINT (Ctrl+C)
            self.shutdown_handlers[signal.SIGINT] = signal.signal(
                signal.SIGINT, 
                self._handle_signal
            )
            logger.debug("Registered SIGINT handler")
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not register SIGINT handler: {e}")
        
        try:
            # Register SIGTERM
            self.shutdown_handlers[signal.SIGTERM] = signal.signal(
                signal.SIGTERM,
                self._handle_signal
            )
            logger.debug("Registered SIGTERM handler")
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not register SIGTERM handler: {e}")
    
    def _handle_signal(self, signum: int, frame):
        """
        Handle shutdown signals.
        
        Args:
            signum: Signal number (SIGINT or SIGTERM)
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        
        with self.shutdown_lock:
            # If shutdown already in progress, force exit
            if self.state.shutdown_requested:
                logger.warning(f"Received {signal_name} again, forcing exit...")
                self._force_shutdown()
                return
            
            # Mark shutdown as requested
            self.state.shutdown_requested = True
            logger.info(f"Received {signal_name}, initiating graceful shutdown...")
            
            # Log current state
            if self.state.in_critical_operation:
                logger.warning(
                    f"Shutdown during critical operation: {self.state.critical_operation_name}"
                )
                logger.info("Creating checkpoint before shutdown...")
                self._create_shutdown_checkpoint()
            else:
                logger.info("Not in critical operation, shutting down...")
    
    def _create_shutdown_checkpoint(self):
        """Create checkpoint if in critical operation"""
        if self.checkpoint_manager:
            try:
                checkpoint_id = self.checkpoint_manager.create(
                    reason="interrupt_shutdown",
                    operation_name=self.state.critical_operation_name
                )
                logger.info(f"Created checkpoint: {checkpoint_id}")
            except Exception as e:
                logger.error(f"Failed to create checkpoint: {e}")
        else:
            logger.warning("No checkpoint manager available, state may be lost")
    
    def _force_shutdown(self):
        """Force immediate shutdown"""
        logger.critical("Forcing immediate shutdown")
        
        # Try to perform cleanup
        try:
            self.perform_cleanup()
        except Exception as e:
            logger.error(f"Error during forced shutdown cleanup: {e}")
        
        # Exit with error code
        sys.exit(130)  # Standard exit code for SIGINT
    
    def register_cleanup(self, cleanup_func: Callable):
        """
        Register a cleanup function to be called during shutdown.
        
        Args:
            cleanup_func: Callable function to execute during cleanup
        """
        with self.state.cleanup_lock:
            self.state.cleanup_functions.append(cleanup_func)
            func_name = getattr(cleanup_func, '__name__', str(cleanup_func))
            logger.debug(f"Registered cleanup function: {func_name}")
    
    def unregister_cleanup(self, cleanup_func: Callable):
        """
        Unregister a cleanup function.
        
        Args:
            cleanup_func: Callable function to remove from cleanup list
        """
        with self.state.cleanup_lock:
            if cleanup_func in self.state.cleanup_functions:
                self.state.cleanup_functions.remove(cleanup_func)
                func_name = getattr(cleanup_func, '__name__', str(cleanup_func))
                logger.debug(f"Unregistered cleanup function: {func_name}")
    
    def perform_cleanup(self):
        """Execute all registered cleanup functions"""
        logger.info("Performing cleanup...")
        
        with self.state.cleanup_lock:
            for cleanup_func in self.state.cleanup_functions:
                try:
                    func_name = getattr(cleanup_func, '__name__', str(cleanup_func))
                    logger.debug(f"Running cleanup: {func_name}")
                    cleanup_func()
                except Exception as e:
                    func_name = getattr(cleanup_func, '__name__', str(cleanup_func))
                    logger.error(f"Error in cleanup function {func_name}: {e}")
        
        logger.info("Cleanup completed")
    
    @contextmanager
    def critical_operation(self, operation_name: str):
        """
        Context manager for critical operations that need state preservation.
        
        Args:
            operation_name: Name of the critical operation
            
        Example:
            with shutdown_handler.critical_operation("implement_task"):
                # ... perform critical operation ...
                pass
        """
        # Mark operation as critical
        with self.state.cleanup_lock:
            self.state.in_critical_operation = True
            self.state.critical_operation_name = operation_name
        
        logger.debug(f"Entered critical operation: {operation_name}")
        
        try:
            yield
        finally:
            # Unmark operation as critical
            with self.state.cleanup_lock:
                self.state.in_critical_operation = False
                self.state.critical_operation_name = None
            
            logger.debug(f"Exited critical operation: {operation_name}")
            
            # Check if shutdown was requested during operation
            if self.is_shutdown_requested():
                logger.info("Shutdown requested during critical operation, initiating graceful shutdown...")
                self.perform_cleanup()
                sys.exit(0)
    
    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown has been requested.
        
        Returns:
            True if shutdown requested, False otherwise
        """
        return self.state.shutdown_requested
    
    def is_in_critical_operation(self) -> bool:
        """
        Check if currently in a critical operation.
        
        Returns:
            True if in critical operation, False otherwise
        """
        return self.state.in_critical_operation
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current shutdown state.
        
        Returns:
            Dictionary containing current shutdown state
        """
        with self.state.cleanup_lock:
            return {
                'shutdown_requested': self.state.shutdown_requested,
                'in_critical_operation': self.state.in_critical_operation,
                'critical_operation_name': self.state.critical_operation_name,
                'cleanup_functions_count': len(self.state.cleanup_functions)
            }
    
    def reset_shutdown(self):
        """Reset shutdown state (useful for testing)"""
        with self.shutdown_lock:
            self.state.shutdown_requested = False
            logger.debug("Shutdown state reset")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - perform cleanup on exit"""
        if self.is_shutdown_requested() or exc_type is not None:
            self.perform_cleanup()
        return False


# Global instance (can be imported as needed)
_global_shutdown_handler: Optional[GracefulShutdown] = None


def init_graceful_shutdown(checkpoint_manager=None) -> GracefulShutdown:
    """
    Initialize global graceful shutdown handler.
    
    Args:
        checkpoint_manager: Optional CheckpointManager instance
        
    Returns:
        GracefulShutdown instance
    """
    global _global_shutdown_handler
    
    if _global_shutdown_handler is None:
        _global_shutdown_handler = GracefulShutdown(checkpoint_manager)
    
    return _global_shutdown_handler


def get_shutdown_handler() -> Optional[GracefulShutdown]:
    """
    Get the global graceful shutdown handler instance.
    
    Returns:
        GracefulShutdown instance or None if not initialized
    """
    return _global_shutdown_handler


def is_shutdown_requested() -> bool:
    """
    Check if shutdown has been requested (convenience function).
    
    Returns:
        True if shutdown requested, False otherwise
    """
    handler = get_shutdown_handler()
    return handler is not None and handler.is_shutdown_requested()


def register_cleanup(cleanup_func: Callable):
    """
    Register a cleanup function (convenience function).
    
    Args:
        cleanup_func: Callable function to execute during cleanup
    """
    handler = get_shutdown_handler()
    if handler:
        handler.register_cleanup(cleanup_func)
    else:
        logger.warning("No shutdown handler initialized, cleanup function not registered")


@contextmanager
def critical_operation(operation_name: str):
    """
    Context manager for critical operations (convenience function).
    
    Args:
        operation_name: Name of the critical operation
        
    Example:
        with critical_operation("implement_task"):
            # ... perform critical operation ...
            pass
    """
    handler = get_shutdown_handler()
    if handler:
        with handler.critical_operation(operation_name):
            yield
    else:
        logger.warning("No shutdown handler initialized, marking operation as critical")
        yield
