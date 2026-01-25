"""
Configuration Validation Module

This module provides comprehensive validation for L4D configuration including:
- Type checking for all configuration values
- Range checking (probabilities, positive integers, etc.)
- Path validation (directories exist, writable)
- LLM API key validation
- Conflict detection between settings
- Deprecated settings detection and migration
- Clear error messages with fix suggestions
"""

import os
import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationErrorSeverity(Enum):
    """Severity level for validation errors."""

    ERROR = "error"  # Must be fixed before proceeding
    WARNING = "warning"  # Recommended to fix
    INFO = "info"  # Informational


@dataclass
class ValidationError:
    """Configuration validation error."""

    severity: ValidationErrorSeverity
    section: str  # e.g., "llm", "cache", "logging"
    key: str  # e.g., "temperature", "max_size_mb"
    message: str  # Clear error message
    suggestion: Optional[str] = None  # Suggested fix
    deprecated_in: Optional[str] = None  # Version where deprecated
    migrate_to: Optional[str] = None  # New setting name


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    infos: List[ValidationError] = field(default_factory=list)

    def add_error(
        self,
        section: str,
        key: str,
        message: str,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add an error."""
        self.errors.append(
            ValidationError(
                severity=ValidationErrorSeverity.ERROR,
                section=section,
                key=key,
                message=message,
                suggestion=suggestion,
            )
        )
        self.is_valid = False

    def add_warning(
        self,
        section: str,
        key: str,
        message: str,
        suggestion: Optional[str] = None,
        deprecated_in: Optional[str] = None,
        migrate_to: Optional[str] = None,
    ) -> None:
        """Add a warning to the result."""
        error = ValidationError(
            severity=ValidationErrorSeverity.WARNING,
            section=section,
            key=key,
            message=message,
            suggestion=suggestion,
        )
        if deprecated_in:
            error.deprecated_in = deprecated_in
        if migrate_to:
            error.migrate_to = migrate_to
        self.warnings.append(error)

    def add_info(
        self,
        section: str,
        key: str,
        message: str,
    ) -> None:
        """Add an info message."""
        self.infos.append(
            ValidationError(
                severity=ValidationErrorSeverity.INFO,
                section=section,
                key=key,
                message=message,
            )
        )

    def get_summary(self) -> str:
        """Get a human-readable summary of validation results."""
        lines = []
        lines.append(f"Configuration Validation: {'VALID' if self.is_valid else 'INVALID'}")
        lines.append("")

        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  - [{error.section}.{error.key}] {error.message}")
                if error.suggestion:
                    lines.append(f"    Suggestion: {error.suggestion}")
                if error.deprecated_in:
                    lines.append(f"    Deprecated in: {error.deprecated_in}")
                    if error.migrate_to:
                        lines.append(f"    Migrate to: {error.migrate_to}")
            lines.append("")

        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  - [{warning.section}.{warning.key}] {warning.message}")
                if warning.suggestion:
                    lines.append(f"    Suggestion: {warning.suggestion}")
            lines.append("")

        if self.infos:
            lines.append(f"Information ({len(self.infos)}):")
            for info in self.infos:
                lines.append(f"  - [{info.section}.{info.key}] {info.message}")

        return "\n".join(lines)


class ConfigValidator:
    """Validates L4D configuration."""

    # Model context limits
    MODEL_CONTEXT_LIMITS = {
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "gemini-pro": 32768,
    }

    # Deprecated settings with migration info
    DEPRECATED_SETTINGS = {
        "adaptive_reasoning": {
            "deprecated_in": "5.0.0",
            "migrate_to": "custom.adaptive_reasoning",
        },
        "progress_tracking": {
            "deprecated_in": "5.0.0",
            "migrate_to": "custom.progress_tracking",
        },
        "trap_detection": {
            "deprecated_in": "5.0.0",
            "migrate_to": "custom.trap_detection",
        },
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ConfigValidator.

        Args:
            config: Configuration dictionary to validate
        """
        self.config = config

    def validate(self) -> ValidationResult:
        """
        Validate entire configuration.

        Returns:
            ValidationResult: Validation result with errors, warnings, and infos
        """
        result = ValidationResult(is_valid=True)

        # Validate each section
        self._validate_llm_config(result)
        self._validate_cache_config(result)
        self._validate_logging_config(result)
        self._validate_telemetry_config(result)
        self._validate_checkpoint_config(result)
        self._validate_session_config(result)
        self._validate_custom_config(result)

        # Check for conflicts between sections
        self._check_conflicts(result)

        # Check for deprecated settings
        self._check_deprecated_settings(result)

        return result

    def _validate_llm_config(self, result: ValidationResult) -> None:
        """Validate LLM configuration."""
        llm = self.config.get("llm", {})

        # Provider
        provider = llm.get("provider")
        if provider:
            valid_providers = ["openai", "anthropic", "gemini"]
            if provider not in valid_providers:
                result.add_error(
                    "llm",
                    "provider",
                    f"Invalid provider: {provider}. Valid providers: {', '.join(valid_providers)}",
                    suggestion=f"Set provider to one of: {', '.join(valid_providers)}",
                )

        # Model
        model = llm.get("model")
        if model:
            valid_models = list(self.MODEL_CONTEXT_LIMITS.keys())
            if model not in valid_models:
                result.add_warning(
                    "llm",
                    "model",
                    f"Unknown model: {model}. Known models: {', '.join(valid_models[:5])}, ...",
                    suggestion=f"Use a known model: {', '.join(valid_models[:3])}",
                )

        # Temperature
        temperature = llm.get("temperature")
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                result.add_error(
                    "llm",
                    "temperature",
                    f"Temperature must be a number, got {type(temperature).__name__}",
                )
            elif temperature < 0 or temperature > 2:
                result.add_error(
                    "llm",
                    "temperature",
                    f"Temperature must be between 0 and 2, got {temperature}",
                    suggestion="Set temperature between 0 and 2 (0=deterministic, 2=creative)",
                )

        # Max tokens
        max_tokens = llm.get("max_tokens")
        if max_tokens is not None:
            if model and model in self.MODEL_CONTEXT_LIMITS:
                context_limit = self.MODEL_CONTEXT_LIMITS[model]
                if max_tokens > context_limit:
                    result.add_error(
                        "llm",
                        "max_tokens",
                        f"max_tokens ({max_tokens}) exceeds model context limit ({context_limit})",
                        suggestion=f"Set max_tokens to at most {context_limit} for model {model}",
                    )
            if max_tokens < 1:
                result.add_error(
                    "llm",
                    "max_tokens",
                    f"max_tokens must be positive, got {max_tokens}",
                )

        # API key
        api_key = llm.get("api_key")
        if api_key:
            if provider == "openai":
                if not api_key.startswith("sk-"):
                    result.add_error(
                        "llm",
                        "api_key",
                        "Invalid OpenAI API key format",
                        suggestion="OpenAI API keys should start with 'sk-'",
                    )
            elif provider == "anthropic":
                if not re.match(r"^sk-ant-[a-z0-9]{95}$", api_key):
                    result.add_warning(
                        "llm",
                        "api_key",
                        "Invalid Anthropic API key format",
                        suggestion="Anthropic API keys should match format: sk-ant-api03-...",
                    )

        # Timeout
        timeout = llm.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, int) or timeout < 1:
                result.add_error(
                    "llm",
                    "timeout",
                    f"Timeout must be a positive integer (seconds), got {timeout}",
                    suggestion="Set timeout to at least 30 seconds",
                )

        # Max retries
        max_retries = llm.get("max_retries")
        if max_retries is not None:
            if not isinstance(max_retries, int) or max_retries < 0:
                result.add_error(
                    "llm",
                    "max_retries",
                    f"Max retries must be a non-negative integer, got {max_retries}",
                )

    def _validate_cache_config(self, result: ValidationResult) -> None:
        """Validate cache configuration."""
        cache = self.config.get("cache", {})

        # Enabled
        enabled = cache.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            result.add_error(
                "cache",
                "enabled",
                f"cache.enabled must be a boolean, got {type(enabled).__name__}",
            )

        # Max size
        max_size = cache.get("max_size_mb")
        if max_size is not None:
            if not isinstance(max_size, int) or max_size < 1:
                result.add_error(
                    "cache",
                    "max_size_mb",
                    f"Max cache size must be a positive integer (MB), got {max_size}",
                    suggestion="Set max_size_mb to at least 1",
                )
            else:
                # Check against available disk space
                try:
                    import shutil

                    free_space = shutil.disk_usage(os.getcwd()).free // (1024 ** 2)  # MB
                    if max_size > free_space * 0.9:  # Don't use more than 90% of free space
                        result.add_warning(
                            "cache",
                            "max_size_mb",
                            f"Cache size ({max_size}MB) exceeds available disk space ({free_space}MB)",
                            suggestion=f"Reduce cache size to {int(free_space * 0.5)}MB or less",
                        )
                except Exception:
                    pass

        # Cache directory
        cache_dir = cache.get("cache_dir")
        if cache_dir:
            path = Path(cache_dir)
            if path.exists() and not path.is_dir():
                result.add_error(
                    "cache",
                    "cache_dir",
                    f"Cache directory exists but is not a directory: {cache_dir}",
                    suggestion="Remove the file or specify a different directory",
                )
            elif path.exists() and not os.access(path, os.W_OK):
                result.add_error(
                    "cache",
                    "cache_dir",
                    f"Cache directory is not writable: {cache_dir}",
                    suggestion="Check permissions or specify a different directory",
                )

        # TTL
        ttl = cache.get("ttl_seconds")
        if ttl is not None:
            if not isinstance(ttl, int) or ttl < 0:
                result.add_error(
                    "cache",
                    "ttl_seconds",
                    f"TTL must be a non-negative integer (seconds), got {ttl}",
                )

        # Eviction policy
        policy = cache.get("eviction_policy")
        if policy:
            valid_policies = ["lru", "lfu", "fifo"]
            if policy not in valid_policies:
                result.add_error(
                    "cache",
                    "eviction_policy",
                    f"Invalid eviction policy: {policy}",
                    suggestion=f"Use one of: {', '.join(valid_policies)}",
                )

    def _validate_logging_config(self, result: ValidationResult) -> None:
        """Validate logging configuration."""
        logging_config = self.config.get("logging", {})

        # Level
        level = logging_config.get("level")
        if level:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if level.upper() not in valid_levels:
                result.add_error(
                    "logging",
                    "level",
                    f"Invalid log level: {level}",
                    suggestion=f"Use one of: {', '.join(valid_levels)}",
                )

        # Log file
        log_file = logging_config.get("file")
        if log_file:
            path = Path(log_file)
            if path.exists() and path.is_dir():
                result.add_error(
                    "logging",
                    "file",
                    f"Log file path is a directory: {log_file}",
                    suggestion="Specify a file path, not a directory",
                )

        # Max size
        max_size = logging_config.get("max_size_mb")
        if max_size is not None:
            if not isinstance(max_size, int) or max_size < 1:
                result.add_error(
                    "logging",
                    "max_size_mb",
                    f"Max log size must be a positive integer (MB), got {max_size}",
                )

        # Backup count
        backup_count = logging_config.get("backup_count")
        if backup_count is not None:
            if not isinstance(backup_count, int) or backup_count < 0:
                result.add_error(
                    "logging",
                    "backup_count",
                    f"Backup count must be a non-negative integer, got {backup_count}",
                )

        # Format
        log_format = logging_config.get("format")
        if log_format:
            valid_formats = ["json", "text"]
            if log_format not in valid_formats:
                result.add_error(
                    "logging",
                    "format",
                    f"Invalid log format: {log_format}",
                    suggestion=f"Use one of: {', '.join(valid_formats)}",
                )

    def _validate_telemetry_config(self, result: ValidationResult) -> None:
        """Validate telemetry configuration."""
        telemetry = self.config.get("telemetry", {})

        # Enabled
        enabled = telemetry.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            result.add_error(
                "telemetry",
                "enabled",
                f"telemetry.enabled must be a boolean, got {type(enabled).__name__}",
            )

        # Database path
        db_path = telemetry.get("telemetry_db")
        if db_path:
            if not isinstance(db_path, str) or len(db_path) > 255:
                result.add_error(
                    "telemetry",
                    "telemetry_db",
                    f"Invalid telemetry database path: {db_path}",
                    suggestion="Use a valid filename (max 255 characters)",
                )
            # Check directory exists
            path = Path(db_path)
            if path.parent != Path(".") and not path.parent.exists():
                result.add_warning(
                    "telemetry",
                    "telemetry_db",
                    f"Telemetry database directory does not exist: {path.parent}",
                    suggestion="Create the directory or use a relative path",
                )

    def _validate_checkpoint_config(self, result: ValidationResult) -> None:
        """Validate checkpoint configuration."""
        checkpoint = self.config.get("checkpoint", {})

        # Enabled
        enabled = checkpoint.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            result.add_error(
                "checkpoint",
                "enabled",
                f"checkpoint.enabled must be a boolean, got {type(enabled).__name__}",
            )

        # Max age
        max_age = checkpoint.get("max_age_hours")
        if max_age is not None:
            if not isinstance(max_age, int) or max_age < 1:
                result.add_error(
                    "checkpoint",
                    "max_age_hours",
                    f"Max checkpoint age must be at least 1 hour, got {max_age}",
                    suggestion="Set max_age_hours to at least 1",
                )

        # Max count
        max_count = checkpoint.get("max_count")
        if max_count is not None:
            if not isinstance(max_count, int) or max_count < 1:
                result.add_error(
                    "checkpoint",
                    "max_count",
                    f"Max checkpoint count must be at least 1, got {max_count}",
                    suggestion="Set max_count to at least 1",
                )

        # Checkpoint directory
        checkpoint_dir = checkpoint.get("checkpoint_dir")
        if checkpoint_dir:
            path = Path(checkpoint_dir)
            if path.exists() and not path.is_dir():
                result.add_error(
                    "checkpoint",
                    "checkpoint_dir",
                    f"Checkpoint directory exists but is not a directory: {checkpoint_dir}",
                )

    def _validate_session_config(self, result: ValidationResult) -> None:
        """Validate session configuration."""
        session = self.config.get("session", {})

        # Auto resume
        auto_resume = session.get("auto_resume")
        if auto_resume is not None and not isinstance(auto_resume, bool):
            result.add_error(
                "session",
                "auto_resume",
                f"session.auto_resume must be a boolean, got {type(auto_resume).__name__}",
            )

        # Session database
        session_db = session.get("session_db")
        if session_db:
            if not isinstance(session_db, str) or len(session_db) > 255:
                result.add_error(
                    "session",
                    "session_db",
                    f"Invalid session database path: {session_db}",
                    suggestion="Use a valid filename (max 255 characters)",
                )

    def _validate_custom_config(self, result: ValidationResult) -> None:
        """Validate custom configuration."""
        custom = self.config.get("custom", {})

        # Check for V5 custom settings
        v5_settings = [
            "adaptive_reasoning",
            "progress_tracking",
            "trap_detection",
        ]

        for setting in v5_settings:
            value = custom.get(setting)
            if value is not None and not isinstance(value, bool):
                result.add_warning(
                    "custom",
                    setting,
                    f"{setting} should be a boolean, got {type(value).__name__}",
                )

    def _check_conflicts(self, result: ValidationResult) -> None:
        """Check for conflicting configuration settings."""
        cache = self.config.get("cache", {})
        custom = self.config.get("custom", {})

        # Conflict 1: Cache disabled but adaptive reasoning enabled
        if not cache.get("enabled", True) and custom.get("adaptive_reasoning", False):
            result.add_warning(
                "cache",
                "enabled",
                "Cache is disabled but adaptive_reasoning is enabled",
                suggestion="Enable cache or disable adaptive_reasoning for better performance",
            )

        # Conflict 2: Token budget exceeds model context
        llm = self.config.get("llm", {})
        model = llm.get("model")
        max_tokens = llm.get("max_tokens")
        custom_token_budget = custom.get("token_budget")

        if model and model in self.MODEL_CONTEXT_LIMITS:
            context_limit = self.MODEL_CONTEXT_LIMITS[model]

            for budget_name, budget_value in [
                ("max_tokens", max_tokens),
                ("token_budget", custom_token_budget),
            ]:
                if budget_value and budget_value > context_limit:
                    result.add_error(
                        "llm" if budget_name == "max_tokens" else "custom",
                        budget_name,
                        f"{budget_name} ({budget_value}) exceeds model context limit ({context_limit})",
                        suggestion=f"Set {budget_name} to at most {context_limit} for model {model}",
                    )

        # Conflict 3: Cache size exceeds available disk space
        cache_size = cache.get("max_size_mb")
        if cache_size:
            try:
                import shutil

                free_space = shutil.disk_usage(os.getcwd()).free // (1024 ** 2)  # MB
                if cache_size > free_space:
                    result.add_error(
                        "cache",
                        "max_size_mb",
                        f"Cache size ({cache_size}MB) exceeds available disk space ({free_space}MB)",
                        suggestion=f"Reduce cache size to {int(free_space * 0.5)}MB or less",
                    )
            except Exception:
                pass

    def _check_deprecated_settings(self, result: ValidationResult) -> None:
        """Check for deprecated settings."""
        # Check top-level deprecated settings
        for setting, info in self.DEPRECATED_SETTINGS.items():
            if setting in self.config:
                result.add_warning(
                    "root",
                    setting,
                    f"Setting '{setting}' is deprecated since {info['deprecated_in']}",
                    suggestion=f"Migrate to '{info['migrate_to']}'",
                    deprecated_in=info["deprecated_in"],
                    migrate_to=info["migrate_to"],
                )

    def migrate_deprecated(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate deprecated settings to new format.

        Args:
            config: Configuration dictionary with potential deprecated settings

        Returns:
            Migrated configuration dictionary
        """
        migrated = config.copy()
        custom = migrated.setdefault("custom", {})

        migrations_performed = []

        for old_setting, info in self.DEPRECATED_SETTINGS.items():
            if old_setting in migrated:
                # Get the value
                value = migrated[old_setting]
                # Set in custom section
                new_setting = info["migrate_to"].split(".", 1)[1]
                custom[new_setting] = value
                # Remove old setting
                del migrated[old_setting]
                migrations_performed.append(
                    f"{old_setting} -> {info['migrate_to']}"
                )

        if migrations_performed:
            logger.info(f"Migrated deprecated settings: {', '.join(migrations_performed)}")

        return migrated


def validate_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Returns:
        ValidationResult with errors, warnings, and infos
    """
    validator = ConfigValidator(config)
    return validator.validate()


def validate_and_migrate(config: Dict[str, Any]) -> Tuple[Dict[str, Any], ValidationResult]:
    """
    Validate configuration and migrate deprecated settings.

    Args:
        config: Configuration dictionary to validate and migrate

    Returns:
        Tuple of (migrated_config, validation_result)
    """
    validator = ConfigValidator(config)

    # First, migrate deprecated settings
    migrated_config = validator.migrate_deprecated(config)

    # Then validate the migrated config
    validator = ConfigValidator(migrated_config)
    result = validator.validate()

    return migrated_config, result