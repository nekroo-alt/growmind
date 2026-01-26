"""
Tests for Configuration Management Module

Tests configuration loading, saving, validation, profiles,
environment variable overrides, and migration.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from v5.core import (
    AppConfig,
    LLMConfig,
    CacheConfig,
    LoggingConfig,
    TelemetryConfig,
    CheckpointConfig,
    SessionConfig,
    ConfigManager,
    ConfigProfile,
    get_config,
    save_config,
    reset_config,
)


class TestLLMConfig:
    """Test LLMConfig validation."""

    def test_default_values(self):
        """Test default LLM configuration values."""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens is None
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_valid_temperature(self):
        """Test valid temperature values."""
        config = LLMConfig(temperature=0.5)
        assert config.temperature == 0.5

        config = LLMConfig(temperature=1.5)
        assert config.temperature == 1.5

    def test_invalid_temperature(self):
        """Test invalid temperature raises error."""
        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            LLMConfig(temperature=-0.1)

        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            LLMConfig(temperature=2.1)

    def test_negative_max_retries(self):
        """Test negative max_retries raises error."""
        with pytest.raises(ValueError, match="Max retries must be non-negative"):
            LLMConfig(max_retries=-1)


class TestCacheConfig:
    """Test CacheConfig validation."""

    def test_default_values(self):
        """Test default cache configuration values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.max_size_mb == 100
        assert config.cache_dir == ".l4_cache"
        assert config.eviction_policy == "lru"

    def test_valid_eviction_policies(self):
        """Test valid eviction policies."""
        for policy in ["lru", "lfu", "fifo"]:
            config = CacheConfig(eviction_policy=policy)
            assert config.eviction_policy == policy

    def test_invalid_eviction_policy(self):
        """Test invalid eviction policy raises error."""
        with pytest.raises(ValueError, match="Invalid eviction policy"):
            CacheConfig(eviction_policy="invalid")

    def test_invalid_max_size(self):
        """Test invalid max_size_mb raises error."""
        with pytest.raises(ValueError, match="Max cache size must be at least 1MB"):
            CacheConfig(max_size_mb=0)


class TestLoggingConfig:
    """Test LoggingConfig validation."""

    def test_default_values(self):
        """Test default logging configuration values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file == "l4.log"
        assert config.max_size_mb == 10
        assert config.backup_count == 5
        assert config.format == "json"
        assert config.console_output is True

    def test_valid_log_levels(self):
        """Test valid log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_invalid_log_level(self):
        """Test invalid log level raises error."""
        with pytest.raises(ValueError, match="Invalid log level"):
            LoggingConfig(level="INVALID")

    def test_invalid_log_format(self):
        """Test invalid log format raises error."""
        with pytest.raises(ValueError, match="Invalid log format"):
            LoggingConfig(format="invalid")


class TestTelemetryConfig:
    """Test TelemetryConfig validation."""

    def test_default_values(self):
        """Test default telemetry configuration values."""
        config = TelemetryConfig()
        assert config.enabled is True
        assert config.track_llm_calls is True
        assert config.track_file_operations is True
        assert config.track_resource_usage is True
        assert config.telemetry_db == "telemetry.db"

    def test_invalid_db_path(self):
        """Test invalid database path raises error."""
        with pytest.raises(ValueError, match="Invalid telemetry database path"):
            TelemetryConfig(telemetry_db="")

        with pytest.raises(ValueError, match="Invalid telemetry database path"):
            TelemetryConfig(telemetry_db="a" * 256)


class TestCheckpointConfig:
    """Test CheckpointConfig validation."""

    def test_default_values(self):
        """Test default checkpoint configuration values."""
        config = CheckpointConfig()
        assert config.enabled is True
        assert config.auto_checkpoint is True
        assert config.max_age_hours == 24
        assert config.max_count == 10
        assert config.checkpoint_dir == "checkpoints"

    def test_invalid_max_age(self):
        """Test invalid max_age_hours raises error."""
        with pytest.raises(
            ValueError, match="Max checkpoint age must be at least 1 hour"
        ):
            CheckpointConfig(max_age_hours=0)

    def test_invalid_max_count(self):
        """Test invalid max_count raises error."""
        with pytest.raises(ValueError, match="Max checkpoint count must be at least 1"):
            CheckpointConfig(max_count=0)


class TestSessionConfig:
    """Test SessionConfig validation."""

    def test_default_values(self):
        """Test default session configuration values."""
        config = SessionConfig()
        assert config.auto_resume is True
        assert config.session_db == "sessions.db"
        assert config.analytics_enabled is True

    def test_invalid_db_path(self):
        """Test invalid database path raises error."""
        with pytest.raises(ValueError, match="Invalid session database path"):
            SessionConfig(session_db="")


class TestAppConfig:
    """Test AppConfig validation."""

    def test_default_values(self):
        """Test default application configuration values."""
        config = AppConfig()
        assert config.version == "3.0.0"
        assert config.profile == "dev"
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.telemetry, TelemetryConfig)
        assert isinstance(config.checkpoint, CheckpointConfig)
        assert isinstance(config.session, SessionConfig)
        assert config.custom == {}

    def test_unknown_profile_warning(self, caplog):
        """Test unknown profile logs warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            config = AppConfig(profile="unknown")
            assert config.profile == "unknown"
            assert "Unknown profile" in caplog.text


class TestConfigManager:
    """Test ConfigManager functionality."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_file = f.name
        yield config_file
        # Cleanup
        if os.path.exists(config_file):
            os.unlink(config_file)

    @pytest.fixture
    def config_manager(self, temp_config_file):
        """Create a ConfigManager with temp file."""
        # Reset global instance
        global _config_manager
        import v2.core.config

        v2.core.config._config_manager = None
        yield ConfigManager(temp_config_file)
        # Cleanup
        v2.core.config._config_manager = None

    def test_load_default_config(self, config_manager):
        """Test loading default configuration."""
        config = config_manager.load()
        assert isinstance(config, AppConfig)
        assert config.version == "3.0.0"
        assert config.profile == "dev"

    def test_load_from_file(self, config_manager, temp_config_file):
        """Test loading configuration from file."""
        # Create a config file
        test_config = {
            "version": "3.0.0",
            "profile": "prod",
            "llm": {"provider": "anthropic", "model": "claude-3"},
            "cache": {"enabled": False},
        }

        with open(temp_config_file, "w") as f:
            json.dump(test_config, f)

        config = config_manager.load()
        assert config.profile == "prod"
        assert config.llm.provider == "anthropic"
        assert config.llm.model == "claude-3"
        assert config.cache.enabled is False

    def test_save_config(self, config_manager, temp_config_file):
        """Test saving configuration to file."""
        config = AppConfig(profile="prod", llm=LLMConfig(provider="anthropic"))

        config_manager.save(config)

        # Verify file was created
        assert os.path.exists(temp_config_file)

        # Load and verify
        with open(temp_config_file, "r") as f:
            saved_config = json.load(f)

        assert saved_config["profile"] == "prod"
        assert saved_config["llm"]["provider"] == "anthropic"

    def test_env_variable_overrides(self, config_manager, monkeypatch):
        """Test environment variable overrides."""
        monkeypatch.setenv("L4_LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("L4_LLM_TEMPERATURE", "0.5")
        monkeypatch.setenv("L4_CACHE_ENABLED", "false")
        monkeypatch.setenv("L4_LOG_LEVEL", "DEBUG")

        config = config_manager.load()

        assert config.llm.provider == "anthropic"
        assert config.llm.temperature == 0.5
        assert config.cache.enabled is False
        assert config.logging.level == "DEBUG"

        # Cleanup
        monkeypatch.delenv("L4_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("L4_LLM_TEMPERATURE", raising=False)
        monkeypatch.delenv("L4_CACHE_ENABLED", raising=False)
        monkeypatch.delenv("L4_LOG_LEVEL", raising=False)

    def test_get_profile(self, config_manager):
        """Test getting configuration profiles."""
        config_manager.load()  # Load to initialize profiles

        dev_profile = config_manager.get_profile("dev")
        assert dev_profile["logging"]["level"] == "DEBUG"

        prod_profile = config_manager.get_profile("prod")
        assert prod_profile["logging"]["level"] == "INFO"
        assert prod_profile["cache"]["max_size_mb"] == 200

    def test_add_profile(self, config_manager):
        """Test adding custom profile."""
        config_manager.load()

        custom_config = {"llm": {"temperature": 0.9}, "cache": {"enabled": False}}

        config_manager.add_profile("custom", custom_config)

        profile = config_manager.get_profile("custom")
        assert profile["llm"]["temperature"] == 0.9
        assert profile["cache"]["enabled"] is False

    def test_reset_to_defaults(self, config_manager, temp_config_file):
        """Test resetting configuration to defaults."""
        # Create a config file
        test_config = {
            "version": "3.0.0",
            "profile": "prod",
            "llm": {"provider": "anthropic"},
        }

        with open(temp_config_file, "w") as f:
            json.dump(test_config, f)

        config = config_manager.load()
        assert config.profile == "prod"

        # Reset
        reset_config = config_manager.reset_to_defaults()
        assert reset_config.profile == "dev"
        assert not os.path.exists(temp_config_file)

    def test_migration_from_v2(self, config_manager, temp_config_file):
        """Test configuration migration from V2 to V3."""
        # Create a V2-style config file
        v2_config = {
            "version": "2.0.0",
            "profile": "dev",
            "llm": {"provider": "openai"},
            "cache": {"enabled": True},
        }

        with open(temp_config_file, "w") as f:
            json.dump(v2_config, f)

        config = config_manager.load()

        # Verify migration added V3 sections
        assert config.version == "3.0.0"
        assert isinstance(config.telemetry, TelemetryConfig)
        assert isinstance(config.checkpoint, CheckpointConfig)
        assert isinstance(config.session, SessionConfig)

    def test_invalid_config_file(self, config_manager, temp_config_file, caplog):
        """Test handling of invalid config file."""
        # Create an invalid config file
        with open(temp_config_file, "w") as f:
            f.write("invalid json {{{")

        import logging

        with caplog.at_level(logging.ERROR):
            config = config_manager.load()

        # Should fall back to defaults
        assert isinstance(config, AppConfig)
        assert "Failed to load config file" in caplog.text


class TestGlobalFunctions:
    """Test global convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_global(self):
        """Reset global config manager before/after each test."""
        import v2.core.config

        v2.core.config._config_manager = None
        yield
        v2.core.config._config_manager = None

    def test_get_config(self):
        """Test get_config function."""
        config = get_config()
        assert isinstance(config, AppConfig)
        assert config.version == "3.0.0"

    def test_save_config(self):
        """Test save_config function."""
        config = AppConfig(profile="test")
        save_config(config)

        # Verify config was saved
        config2 = get_config()
        assert config2.profile == "test"

        # Cleanup
        if os.path.exists(ConfigManager.DEFAULT_CONFIG_FILE):
            os.unlink(ConfigManager.DEFAULT_CONFIG_FILE)

    def test_reset_config(self):
        """Test reset_config function."""
        # Set a custom config
        config = AppConfig(profile="prod")
        save_config(config)

        assert get_config().profile == "prod"

        # Reset
        reset_config()

        assert get_config().profile == "dev"


class TestConfigurationScenarios:
    """Test real-world configuration scenarios."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Cleanup after tests."""
        yield
        if os.path.exists(ConfigManager.DEFAULT_CONFIG_FILE):
            os.unlink(ConfigManager.DEFAULT_CONFIG_FILE)

    def test_dev_profile_scenario(self):
        """Test development profile scenario."""
        manager = ConfigManager()
        config = manager.load()

        assert config.profile == "dev"
        assert config.logging.level == "DEBUG"
        assert config.cache.enabled is True
        assert config.telemetry.enabled is True

    def test_prod_profile_scenario(self):
        """Test production profile scenario."""
        manager = ConfigManager()
        manager._profiles["prod"] = manager._profiles["prod"]
        manager._config = AppConfig(profile="prod")
        profile_config = manager.get_profile("prod")

        assert profile_config["logging"]["level"] == "INFO"
        assert profile_config["cache"]["max_size_mb"] == 200

    def test_test_profile_scenario(self):
        """Test test profile scenario."""
        manager = ConfigManager()
        profile_config = manager.get_profile("test")

        assert profile_config["cache"]["enabled"] is False
        assert profile_config["telemetry"]["enabled"] is False
        assert profile_config["logging"]["level"] == "DEBUG"

    def test_custom_profile_scenario(self):
        """Test custom profile scenario."""
        manager = ConfigManager()

        custom_config = {
            "llm": {
                "provider": "custom_llm",
                "model": "custom_model",
                "temperature": 0.3,
            },
            "cache": {"enabled": True, "max_size_mb": 500},
        }

        manager.add_profile("my_custom", custom_config)
        profile = manager.get_profile("my_custom")

        assert profile["llm"]["provider"] == "custom_llm"
        assert profile["cache"]["max_size_mb"] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
