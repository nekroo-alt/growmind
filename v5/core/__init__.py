"""
Core Module

Provides orchestration, logging, error handling, session management, and UI components.
"""

from .logging_config import get_logger, get_logging_config
from .error_handling import (
    classify_exception as classify_error,
    retry as retry_with_backoff,
    get_recovery_strategy,
)
from .graceful_shutdown import (
    GracefulShutdown,
    init_graceful_shutdown,
    get_shutdown_handler,
    is_shutdown_requested,
    register_cleanup,
    critical_operation,
)
from .health_check import run_health_check
from .session_manager import SessionManager, get_session_manager
from .transactions import Transaction, TransactionManager, with_transaction, create_transaction_manager, get_transaction_manager
from .ui import (
    ProgressIndicator,
    MultiStepProgress,
    ErrorDisplay,
    StatusDashboard,
    ProgressVisualizer,
    DecisionVisualizer,
    create_progress,
    create_multi_step_progress,
    create_error_display,
    display_error,
    display_recovery_result,
    create_status_dashboard,
    display_status,
    create_progress_visualizer,
    create_decision_visualizer,
)

__all__ = [
    'get_logger',
    'get_logging_config',
    'classify_error',
    'retry_with_backoff',
    'get_recovery_strategy',
    'GracefulShutdown',
    'init_graceful_shutdown',
    'get_shutdown_handler',
    'is_shutdown_requested',
    'register_cleanup',
    'critical_operation',
    'run_health_check',
    'SessionManager',
    'get_session_manager',
    'Transaction',
    'TransactionManager',
    'with_transaction',
    'create_transaction_manager',
    'get_transaction_manager',
    'ProgressIndicator',
    'MultiStepProgress',
    'ErrorDisplay',
    'StatusDashboard',
    'ProgressVisualizer',
    'DecisionVisualizer',
    'create_progress',
    'create_multi_step_progress',
    'create_error_display',
    'display_error',
    'display_recovery_result',
    'create_status_dashboard',
    'display_status',
    'create_progress_visualizer',
    'create_decision_visualizer',
]
