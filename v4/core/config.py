"""
Configuration Management Module

This module handles loading, saving, and validating user preferences and configuration
for the L4D development platform. It supports:
- JSON/YAML configuration files (.l4_config)
- Configuration profiles (dev, prod, etc.)
- Schema validation with defaults
- Environment variable overrides
- Configuration migration on version changes
"""

import json
import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import yaml
import shutil

# Import configuration validator
from .config_validator import (
    validate_config,
    validate_and_migrate,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class ConfigProfile(str, Enum):
    """Configuration profile types."""

    DEV = "dev"
    PROD = "prod"
    TEST = "test"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openai"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3

    def __post_init__(self):
        """Validate configuration values."""
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError(
                f"Temperature must be between 0 and 2, got {self.temperature}"
            )
        if self.max_retries < 0:
            raise ValueError(
                f"Max retries must be non-negative, got {self.max_retries}"
            )


@dataclass
class CacheConfig:
    """Cache configuration."""

    enabled: bool = True
    max_size_mb: int = 100
    cache_dir: str = ".l4_cache"
    ttl_seconds: Optional[int] = None
    eviction_policy: str = "lru"  # lru, lfu, fifo

    def __post_init__(self):
        """Validate configuration values."""
        if self.max_size_mb < 1:
            raise ValueError(
                f"Max cache size must be at least 1MB, got {self.max_size_mb}"
            )
        if self.eviction_policy not in ["lru", "lfu", "fifo"]:
            raise ValueError(f"Invalid eviction policy: {self.eviction_policy}")


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    file: str = "l4.log"
    max_size_mb: int = 10
    backup_count: int = 5
    format: str = "json"
    console_output: bool = True

    def __post_init__(self):
        """Validate configuration values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.level}")
        if self.format not in ["json", "text"]:
            raise ValueError(f"Invalid log format: {self.format}")


@dataclass
class TelemetryConfig:
    """Telemetry configuration."""

    enabled: bool = True
    track_llm_calls: bool = True
    track_file_operations: bool = True
    track_resource_usage: bool = True
    telemetry_db: str = "telemetry.db"

    def __post_init__(self):
        """Validate configuration values."""
        # Basic validation - ensure DB path is reasonable
        if not self.telemetry_db or len(self.telemetry_db) > 255:
            raise ValueError(f"Invalid telemetry database path: {self.telemetry_db}")


@dataclass
class CheckpointConfig:
    """Checkpoint configuration."""

    enabled: bool = True
    auto_checkpoint: bool = True
    max_age_hours: int = 24
    max_count: int = 10
    checkpoint_dir: str = "checkpoints"

    def __post_init__(self):
        """Validate configuration values."""
        if self.max_age_hours < 1:
            raise ValueError(
                f"Max checkpoint age must be at least 1 hour, got {self.max_age_hours}"
            )
        if self.max_count < 1:
            raise ValueError(
                f"Max checkpoint count must be at least 1, got {self.max_count}"
            )


@dataclass
class SessionConfig:
    """Session configuration."""

    auto_resume: bool = True
    session_db: str = "sessions.db"
    analytics_enabled: bool = True

    def __post_init__(self):
        """Validate configuration values."""
        if not self.session_db or len(self.session_db) > 255:
            raise ValueError(f"Invalid session database path: {self.session_db}")


@dataclass
class AppConfig:
    """Complete application configuration."""

    version: str = "3.0.0"
    profile: str = "dev"
    llm: LLMConfig = field(default_factory=LLMConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    custom: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate complete configuration."""
        if self.profile not in [p.value for p in ConfigProfile]:
            logger.warning(f"Unknown profile: {self.profile}, using custom")


class SmartDefaults:
    """Smart default configuration based on auto-detection."""

    @staticmethod
    def detect_project_size() -> str:
        """
        Detect project size.

        Returns:
            Project size category: small, medium, or large
        """
        try:
            python_files = list(Path(".").rglob("*.py"))
            file_count = len(python_files)

            # Count lines of code
            total_lines = 0
            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        total_lines += sum(
                            1 for line in lines if line.strip() and not line.strip().startswith("#")
                        )
                except Exception:
                    pass

            # Classify project size
            if file_count < 50 and total_lines < 5000:
                return "small"
            elif file_count < 200 and total_lines < 20000:
                return "medium"
            else:
                return "large"
        except Exception as e:
            logger.warning(f"Failed to detect project size: {e}")
            return "medium"

    @staticmethod
    def get_available_disk_space() -> int:
        """
        Get available disk space.

        Returns:
            Disk space in GB
        """
        try:
            usage = shutil.disk_usage(os.getcwd())
            return usage.free // (1024 ** 3)
        except Exception as e:
            logger.warning(f"Failed to detect disk space: {e}")
            return 50  # Default assumption

    @staticmethod
    def get_defaults() -> Dict[str, Any]:
        """
        Get smart defaults based on system detection.

        Returns:
            Dictionary of smart default configuration
        """
        # Detect project size
        project_size = SmartDefaults.detect_project_size()
        logger.info(f"Detected project size: {project_size}")

        # Detect available disk space
        disk_space = SmartDefaults.get_available_disk_space()
        logger.info(f"Available disk space: {disk_space} GB")

        # Calculate cache size (project-based, limited by disk space)
        cache_size_map = {"small": 50, "medium": 100, "large": 200}
        base_cache_size = cache_size_map.get(project_size, 100)
        max_cache_from_disk = min(500, disk_space * 1024 // 10)  # Max 500MB or 10% of free space
        cache_size = min(base_cache_size, max_cache_from_disk)

        # Determine optimal depth
        max_depth = 3 if project_size != "large" else 2

        # Determine token budget
        token_budget_map = {"small": 2000, "medium": 3000, "large": 4000}
        token_budget = token_budget_map.get(project_size, 3000)

        # Determine LLM model (prefer cheaper models for smaller projects)
        llm_model = "gpt-3.5-turbo" if project_size == "small" else "gpt-4"

        logger.info(f"Smart defaults: cache={cache_size}MB, depth={max_depth}, tokens={token_budget}, model={llm_model}")

        return {
            "project_size": project_size,
            "cache_size_mb": cache_size,
            "max_depth": max_depth,
            "token_budget": token_budget,
            "llm_model": llm_model,
            "cache_enabled": True,
            "adaptive_reasoning": True,
            "progress_tracking": True,
            "trap_detection": True,
        }


class ConfigManager:
    """Manages configuration loading, saving, and validation."""

    DEFAULT_CONFIG_FILE = ".l4_config"
    CONFIG_VERSION = "5.0.0"

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            config_file: Path to configuration file. Defaults to .l4_config
        """
        self.config_file = Path(config_file or self.DEFAULT_CONFIG_FILE)
        self._config: Optional[AppConfig] = None
        self._profiles: Dict[str, Dict[str, Any]] = {}
        # Load profiles immediately on initialization
        self._load_profiles({})

    def load(self) -> AppConfig:
        """
        Load configuration from file, environment variables, and defaults.

        Returns:
            AppConfig: Loaded and validated configuration
        """
        if self._config is not None:
            return self._config

        # Start with defaults
        config_dict = self._get_default_config()

        # Load from file
        file_profile = None
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    file_config = self._parse_config_file(f)

                # Extract profile from file before merging
                file_profile = file_config.get("profile", "dev")

                # Load custom profiles from config file
                if "profiles" in file_config:
                    for name, profile_config in file_config["profiles"].items():
                        self._profiles[name] = profile_config

                # Check for version mismatch and migrate if needed
                file_version = file_config.get("version", "1.0.0")
                if file_version != self.CONFIG_VERSION:
                    logger.info(
                        f"Config version {file_version}, current {self.CONFIG_VERSION}"
                    )
                    file_config = self._migrate_config(file_version, file_config)

                # Apply profile first, then merge file config (file overrides profile)
                profile = file_profile or "dev"
                if profile in self._profiles:
                    profile_config = self._profiles[profile]
                    config_dict = self._merge_configs(config_dict, profile_config)

                # File config overrides profile settings
                config_dict = self._merge_configs(config_dict, file_config)

            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
                logger.info("Using default configuration")

        # If no file, apply default profile
        if file_profile is None:
            profile = config_dict.get("profile", "dev")
            if profile in self._profiles:
                profile_config = self._profiles[profile]
                config_dict = self._merge_configs(config_dict, profile_config)

        # Apply environment variable overrides (highest priority)
        config_dict = self._apply_env_overrides(config_dict)

        # Validate configuration using ConfigValidator
        validation_result = validate_config(config_dict)
        if not validation_result.is_valid:
            logger.error("Configuration validation failed:")
            for error in validation_result.errors:
                logger.error(f"  [{error.section}.{error.key}] {error.message}")
                if error.suggestion:
                    logger.error(f"    Suggestion: {error.suggestion}")
            logger.info("Resetting to defaults")
            self._config = AppConfig()
            return self._config

        # Log warnings
        for warning in validation_result.warnings:
            logger.warning(
                f"[{warning.section}.{warning.key}] {warning.message}"
            )
            if warning.suggestion:
                logger.warning(f"  Suggestion: {warning.suggestion}")

        # Validate and create AppConfig object
        try:
            self._config = self._create_config_from_dict(config_dict)
            profile = config_dict.get("profile", "dev")
            logger.info(f"Configuration loaded successfully (profile: {profile})")
            return self._config
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            logger.info("Resetting to defaults")
            self._config = AppConfig()
            return self._config

    def save(self, config: Optional[AppConfig] = None) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration to save. If None, saves current config.
        """
        config_to_save = config or self._config or self.load()

        try:
            config_dict = self._config_to_dict(config_to_save)

            # Create parent directories if needed
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # Save as JSON (could also support YAML)
            with open(self.config_file, "w") as f:
                json.dump(config_dict, f, indent=2, default=str)

            logger.info(f"Configuration saved to {self.config_file}")
            self._config = config_to_save

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def get_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Get a specific configuration profile.

        Args:
            profile_name: Name of the profile

        Returns:
            Dict containing profile configuration
        """
        if profile_name not in self._profiles:
            raise ValueError(f"Profile '{profile_name}' not found")
        return self._profiles[profile_name].copy()

    def add_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """
        Add or update a configuration profile.

        Args:
            profile_name: Name of the profile
            config: Configuration dictionary for the profile
        """
        self._profiles[profile_name] = config
        logger.info(f"Profile '{profile_name}' added/updated")

    def reset_to_defaults(self) -> AppConfig:
        """
        Reset configuration to defaults and delete config file.

        Returns:
            AppConfig: Default configuration
        """
        config_path = self.config_file
        # Clear cached config
        self._config = None

        if config_path.exists():
            config_path.unlink()
            logger.info(f"Configuration file {config_path} deleted")

        # Load fresh defaults
        self._config = AppConfig()
        return self._config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration as dictionary with smart defaults."""
        # Apply smart defaults
        smart_defaults = SmartDefaults.get_defaults()

        # Build base config with smart defaults applied
        base_config = {
            "version": self.CONFIG_VERSION,
            "profile": "balanced",  # Default to balanced profile
            "llm": asdict(LLMConfig(model=smart_defaults["llm_model"])),
            "cache": asdict(
                CacheConfig(
                    enabled=smart_defaults["cache_enabled"],
                    max_size_mb=smart_defaults["cache_size_mb"],
                )
            ),
            "logging": asdict(LoggingConfig()),
            "telemetry": asdict(TelemetryConfig()),
            "checkpoint": asdict(CheckpointConfig()),
            "session": asdict(SessionConfig()),
            "custom": {
                "project_size": smart_defaults["project_size"],
                "adaptive_reasoning": smart_defaults["adaptive_reasoning"],
                "progress_tracking": smart_defaults["progress_tracking"],
                "trap_detection": smart_defaults["trap_detection"],
            },
        }

        logger.info("Applied smart defaults based on auto-detection")
        return base_config

    def _parse_config_file(self, file_handle) -> Dict[str, Any]:
        """Parse configuration file (JSON or YAML)."""
        content = file_handle.read()

        try:
            # Try JSON first
            return json.loads(content)
        except json.JSONDecodeError:
            # Try YAML
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"Failed to parse config as JSON or YAML: {e}")

    def _merge_configs(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            "L4_LLM_PROVIDER": ("llm", "provider"),
            "L4_LLM_MODEL": ("llm", "model"),
            "L4_LLM_TEMPERATURE": ("llm", "temperature"),
            "L4_LLM_API_KEY": ("llm", "api_key"),
            "L4_CACHE_ENABLED": ("cache", "enabled"),
            "L4_CACHE_SIZE_MB": ("cache", "max_size_mb"),
            "L4_CACHE_DIR": ("cache", "cache_dir"),
            "L4_LOG_LEVEL": ("logging", "level"),
            "L4_LOG_FILE": ("logging", "file"),
            "L4_TELEMETRY_ENABLED": ("telemetry", "enabled"),
            "L4_CHECKPOINT_ENABLED": ("checkpoint", "enabled"),
            "L4_CHECKPOINT_MAX_AGE": ("checkpoint", "max_age_hours"),
            "L4_SESSION_AUTO_RESUME": ("session", "auto_resume"),
        }

        for env_var, (section, key) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if value.lower() in ["true", "false"]:
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)

                if section in config:
                    config[section][key] = value
                    logger.debug(f"Applied env override: {env_var}={value}")

        return config

    def _load_profiles(self, config: Dict[str, Any]) -> None:
        """Load predefined profiles from configuration."""
        # Only load if not already loaded
        if not self._profiles:
            self._profiles = {
                # V5 Built-in Profiles
                "minimal": {
                    "description": "Minimal configuration for small projects",
                    "llm": {"model": "gpt-3.5-turbo", "temperature": 0.7},
                    "cache": {"enabled": True, "max_size_mb": 50},
                    "logging": {"level": "INFO"},
                    "telemetry": {"enabled": True},
                    "custom": {
                        "adaptive_reasoning": False,
                        "progress_tracking": False,
                        "trap_detection": False,
                    },
                },
                "balanced": {
                    "description": "Balanced configuration for most use cases",
                    "llm": {"model": "gpt-4", "temperature": 0.7},
                    "cache": {"enabled": True, "max_size_mb": 100},
                    "logging": {"level": "INFO"},
                    "telemetry": {"enabled": True},
                    "custom": {
                        "adaptive_reasoning": True,
                        "progress_tracking": True,
                        "trap_detection": True,
                    },
                },
                "max": {
                    "description": "Maximum features for large projects",
                    "llm": {"model": "gpt-4", "temperature": 0.5},
                    "cache": {"enabled": True, "max_size_mb": 500},
                    "logging": {"level": "DEBUG"},
                    "telemetry": {"enabled": True},
                    "custom": {
                        "adaptive_reasoning": True,
                        "progress_tracking": True,
                        "trap_detection": True,
                    },
                },
                # Legacy V3/V4 Profiles
                "dev": {
                    "llm": {"temperature": 0.7},
                    "cache": {"enabled": True},
                    "logging": {"level": "DEBUG"},
                    "telemetry": {"enabled": True},
                },
                "prod": {
                    "llm": {"temperature": 0.5},
                    "cache": {"enabled": True, "max_size_mb": 200},
                    "logging": {"level": "INFO"},
                    "telemetry": {"enabled": True},
                },
                "test": {
                    "llm": {"temperature": 0.5},
                    "cache": {"enabled": False},
                    "logging": {"level": "DEBUG"},
                    "telemetry": {"enabled": False},
                },
            }

        # Load custom profiles from config if present
        if "profiles" in config and config["profiles"]:
            for name, profile_config in config["profiles"].items():
                self._profiles[name] = profile_config

    def _migrate_config(
        self, from_version: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Migrate configuration from an older version."""
        logger.info(f"Migrating configuration from version {from_version}")

        # Add migration logic here as needed
        # Example: if migrating from 2.0.0 to 3.0.0
        if from_version.startswith("2."):
            # Add new V3 sections with defaults
            if "telemetry" not in config:
                config["telemetry"] = asdict(TelemetryConfig())
            if "checkpoint" not in config:
                config["checkpoint"] = asdict(CheckpointConfig())
            if "session" not in config:
                config["session"] = asdict(SessionConfig())

        # Update version
        config["version"] = self.CONFIG_VERSION

        logger.info(f"Configuration migrated to version {self.CONFIG_VERSION}")
        return config

    def _create_config_from_dict(self, config_dict: Dict[str, Any]) -> AppConfig:
        """Create AppConfig object from dictionary with validation."""
        try:
            return AppConfig(
                version=config_dict.get("version", self.CONFIG_VERSION),
                profile=config_dict.get("profile", "dev"),
                llm=LLMConfig(**config_dict.get("llm", {})),
                cache=CacheConfig(**config_dict.get("cache", {})),
                logging=LoggingConfig(**config_dict.get("logging", {})),
                telemetry=TelemetryConfig(**config_dict.get("telemetry", {})),
                checkpoint=CheckpointConfig(**config_dict.get("checkpoint", {})),
                session=SessionConfig(**config_dict.get("session", {})),
                custom=config_dict.get("custom", {}),
            )
        except TypeError as e:
            raise ValueError(f"Invalid configuration structure: {e}")

    def _config_to_dict(self, config: AppConfig) -> Dict[str, Any]:
        """Convert AppConfig object to dictionary."""
        return {
            "version": config.version,
            "profile": config.profile,
            "llm": asdict(config.llm),
            "cache": asdict(config.cache),
            "logging": asdict(config.logging),
            "telemetry": asdict(config.telemetry),
            "checkpoint": asdict(config.checkpoint),
            "session": asdict(config.session),
            "custom": config.custom,
        }


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config(config_file: Optional[str] = None) -> AppConfig:
    """
    Get global configuration instance.

    Args:
        config_file: Optional path to configuration file

    Returns:
        AppConfig: Current configuration
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager.load()


def save_config(config: AppConfig) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    _config_manager.save(config)


def reset_config() -> AppConfig:
    """
    Reset configuration to defaults.

    Returns:
        AppConfig: Default configuration
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.reset_to_defaults()
