"""
Configuration Wizard Module

Provides interactive setup wizard for first-time users with auto-detection
of project characteristics and system resources.
"""

import os
import shutil
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import psutil
from .config import ConfigManager, AppConfig, LLMConfig, CacheConfig

logger = logging.getLogger(__name__)


class ProjectSize(str):
    """Project size categories."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ResourceDetector:
    """Detects system resources and project characteristics."""

    @staticmethod
    def get_disk_space() -> Dict[str, int]:
        """
        Get available disk space.

        Returns:
            Dict with total, free, and used space in GB
        """
        try:
            usage = shutil.disk_usage(os.getcwd())
            return {
                "total_gb": usage.total // (1024 ** 3),
                "free_gb": usage.free // (1024 ** 3),
                "used_gb": usage.used // (1024 ** 3),
            }
        except Exception as e:
            logger.warning(f"Failed to detect disk space: {e}")
            return {"total_gb": 100, "free_gb": 50, "used_gb": 50}

    @staticmethod
    def get_ram() -> int:
        """
        Get available RAM.

        Returns:
            RAM in GB
        """
        try:
            return psutil.virtual_memory().total // (1024 ** 3)
        except Exception as e:
            logger.warning(f"Failed to detect RAM: {e}")
            return 16  # Default assumption

    @staticmethod
    def get_cpu_count() -> int:
        """
        Get CPU core count.

        Returns:
            Number of CPU cores
        """
        try:
            return psutil.cpu_count(logical=True) or 4
        except Exception as e:
            logger.warning(f"Failed to detect CPU count: {e}")
            return 4  # Default assumption

    @staticmethod
    def detect_project_size() -> Tuple[ProjectSize, Dict[str, int]]:
        """
        Detect project size based on files and lines of code.

        Returns:
            Tuple of (size_category, metrics)
        """
        try:
            python_files = list(Path(".").rglob("*.py"))
            file_count = len(python_files)

            # Count lines of code (exclude empty lines and comments)
            total_lines = 0
            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        total_lines += sum(
                            1
                            for line in lines
                            if line.strip()
                            and not line.strip().startswith("#")
                        )
                except Exception:
                    pass

            metrics = {
                "file_count": file_count,
                "line_count": total_lines,
            }

            # Classify project size
            if file_count < 50 and total_lines < 5000:
                return ProjectSize.SMALL, metrics
            elif file_count < 200 and total_lines < 20000:
                return ProjectSize.MEDIUM, metrics
            else:
                return ProjectSize.LARGE, metrics

        except Exception as e:
            logger.warning(f"Failed to detect project size: {e}")
            return ProjectSize.MEDIUM, {"file_count": 100, "line_count": 10000}

    @staticmethod
    def has_llm_api_key() -> bool:
        """
        Check if LLM API key is available in environment.

        Returns:
            True if API key is configured
        """
        return bool(
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )


class ConfigWizard:
    """Interactive configuration wizard for first-time setup."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize ConfigWizard.

        Args:
            config_file: Path to configuration file
        """
        self.config_manager = ConfigManager(config_file)
        self.detector = ResourceDetector()
        self.config_file = config_file or ConfigManager.DEFAULT_CONFIG_FILE

    def run(self) -> AppConfig:
        """
        Run the interactive configuration wizard.

        Returns:
            AppConfig: Configured application settings
        """
        print("\n" + "=" * 60)
        print("Welcome to L4D Setup Wizard!")
        print("=" * 60 + "\n")

        # Step 1: Detect system resources
        self._step_detect_resources()

        # Step 2: Detect project size
        self._step_detect_project_size()

        # Step 3: Configure LLM settings
        llm_config = self._step_configure_llm()

        # Step 4: Configure features
        cache_enabled, adaptive_reasoning, trap_detection = self._step_configure_features()

        # Step 5: Review and confirm
        config = self._step_review_and_confirm(
            llm_config, cache_enabled, adaptive_reasoning, trap_detection
        )

        # Step 6: Save configuration
        self._step_save_configuration(config)

        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60 + "\n")

        return config

    def _step_detect_resources(self) -> Dict[str, Any]:
        """Detect and display system resources."""
        print("Step 1: Detecting System Resources")
        print("-" * 40)

        disk = self.detector.get_disk_space()
        ram = self.detector.get_ram()
        cpu = self.detector.get_cpu_count()

        print(f"  Disk Space: {disk['free_gb']} GB free / {disk['total_gb']} GB total")
        print(f"  RAM: {ram} GB")
        print(f"  CPU Cores: {cpu}")
        print()

        return {"disk": disk, "ram": ram, "cpu": cpu}

    def _step_detect_project_size(self) -> Tuple[ProjectSize, Dict[str, int]]:
        """Detect and display project size."""
        print("Step 2: Detecting Project Size")
        print("-" * 40)

        size, metrics = self.detector.detect_project_size()

        print(f"  Project Size: {size.upper()}")
        print(f"  Python Files: {metrics['file_count']}")
        print(f"  Lines of Code: {metrics['line_count']:,}")
        print()

        return size, metrics

    def _step_configure_llm(self) -> LLMConfig:
        """Configure LLM provider and model."""
        print("Step 3: Configure LLM Provider")
        print("-" * 40)

        # Check if API key is available
        has_api_key = self.detector.has_llm_api_key()

        if has_api_key:
            print("  ✓ API key detected in environment")
        else:
            print("  ! No API key detected in environment")
            print("  ! You can configure it later in .l4_config.json")
            print()

        # Select provider
        print("\n  Select LLM Provider:")
        print("  [1] OpenAI (GPT-4, GPT-3.5-turbo)")
        print("  [2] Anthropic (Claude)")
        print("  [3] Google (Gemini)")

        choice = input("\n  Select provider [1-3] [default: 1]: ").strip()
        if not choice:
            choice = "1"

        provider_map = {
            "1": ("openai", "gpt-4"),
            "2": ("anthropic", "claude-3-opus-20240229"),
            "3": ("google", "gemini-pro"),
        }

        provider, model = provider_map.get(choice, ("openai", "gpt-4"))

        print(f"\n  Provider: {provider}")
        print(f"  Model: {model}")

        return LLMConfig(provider=provider, model=model)

    def _step_configure_features(self) -> Tuple[bool, bool, bool]:
        """Configure feature flags."""
        print("\nStep 4: Configure Features")
        print("-" * 40)

        # Cache
        cache_input = input(
            "  Enable caching? [Y/n] [default: Y]: "
        ).strip().lower()
        cache_enabled = cache_input != "n"

        # Adaptive reasoning
        adaptive_input = input(
            "  Enable adaptive reasoning? [Y/n] [default: Y]: "
        ).strip().lower()
        adaptive_reasoning = adaptive_input != "n"

        # Trap detection
        trap_input = input(
            "  Enable trap detection? [Y/n] [default: Y]: "
        ).strip().lower()
        trap_detection = trap_input != "n"

        print()

        return cache_enabled, adaptive_reasoning, trap_detection

    def _step_review_and_confirm(
        self, llm_config: LLMConfig, cache_enabled: bool, adaptive_reasoning: bool, trap_detection: bool
    ) -> AppConfig:
        """Review and confirm configuration."""
        print("Step 5: Review Configuration")
        print("-" * 40)

        print(f"  LLM Provider: {llm_config.provider}")
        print(f"  LLM Model: {llm_config.model}")
        print(f"  Cache Enabled: {cache_enabled}")
        print(f"  Adaptive Reasoning: {adaptive_reasoning}")
        print(f"  Trap Detection: {trap_detection}")
        print()

        confirm = input("  Save this configuration? [Y/n] [default: Y]: ").strip().lower()

        if confirm == "n":
            print("\n  Setup cancelled. Configuration not saved.")
            exit(0)

        # Create config with smart defaults
        size, metrics = self.detector.detect_project_size()
        resources = self._step_detect_resources()

        config = AppConfig(
            llm=llm_config,
            cache=CacheConfig(
                enabled=cache_enabled,
                max_size_mb=self._calculate_cache_size(size, resources),
                cache_dir=".l4_cache",
            ),
            custom={
                "adaptive_reasoning": adaptive_reasoning,
                "trap_detection": trap_detection,
                "project_size": size,
            },
        )

        return config

    def _step_save_configuration(self, config: AppConfig) -> None:
        """Save configuration to file."""
        print("Step 6: Saving Configuration")
        print("-" * 40)

        self.config_manager.save(config)

        config_path = Path(self.config_file).absolute()
        print(f"  Configuration saved to: {config_path}")
        print()

    def _calculate_cache_size(self, size: ProjectSize, resources: Dict[str, Any]) -> int:
        """
        Calculate optimal cache size based on project size and available resources.

        Args:
            size: Project size category
            resources: System resources dict

        Returns:
            Optimal cache size in MB
        """
        # Base size by project
        base_sizes = {
            ProjectSize.SMALL: 50,
            ProjectSize.MEDIUM: 100,
            ProjectSize.LARGE: 200,
        }

        # Limit to 10% of free disk space
        free_gb = resources["disk"]["free_gb"]
        max_from_disk = min(500, free_gb * 1024 // 10)  # Max 500MB or 10% of free space

        # Use smaller of project-based or disk-based limit
        cache_size = min(base_sizes[size], max_from_disk)

        logger.info(f"Calculated cache size: {cache_size} MB (project: {size}, free disk: {free_gb} GB)")
        return cache_size


def run_wizard(config_file: Optional[str] = None) -> AppConfig:
    """
    Run the configuration wizard.

    Args:
        config_file: Optional path to configuration file

    Returns:
        AppConfig: Configured application settings
    """
    wizard = ConfigWizard(config_file)
    return wizard.run()