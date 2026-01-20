"""
Structured Logging Configuration for L4D V3

Provides comprehensive logging infrastructure with:
- Structured JSON format for machine parsing
- Color-coded console output for human readability
- File rotation for long-running sessions
- Separate error log for critical issues
- Request/session ID correlation
- Module and operation filtering
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
from logging.handlers import RotatingFileHandler

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

# Default configuration values
DEFAULT_LOG_DIR = "v2/logs"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_LOG_LEVEL = logging.INFO


class LoggingConfig:
    """
    Centralized logging configuration for L4D V3.
    
    Manages logger setup with structured output, multiple handlers,
    and context correlation support.
    """
    
    def __init__(
        self,
        log_dir: str = DEFAULT_LOG_DIR,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT,
        level: str = "INFO",
        json_format: bool = True
    ):
        """
        Initialize logging configuration.
        
        Args:
            log_dir: Directory for log files
            max_bytes: Maximum size per log file before rotation
            backup_count: Number of backup files to keep
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            json_format: If True, use JSON format for structured output
        """
        self.log_dir = Path(log_dir)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.level = self._parse_level(level)
        self.json_format = json_format
        self._configured = False
        
    def _parse_level(self, level: str) -> int:
        """Parse log level string to logging constant."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level.upper(), logging.INFO)
    
    def setup(self) -> None:
        """
        Configure the logging system with all handlers.
        
        This sets up:
        1. Console handler with color-coded output
        2. File handler with rotation
        3. Separate error log file
        4. Structured formatting
        """
        if self._configured:
            return
            
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)
        
        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Setup console handler
        self._setup_console_handler(root_logger)
        
        # Setup file handler
        self._setup_file_handler(root_logger)
        
        # Setup error file handler
        self._setup_error_handler(root_logger)
        
        # Setup structlog if available
        if STRUCTLOG_AVAILABLE:
            self._setup_structlog()
        
        self._configured = True
        
    def _setup_console_handler(self, logger: logging.Logger) -> None:
        """Setup console handler with color-coded output."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        
        if self.json_format and STRUCTLOG_AVAILABLE:
            # Use structlog for console if JSON format enabled
            formatter = structlog.dev.ConsoleFormatter(colors=True)
        else:
            # Use colored formatter for console
            formatter = ColoredFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    def _setup_file_handler(self, logger: logging.Logger) -> None:
        """Setup rotating file handler for main log."""
        log_file = self.log_dir / "l4d.log"
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.level)
        
        if self.json_format:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    def _setup_error_handler(self, logger: logging.Logger) -> None:
        """Setup separate file handler for errors and critical issues."""
        error_log_file = self.log_dir / "errors.log"
        error_handler = RotatingFileHandler(
            filename=error_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        if self.json_format:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s [%(funcName)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
    def _setup_structlog(self) -> None:
        """Setup structlog for structured logging."""
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer() if self.json_format else structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def get_logger(self, name: str, **context: Any) -> logging.Logger:
        """
        Get a configured logger with optional context.
        
        Args:
            name: Logger name (typically __name__)
            **context: Additional context to add to all log messages
            
        Returns:
            Configured logger instance
        """
        if not self._configured:
            self.setup()
            
        logger = logging.getLogger(name)
        
        # Add context if structlog is available
        if STRUCTLOG_AVAILABLE and context:
            structlog.contextvars.bind_contextvars(**context)
        
        return logger
    
    def add_context(self, **context: Any) -> None:
        """
        Add context to all future log messages.
        
        Args:
            **context: Context key-value pairs (e.g., operation_id, task_id)
        """
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.bind_contextvars(**context)
    
    def clear_context(self) -> None:
        """Clear all context variables."""
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.clear_contextvars()


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color-coded output for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format the message with color
        record.levelname = f"{log_color}{record.levelname}{reset}"
        record.name = f"{log_color}{record.name}{reset}"
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Formatter that outputs log records as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context if available
        if hasattr(record, 'operation_id'):
            log_obj['operation_id'] = record.operation_id
        if hasattr(record, 'task_id'):
            log_obj['task_id'] = record.task_id
        if hasattr(record, 'session_id'):
            log_obj['session_id'] = record.session_id
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'exc_info', 
                          'exc_text', 'stack_info', 'lineno', 'funcName',
                          'created', 'msecs', 'relativeCreated', 'thread',
                          'threadName', 'processName', 'process', 'message',
                          'asctime']:
                log_obj[key] = value
        
        return json.dumps(log_obj)


# Global logging configuration instance
_logging_config: Optional[LoggingConfig] = None


def get_logging_config(
    log_dir: str = DEFAULT_LOG_DIR,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    level: str = "INFO",
    json_format: bool = True
) -> LoggingConfig:
    """
    Get or create the global logging configuration.
    
    Args:
        log_dir: Directory for log files
        max_bytes: Maximum size per log file before rotation
        backup_count: Number of backup files to keep
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON format for structured output
        
    Returns:
        LoggingConfig instance
    """
    global _logging_config
    
    if _logging_config is None:
        _logging_config = LoggingConfig(
            log_dir=log_dir,
            max_bytes=max_bytes,
            backup_count=backup_count,
            level=level,
            json_format=json_format
        )
        _logging_config.setup()
    
    return _logging_config


def get_logger(name: str, **context: Any) -> logging.Logger:
    """
    Get a configured logger with optional context.
    
    Args:
        name: Logger name (typically __name__)
        **context: Additional context to add to all log messages
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Task started")
        
        >>> logger = get_logger(__name__, operation_id="abc-123", task_id=42)
        >>> logger.info("Task implementation started")
    """
    config = get_logging_config()
    return config.get_logger(name, **context)


def add_log_context(**context: Any) -> None:
    """
    Add context to all future log messages.
    
    Args:
        **context: Context key-value pairs (e.g., operation_id, task_id)
        
    Example:
        >>> add_log_context(operation_id="abc-123", task_id=42)
        >>> logger.info("This message will include operation_id and task_id")
    """
    config = get_logging_config()
    config.add_context(**context)


def clear_log_context() -> None:
    """Clear all context variables."""
    config = get_logging_config()
    config.clear_context()


# Convenience functions for different log levels
def debug(message: str, **kwargs: Any) -> None:
    """Log a debug message."""
    logger = get_logger(__name__)
    logger.debug(message, extra=kwargs)


def info(message: str, **kwargs: Any) -> None:
    """Log an info message."""
    logger = get_logger(__name__)
    logger.info(message, extra=kwargs)


def warning(message: str, **kwargs: Any) -> None:
    """Log a warning message."""
    logger = get_logger(__name__)
    logger.warning(message, extra=kwargs)


def error(message: str, **kwargs: Any) -> None:
    """Log an error message."""
    logger = get_logger(__name__)
    logger.error(message, extra=kwargs)


def critical(message: str, **kwargs: Any) -> None:
    """Log a critical message."""
    logger = get_logger(__name__)
    logger.critical(message, extra=kwargs)
