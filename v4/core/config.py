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
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import yaml

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


class ConfigManager:
    """Manages configuration loading, saving, and validation."""

    DEFAULT_CONFIG_FILE = ".l4_config"
    CONFIG_VERSION = "3.0.0"

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
        """Get default configuration as dictionary."""
        return {
            "version": self.CONFIG_VERSION,
            "profile": "dev",
            "llm": asdict(LLMConfig()),
            "cache": asdict(CacheConfig()),
            "logging": asdict(LoggingConfig()),
            "telemetry": asdict(TelemetryConfig()),
            "checkpoint": asdict(CheckpointConfig()),
            "session": asdict(SessionConfig()),
            "custom": {},
        }

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
