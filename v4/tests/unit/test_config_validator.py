"""
Unit tests for Configuration Validator Module

Tests configuration validation, error detection, conflict detection,
and migration of deprecated settings.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from v4.core.config_validator import (
    ConfigValidator,
    ValidationError,
    ValidationResult,
    ValidationErrorSeverity,
    validate_config,
    validate_and_migrate,
)


class TestValidationError(unittest.TestCase):
    """Test ValidationError dataclass."""

    def test_error_creation(self):
        """Test creating a validation error."""
        error = ValidationError(
            severity=ValidationErrorSeverity.ERROR,
            section="llm",
            key="temperature",
            message="Temperature must be between 0 and 2",
            suggestion="Set temperature between 0 and 2",
        )

        self.assertEqual(error.severity, ValidationErrorSeverity.ERROR)
        self.assertEqual(error.section, "llm")
        self.assertEqual(error.key, "temperature")
        self.assertEqual(error.message, "Temperature must be between 0 and 2")
        self.assertEqual(error.suggestion, "Set temperature between 0 and 2")


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True)

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
        self.assertEqual(len(result.infos), 0)

    def test_add_error(self):
        """Test adding an error to result."""
        result = ValidationResult(is_valid=True)
        result.add_error("llm", "temperature", "Invalid temperature")

        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].section, "llm")
        self.assertEqual(result.errors[0].key, "temperature")

    def test_add_warning(self):
        """Test adding a warning to result."""
        result = ValidationResult(is_valid=True)
        result.add_warning("cache", "max_size_mb", "Cache size too large")

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].section, "cache")

    def test_add_info(self):
        """Test adding an info message to result."""
        result = ValidationResult(is_valid=True)
        result.add_info("llm", "model", "Using GPT-4 model")

        self.assertEqual(len(result.infos), 1)
        self.assertEqual(result.infos[0].section, "llm")

    def test_get_summary(self):
        """Test generating summary from validation result."""
        result = ValidationResult(is_valid=False)
        result.add_error("llm", "temperature", "Invalid temperature", "Fix it")
        result.add_warning("cache", "max_size_mb", "Cache size large")
        result.add_info("llm", "model", "Using GPT-4")

        summary = result.get_summary()

        self.assertIn("INVALID", summary)
        self.assertIn("Errors (1)", summary)
        self.assertIn("Warnings (1)", summary)
        self.assertIn("[llm.temperature]", summary)
        self.assertIn("Suggestion: Fix it", summary)


class TestLLMConfigValidation(unittest.TestCase):
    """Test LLM configuration validation."""

    def test_valid_llm_config(self):
        """Test valid LLM configuration."""
        config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4000,
                "api_key": "sk-test123",
                "timeout": 30,
                "max_retries": 3,
            }
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        # Check no errors in llm section
        llm_errors = [e for e in result.errors if e.section == "llm"]
        self.assertEqual(len(llm_errors), 0)

    def test_invalid_provider(self):
        """Test invalid LLM provider."""
        config = {"llm": {"provider": "invalid_provider"}}

        validator = ConfigValidator(config)
        result = validator.validate()

        llm_errors = [e for e in result.errors if e.section == "llm" and e.key == "provider"]
        self.assertGreater(len(llm_errors), 0)
        self.assertIn("Invalid provider", llm_errors[0].message)

    def test_invalid_temperature_negative(self):
        """Test temperature below 0."""
        config = {"llm": {"temperature": -0.5}}

        validator = ConfigValidator(config)
        result = validator.validate()

        temp_errors = [
            e for e in result.errors if e.section == "llm" and e.key == "temperature"
        ]
        self.assertGreater(len(temp_errors), 0)
        self.assertIn("between 0 and 2", temp_errors[0].message)

    def test_invalid_temperature_too_high(self):
        """Test temperature above 2."""
        config = {"llm": {"temperature": 3.0}}

        validator = ConfigValidator(config)
        result = validator.validate()

        temp_errors = [
            e for e in result.errors if e.section == "llm" and e.key == "temperature"
        ]
        self.assertGreater(len(temp_errors), 0)

    def test_max_tokens_exceeds_context(self):
        """Test max_tokens exceeds model context limit."""
        config = {
            "llm": {"model": "gpt-3.5-turbo", "max_tokens": 10000}
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        token_errors = [
            e for e in result.errors
            if e.section == "llm" and e.key == "max_tokens"
        ]
        self.assertGreater(len(token_errors), 0)
        self.assertIn("exceeds model context limit", token_errors[0].message)

    def test_invalid_openai_api_key(self):
        """Test invalid OpenAI API key format."""
        config = {"llm": {"provider": "openai", "api_key": "invalid_key"}}

        validator = ConfigValidator(config)
        result = validator.validate()

        key_errors = [
            e for e in result.errors if e.section == "llm" and e.key == "api_key"
        ]
        self.assertGreater(len(key_errors), 0)
        self.assertIn("Invalid OpenAI API key format", key_errors[0].message)

    def test_invalid_timeout(self):
        """Test invalid timeout value."""
        config = {"llm": {"timeout": 0}}

        validator = ConfigValidator(config)
        result = validator.validate()

        timeout_errors = [
            e for e in result.errors if e.section == "llm" and e.key == "timeout"
        ]
        self.assertGreater(len(timeout_errors), 0)

    def test_invalid_max_retries(self):
        """Test invalid max_retries value."""
        config = {"llm": {"max_retries": -1}}

        validator = ConfigValidator(config)
        result = validator.validate()

        retry_errors = [
            e for e in result.errors if e.section == "llm" and e.key == "max_retries"
        ]
        self.assertGreater(len(retry_errors), 0)


class TestCacheConfigValidation(unittest.TestCase):
    """Test cache configuration validation."""

    def test_valid_cache_config(self):
        """Test valid cache configuration."""
        config = {
            "cache": {
                "enabled": True,
                "max_size_mb": 100,
                "cache_dir": ".l4_cache",
                "ttl_seconds": 3600,
                "eviction_policy": "lru",
            }
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        cache_errors = [e for e in result.errors if e.section == "cache"]
        self.assertEqual(len(cache_errors), 0)

    def test_invalid_max_size_mb(self):
        """Test invalid cache max size."""
        config = {"cache": {"max_size_mb": 0}}

        validator = ConfigValidator(config)
        result = validator.validate()

        size_errors = [
            e for e in result.errors if e.section == "cache" and e.key == "max_size_mb"
        ]
        self.assertGreater(len(size_errors), 0)

    def test_cache_dir_is_file(self):
        """Test cache directory path pointing to a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            tmp_file_path = tmp_file.name

        try:
            config = {"cache": {"cache_dir": tmp_file_path}}

            validator = ConfigValidator(config)
            result = validator.validate()

            dir_errors = [
                e for e in result.errors if e.section == "cache" and e.key == "cache_dir"
            ]
            self.assertGreater(len(dir_errors), 0)
            self.assertIn("not a directory", dir_errors[0].message)
        finally:
            Path(tmp_file_path).unlink()

    def test_invalid_eviction_policy(self):
        """Test invalid eviction policy."""
        config = {"cache": {"eviction_policy": "invalid_policy"}}

        validator = ConfigValidator(config)
        result = validator.validate()

        policy_errors = [
            e for e in result.errors
            if e.section == "cache" and e.key == "eviction_policy"
        ]
        self.assertGreater(len(policy_errors), 0)

    def test_invalid_ttl_seconds(self):
        """Test invalid TTL value."""
        config = {"cache": {"ttl_seconds": -1}}

        validator = ConfigValidator(config)
        result = validator.validate()

        ttl_errors = [
            e for e in result.errors if e.section == "cache" and e.key == "ttl_seconds"
        ]
        self.assertGreater(len(ttl_errors), 0)


class TestLoggingConfigValidation(unittest.TestCase):
    """Test logging configuration validation."""

    def test_valid_logging_config(self):
        """Test valid logging configuration."""
        config = {
            "logging": {
                "level": "INFO",
                "file": "l4.log",
                "max_size_mb": 10,
                "backup_count": 5,
                "format": "json",
            }
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        logging_errors = [e for e in result.errors if e.section == "logging"]
        self.assertEqual(len(logging_errors), 0)

    def test_invalid_log_level(self):
        """Test invalid log level."""
        config = {"logging": {"level": "INVALID"}}

        validator = ConfigValidator(config)
        result = validator.validate()

        level_errors = [
            e for e in result.errors if e.section == "logging" and e.key == "level"
        ]
        self.assertGreater(len(level_errors), 0)

    def test_invalid_log_format(self):
        """Test invalid log format."""
        config = {"logging": {"format": "invalid_format"}}

        validator = ConfigValidator(config)
        result = validator.validate()

        format_errors = [
            e for e in result.errors if e.section == "logging" and e.key == "format"
        ]
        self.assertGreater(len(format_errors), 0)

    def test_invalid_max_size_mb(self):
        """Test invalid max size."""
        config = {"logging": {"max_size_mb": 0}}

        validator = ConfigValidator(config)
        result = validator.validate()

        size_errors = [
            e for e in result.errors if e.section == "logging" and e.key == "max_size_mb"
        ]
        self.assertGreater(len(size_errors), 0)

    def test_invalid_backup_count(self):
        """Test invalid backup count."""
        config = {"logging": {"backup_count": -1}}

        validator = ConfigValidator(config)
        result = validator.validate()

        backup_errors = [
            e for e in result.errors if e.section == "logging" and e.key == "backup_count"
        ]
        self.assertGreater(len(backup_errors), 0)


class TestTelemetryConfigValidation(unittest.TestCase):
    """Test telemetry configuration validation."""

    def test_valid_telemetry_config(self):
        """Test valid telemetry configuration."""
        config = {
            "telemetry": {
                "enabled": True,
                "track_llm_calls": True,
                "telemetry_db": "telemetry.db",
            }
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        telemetry_errors = [e for e in result.errors if e.section == "telemetry"]
        self.assertEqual(len(telemetry_errors), 0)

    def test_invalid_telemetry_db_too_long(self):
        """Test telemetry db path too long."""
        config = {"telemetry": {"telemetry_db": "a" * 300}}

        validator = ConfigValidator(config)
        result = validator.validate()

        db_errors = [
            e for e in result.errors
            if e.section == "telemetry" and e.key == "telemetry_db"
        ]
        self.assertGreater(len(db_errors), 0)


class TestCheckpointConfigValidation(unittest.TestCase):
    """Test checkpoint configuration validation."""

    def test_valid_checkpoint_config(self):
        """Test valid checkpoint configuration."""
        config = {
            "checkpoint": {
                "enabled": True,
                "max_age_hours": 24,
                "max_count": 10,
                "checkpoint_dir": "checkpoints",
            }
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        checkpoint_errors = [e for e in result.errors if e.section == "checkpoint"]
        self.assertEqual(len(checkpoint_errors), 0)

    def test_invalid_max_age_hours(self):
        """Test invalid max age hours."""
        config = {"checkpoint": {"max_age_hours": 0}}

        validator = ConfigValidator(config)
        result = validator.validate()

        age_errors = [
            e for e in result.errors
            if e.section == "checkpoint" and e.key == "max_age_hours"
        ]
        self.assertGreater(len(age_errors), 0)

    def test_invalid_max_count(self):
        """Test invalid max count."""
        config = {"checkpoint": {"max_count": 0}}

        validator = ConfigValidator(config)
        result = validator.validate()

        count_errors = [
            e for e in result.errors if e.section == "checkpoint" and e.key == "max_count"
        ]
        self.assertGreater(len(count_errors), 0)


class TestSessionConfigValidation(unittest.TestCase):
    """Test session configuration validation."""

    def test_valid_session_config(self):
        """Test valid session configuration."""
        config = {
            "session": {
                "auto_resume": True,
                "session_db": "sessions.db",
                "analytics_enabled": True,
            }
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        session_errors = [e for e in result.errors if e.section == "session"]
        self.assertEqual(len(session_errors), 0)

    def test_invalid_session_db_too_long(self):
        """Test session db path too long."""
        config = {"session": {"session_db": "a" * 300}}

        validator = ConfigValidator(config)
        result = validator.validate()

        db_errors = [
            e for e in result.errors if e.section == "session" and e.key == "session_db"
        ]
        self.assertGreater(len(db_errors), 0)


class TestConflictDetection(unittest.TestCase):
    """Test conflict detection between configuration settings."""

    def test_cache_disabled_adaptive_reasoning_enabled(self):
        """Test conflict: cache disabled but adaptive reasoning enabled."""
        config = {
            "cache": {"enabled": False},
            "custom": {"adaptive_reasoning": True},
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        # Should have a warning
        conflict_warnings = [
            w
            for w in result.warnings
            if "Cache is disabled but adaptive_reasoning is enabled" in w.message
        ]
        self.assertGreater(len(conflict_warnings), 0)

    def test_token_budget_exceeds_model_context(self):
        """Test conflict: token budget exceeds model context."""
        config = {
            "llm": {"model": "gpt-3.5-turbo"},
            "custom": {"token_budget": 10000},
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        # Should have an error
        conflict_errors = [
            e
            for e in result.errors
            if "exceeds model context limit" in e.message
        ]
        self.assertGreater(len(conflict_errors), 0)


class TestDeprecatedSettingsDetection(unittest.TestCase):
    """Test detection of deprecated settings."""

    def test_detect_deprecated_adaptive_reasoning(self):
        """Test detection of deprecated adaptive_reasoning setting."""
        config = {"adaptive_reasoning": True}

        validator = ConfigValidator(config)
        result = validator.validate()

        deprecated_warnings = [
            w
            for w in result.warnings
            if w.key == "adaptive_reasoning" and w.deprecated_in
        ]
        self.assertGreater(len(deprecated_warnings), 0)
        self.assertEqual(deprecated_warnings[0].deprecated_in, "5.0.0")

    def test_detect_deprecated_progress_tracking(self):
        """Test detection of deprecated progress_tracking setting."""
        config = {"progress_tracking": True}

        validator = ConfigValidator(config)
        result = validator.validate()

        deprecated_warnings = [
            w for w in result.warnings if w.key == "progress_tracking"
        ]
        self.assertGreater(len(deprecated_warnings), 0)

    def test_detect_deprecated_trap_detection(self):
        """Test detection of deprecated trap_detection setting."""
        config = {"trap_detection": True}

        validator = ConfigValidator(config)
        result = validator.validate()

        deprecated_warnings = [
            w for w in result.warnings if w.key == "trap_detection"
        ]
        self.assertGreater(len(deprecated_warnings), 0)


class TestMigration(unittest.TestCase):
    """Test migration of deprecated settings."""

    def test_migrate_deprecated_settings(self):
        """Test migration of deprecated settings."""
        config = {
            "adaptive_reasoning": True,
            "progress_tracking": False,
            "trap_detection": True,
        }

        validator = ConfigValidator(config)
        migrated = validator.migrate_deprecated(config)

        # Old settings should be removed
        self.assertNotIn("adaptive_reasoning", migrated)
        self.assertNotIn("progress_tracking", migrated)
        self.assertNotIn("trap_detection", migrated)

        # New settings should be in custom section
        self.assertIn("custom", migrated)
        self.assertTrue(migrated["custom"]["adaptive_reasoning"])
        self.assertFalse(migrated["custom"]["progress_tracking"])
        self.assertTrue(migrated["custom"]["trap_detection"])

    def test_migrate_preserves_other_settings(self):
        """Test that migration preserves other settings."""
        config = {
            "llm": {"model": "gpt-4"},
            "adaptive_reasoning": True,
            "cache": {"enabled": True},
        }

        validator = ConfigValidator(config)
        migrated = validator.migrate_deprecated(config)

        # Other settings should be preserved
        self.assertEqual(migrated["llm"]["model"], "gpt-4")
        self.assertEqual(migrated["cache"]["enabled"], True)
        self.assertNotIn("adaptive_reasoning", migrated)


class TestValidateAndMigrate(unittest.TestCase):
    """Test validate_and_migrate convenience function."""

    def test_validate_and_migrate_function(self):
        """Test validate_and_migrate function."""
        config = {
            "llm": {"model": "gpt-4", "temperature": 0.7},
            "adaptive_reasoning": True,  # Deprecated
        }

        migrated_config, result = validate_and_migrate(config)

        # Config should be migrated
        self.assertNotIn("adaptive_reasoning", migrated_config)
        self.assertTrue(migrated_config["custom"]["adaptive_reasoning"])

        # Validation should be performed on migrated config
        self.assertTrue(result.is_valid)

    def test_validate_and_migrate_with_errors(self):
        """Test validate_and_migrate with configuration errors."""
        config = {
            "llm": {"temperature": -1.0},  # Invalid
            "adaptive_reasoning": True,  # Deprecated
        }

        migrated_config, result = validate_and_migrate(config)

        # Config should be migrated
        self.assertNotIn("adaptive_reasoning", migrated_config)

        # Validation should detect errors
        self.assertFalse(result.is_valid)
        temp_errors = [
            e for e in result.errors if e.key == "temperature"
        ]
        self.assertGreater(len(temp_errors), 0)


class TestValidateConfigFunction(unittest.TestCase):
    """Test validate_config convenience function."""

    def test_validate_config_function(self):
        """Test validate_config convenience function."""
        config = {
            "llm": {"model": "gpt-4", "temperature": 0.7},
            "cache": {"enabled": True},
        }

        result = validate_config(config)

        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)


class TestComplexConfiguration(unittest.TestCase):
    """Test validation of complex, multi-section configuration."""

    def test_complex_valid_config(self):
        """Test validation of complex but valid configuration."""
        config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "cache": {
                "enabled": True,
                "max_size_mb": 100,
                "eviction_policy": "lru",
            },
            "logging": {
                "level": "INFO",
                "file": "l4.log",
                "format": "json",
            },
            "telemetry": {"enabled": True, "telemetry_db": "telemetry.db"},
            "checkpoint": {
                "enabled": True,
                "max_age_hours": 24,
                "max_count": 10,
            },
            "session": {"auto_resume": True, "session_db": "sessions.db"},
            "custom": {
                "adaptive_reasoning": True,
                "progress_tracking": True,
                "trap_detection": True,
            },
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        self.assertTrue(result.is_valid)

    def test_complex_invalid_config_multiple_errors(self):
        """Test validation of complex configuration with multiple errors."""
        config = {
            "llm": {
                "provider": "invalid_provider",
                "temperature": 3.0,
            },
            "cache": {"max_size_mb": 0, "eviction_policy": "invalid_policy"},
            "logging": {"level": "INVALID", "max_size_mb": -1},
        }

        validator = ConfigValidator(config)
        result = validator.validate()

        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 3)


if __name__ == "__main__":
    unittest.main()