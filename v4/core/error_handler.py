"""
V5 Enhanced Error Handler with Helpful Suggestions

Provides intelligent error detection, helpful suggestions,
and recovery guidance for common issues.
"""

import sys
import os
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    CONFIGURATION = "Configuration"
    ENVIRONMENT = "Environment"
    NETWORK = "Network"
    LLM_API = "LLM API"
    FILE_SYSTEM = "File System"
    GIT = "Git Repository"
    TEST_FAILURE = "Test Failure"
    DEPENDENCY = "Dependency"
    CONTEXT = "Context"


class ErrorSuggestion:
    """Represents a suggested fix for an error."""
    
    def __init__(
        self,
        title: str,
        command: str,
        description: str,
        priority: str = "medium",  # high, medium, low
        auto_fix_available: bool = False,
        requires_user_action: bool = True,
        related_docs: List[str] = None,
        similar_errors: List[str] = None
    ):
        self.title = title
        self.command = command
        self.description = description
        self.priority = priority
        self.auto_fix_available = auto_fix_available
        self.requires_user_action = requires_user_action
        self.related_docs = related_docs or []
        self.similar_errors = similar_errors or []


class ErrorHandler:
    """V5 Enhanced Error Handler with helpful suggestions."""
    
    def __init__(self):
        self.error_history: List[Dict[str, Any]] = []
        self.error_patterns = {
            # Git repository errors
            "git_not_clean": ErrorSuggestion(
                title="Git Repository Not Clean",
                command="git commit",
                description="You have uncommitted changes in the repository",
                priority="high",
                auto_fix_available=False,
                requires_user_action=True,
                similar_errors=["git stash", "git reset --hard"],
                related_docs=["docs/QUICKSTART.md#troubleshooting"]
            ),
            
            # Environment errors
            "missing_dependency": ErrorSuggestion(
                title="Missing Dependency",
                command="pip install <package>",
                description="A required Python package is not installed",
                priority="high",
                auto_fix_available=True,
                requires_user_action=False,
                related_docs=[]
            ),
            
            "api_key_missing": ErrorSuggestion(
                title="LLM API Key Not Found",
                command="l4-dev config wizard",
                description="LLM API key is not configured in settings",
                priority="critical",
                auto_fix_available=False,
                requires_user_action=True,
                related_docs=["docs/beginner/QUICKSTART.md#configuration"]
            ),
            
            # Test failures
            "test_failure": ErrorSuggestion(
                title="Test Failure Detected",
                command="l4-dev workflow debug",
                description="Automated tests have failed",
                priority="high",
                auto_fix_available=False,
                requires_user_action=True,
                similar_errors=["Run tests manually"],
                related_docs=["docs/beginner/BASIC_TASKS.md#testing"]
            ),
            
            # Context quality errors
            "low_context_quality": ErrorSuggestion(
                title="Low Context Quality Detected",
                command="l4-dev quality report",
                description="Context quality is below threshold, task may fail",
                priority="medium",
                auto_fix_available=False,
                requires_user_action=False,
                related_docs=["docs/intermediate/ADVANCED_FEATURES.md#optimization"]
            ),
            
            # Cost overruns
            "cost_overrun": ErrorSuggestion(
                title="Cost Budget Exceeded",
                command="l4-dev cost --predict",
                description="Estimated cost exceeds budget",
                priority="warning",
                auto_fix_available=False,
                requires_user_action=True,
                related_docs=["docs/intermediate/CONFIGURATION.md#cost"]
            ),
            
            # Dead code removal risks
            "dead_code_risk": ErrorSuggestion(
                title="Potentially Risky Dead Code Removal",
                command="l4-dev housekeep --dry-run",
                description="Some deletions may be risky to perform automatically",
                priority="warning",
                auto_fix_available=False,
                requires_user_action=True,
                related_docs=["docs/expert/ARCHITECTURE.md#housekeeping"]
            ),
            
            # Import errors
            "import_error": ErrorSuggestion(
                title="Import Error",
                command="l4-dev deps --outdated",
                description="Module could not be imported or is outdated",
                priority="high",
                auto_fix_available=True,
                requires_user_action=False,
                similar_errors=["Check for circular dependencies"],
                related_docs=["docs/beginner/BASIC_TASKS.md#dependencies"]
            ),
            
            # File system errors
            "file_permission_error": ErrorSuggestion(
                title="File Permission Error",
                command="chmod +x <file>",
                description="Cannot read/write file due to permissions",
                priority="critical",
                auto_fix_available=False,
                requires_user_action=True,
                related_docs=["docs/QUICKSTART.md#troubleshooting"]
            ),
            
            # Configuration errors
            "config_invalid": ErrorSuggestion(
                title="Invalid Configuration",
                command="l4-dev config wizard",
                description="Configuration value is invalid or out of range",
                priority="medium",
                auto_fix_available=True,
                requires_user_action=False,
                related_docs=["docs/intermediate/CONFIGURATION.md"]
            ),
            
            # LLM API errors
            "llm_rate_limit": ErrorSuggestion(
                title="LLM API Rate Limit",
                command="l4-dev status",
                description="API rate limit reached, wait or use different provider",
                priority="warning",
                auto_fix_available=False,
                requires_user_action=True,
                related_docs=["docs/intermediate/CONFIGURATION.md#llm"]
            ),
            
            "llm_network_error": ErrorSuggestion(
                title="LLM API Network Error",
                command="l4-dev status",
                description="Network connectivity issue with LLM API",
                priority="medium",
                auto_fix_available=False,
                requires_user_action=False,
                similar_errors=["Check internet connection", "Try different provider"],
                related_docs=["docs/QUICKSTART.md#troubleshooting"]
            ),
        }
    
    def detect_error_pattern(self, error_message: str, error_type: str = None) -> Optional[ErrorSuggestion]:
        """Detect error pattern and return suggestion."""
        error_message_lower = error_message.lower()
        
        # Check each error pattern
        for pattern_key, suggestion in self.error_patterns.items():
            if any(keyword in error_message_lower for keyword in self._get_pattern_keywords(pattern_key)):
                # Apply additional filtering if needed
                if self._pattern_matches(pattern_key, error_message_lower):
                    return suggestion
        
        return None
    
    def _get_pattern_keywords(self, pattern_key: str) -> List[str]:
        """Get keywords for an error pattern."""
        keywords = {
            "git_not_clean": ["git", "uncommitted", "changes", "clean", "repository", "stash", "commit"],
            "missing_dependency": ["import", "module", "package", "installed", "pip", "install", "not found"],
            "api_key_missing": ["api", "key", "token", "missing", "not configured", "llm", "provider"],
            "test_failure": ["test", "failure", "failed", "error", "assert", "pytest"],
            "low_context_quality": ["context", "quality", "threshold", "score", "below"],
            "cost_overrun": ["cost", "budget", "exceed", "limit", "over", "estimate"],
            "dead_code_risk": ["dead", "code", "deletion", "risky", "auto", "safe", "manual"],
            "import_error": ["import", "error", "cannot", "no module", "modulenotfound", "outdated"],
            "file_permission_error": ["permission", "denied", "cannot", "read", "write", "file"],
            "config_invalid": ["config", "invalid", "out of range", "value", "setting"],
            "llm_rate_limit": ["rate", "limit", "quota", "exceeded", "429", "429 too many requests"],
            "llm_network_error": ["network", "connection", "timeout", "dns", "internet", "provider"],
        }
        return keywords.get(pattern_key, [])
    
    def _pattern_matches(self, pattern_key: str, error_message: str) -> bool:
        """Check if error message matches a pattern."""
        # Additional pattern-specific matching logic
        if pattern_key == "git_not_clean":
            # Check if actually about git being dirty
            return "uncommitted" in error_message and "git" in error_message
        elif pattern_key == "missing_dependency":
            # Check if actually about missing import
            return "no module named" in error_message.lower() or "cannot import" in error_message.lower()
        elif pattern_key == "test_failure":
            # Check if actually about test failures
            return any(word in error_message.lower() for word in ["failed", "error", "assert", "pytest"])
        elif pattern_key == "file_permission_error":
            # Check if about permissions
            return any(word in error_message.lower() for word in ["permission", "denied", "cannot", "read", "write"])
        elif pattern_key == "llm_rate_limit":
            # Check if about rate limits
            return any(word in error_message.lower() for word in ["rate limit", "429", "quota", "too many"])
        return False
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.ENVIRONMENT
    ) -> str:
        """Handle an error with helpful suggestions."""
        
        # Extract error information
        error_message = str(error)
        error_type = type(error).__name__
        
        # Detect error pattern and get suggestion
        suggestion = self.detect_error_pattern(error_message, error_type)
        
        # Log error
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "severity": severity.value,
            "category": category.value,
            "context": context,
            "suggestion": suggestion.title if suggestion else None,
            "resolved": False
        }
        self.error_history.append(error_entry)
        
        # Format error message
        output = []
        output.append(f"\n{'=' * 70}")
        output.append(f"{'=' * 70}")
        output.append(f"  {severity.value}: {error_message}")
        
        # Add context if available
        if context:
            output.append(f"\n  Context:")
            for key, value in context.items():
                output.append(f"    {key}: {value}")
        
        # Add suggestion if available
        if suggestion:
            priority_emoji = {"high": "🔴", "medium": "⚠️", "low": "💡", "critical": "🚨"}.get(suggestion.priority, "⚠️")
            output.append(f"\n  {priority_emoji} Suggestion: {suggestion.title}")
            output.append(f"  Description: {suggestion.description}")
            
            if suggestion.auto_fix_available:
                output.append(f"  Auto-fix: {suggestion.command}")
            else:
                output.append(f"  Command: {suggestion.command}")
            
            if suggestion.requires_user_action:
                output.append(f"  ⚠️  Requires user action")
            
            if suggestion.related_docs:
                output.append(f"  📚 Related docs: {', '.join(suggestion.related_docs[:2])}")
            
            if suggestion.similar_errors:
                output.append(f"  See also: {', '.join(suggestion.similar_errors[:2])}")
        
        # Add recovery suggestion
        if severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            recovery_options = self._get_recovery_options(error)
            if recovery_options:
                output.append(f"\n  🔄 Recovery Options:")
                for i, option in enumerate(recovery_options[:3], 1):
                    output.append(f"    [{i}] {option}")
        
        # Add V5-specific helpful tips
        v5_tips = self._get_v5_helpful_tips(error)
        if v5_tips:
            output.append(f"\n  💡 V5 Tips:")
            for tip in v5_tips[:2]:
                output.append(f"    • {tip}")
        
        output.append(f"{'=' * 70}")
        
        return "\n".join(output)
    
    def _get_recovery_options(self, error: Exception) -> List[str]:
        """Get recovery options based on error type."""
        error_type = type(error).__name__
        
        recovery_map = {
            "ConnectionError": [
                "Check internet connection",
                "Verify API credentials",
                "Try different network",
                "Use 'l4-dev status' to check provider status"
            ],
            "TimeoutError": [
                "Increase timeout in config",
                "Check network connectivity",
                "Try operation again later",
                "Use minimal context to reduce complexity"
            ],
            "FileNotFoundError": [
                "Verify file path in config",
                "Check working directory",
                "Run 'l4-dev doctor'",
                "Initialize project with 'l4-dev init'"
            ],
            "ImportError": [
                "Run 'l4-dev deps --outdated'",
                "Install missing dependencies",
                "Check Python path in config",
                "Use virtual environment"
            ],
            "ValueError": [
                "Validate configuration with 'l4-dev config wizard'",
                "Check configuration profile",
                "Review recent config changes",
                "Reset to defaults with 'l4-dev init --reset'"
            ],
            "RuntimeError": [
                "Check system logs with 'l4-dev logs'",
                "Review recent changes with 'l4-dev retro'",
                "Run health check with 'l4-dev doctor'",
                "Try using simpler workflow"
            ],
            "AttributeError": [
                "Run 'l4-dev doctor' to verify setup",
                "Update to latest version",
                "Check configuration compatibility",
                "Reinitialize project"
            ],
            "KeyError": [
                "Reset configuration with 'l4-dev init --reset'",
                "Check for corrupted database files",
                "Restore from checkpoint with 'l4-dev checkpoints restore'"
            ],
        }
        
        return recovery_map.get(error_type, [
            "Run 'l4-dev doctor' for diagnostics",
            "Check documentation for help",
            "Try recovery wizard with 'l4-dev recover'"
        ])
    
    def _get_v5_helpful_tips(self, error: Exception) -> List[str]:
        """Get V5-specific helpful tips based on error type."""
        error_type = type(error).__name__
        
        tips_map = {
            "ConnectionError": [
                "V5 LLM caching can help with transient errors",
                "Use 'l4-dev housekeep --dry-run' to test safely",
                "Enable local decision making in config to reduce API calls"
            ],
            "TimeoutError": [
                "Reduce context size to decrease token usage",
                "Use minimal context starter (V5 default)",
                "Check cost budget with 'l4-dev cost --report'"
            ],
            "FileNotFoundError": [
                "Use interactive mode for guidance: 'l4-dev start --interactive'",
                "Run quick start guide: 'l4-dev tutorial'",
                "Check V5 documentation: docs/beginner/"
            ],
            "ImportError": [
                "Use dependency manager: 'l4-dev deps --cleanup'",
                "V5 can detect unused dependencies automatically",
                "Housekeeping can identify unused imports"
            ],
            "RuntimeError": [
                "V5 progressive context handles errors gracefully",
                "Local decision engine prevents some LLM calls",
                "Try simplified workflow: 'l4-dev workflow simple'"
            ],
            "AttributeError": [
                "Use V5 configuration profiles for different setups",
                "Try 'minimal' profile for basic functionality",
                "Config wizard: 'l4-dev init'"
            ],
            "KeyError": [
                "V5 checkpoint system can restore state",
                "Use 'l4-dev checkpoints list' to find recovery point",
                "Try 'l4-dev recover' for interactive recovery"
            ],
        }
        
        return tips_map.get(error_type, [
            "Check V5 documentation: docs/beginner/QUICKSTART.md",
            "Try simplified command: l4-dev start (uses V5 defaults)"
        ])
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics."""
        if not self.error_history:
            return {
                "total_errors": 0,
                "by_severity": {},
                "by_category": {},
                "resolved_count": 0,
                "suggested_fixes_applied": 0
            }
        
        severity_counts = {}
        category_counts = {}
        resolved_count = sum(1 for e in self.error_history if e.get("resolved", False))
        
        for error in self.error_history:
            severity = error.get("severity", "UNKNOWN")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            category = error.get("category", "UNKNOWN")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "resolved_count": resolved_count,
            "suggested_fixes_applied": 0  # TODO: Track when suggestions are applied
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return sorted(self.error_history, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    def print_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Print error with helpful suggestions."""
        message = self.handle_error(error, context)
        print(message)


# Singleton instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_exception(error: Exception, context: Optional[Dict[str, Any]] = None, exit_on_critical: bool = True) -> None:
    """Handle an exception with helpful suggestions."""
    handler = get_error_handler()
    handler.print_error(error, context)
    
    if exit_on_critical:
        # Determine if error is critical
        error_types_to_exit = [
            KeyboardInterrupt,
            SystemExit,
            MemoryError,
            OSError,  # Only for critical OS errors
        ]
        
        if type(error) in error_types_to_exit:
            sys.exit(1)


def wrap_errors(func):
    """Decorator to wrap functions with error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = {
                "function": func.__name__,
                "args": str(args)[:100],  # Truncate for display
            }
            handle_exception(e, context)
            # Re-raise for caller to handle
            raise
    return wrapper


def safe_execute(func, default_return=None):
    """Safely execute a function and return default on error."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            handler = get_error_handler()
            handler.print_error(e, {"function": func.__name__})
            return default_return
    return wrapper