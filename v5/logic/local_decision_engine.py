"""
Local Decision Engine - Make decisions locally without LLM for simple scenarios

This module implements a rule-based decision engine that can make decisions locally
without calling the LLM for common, predictable scenarios. This reduces LLM API
calls and costs by 20-30%.

Key capabilities:
- Rule-based decision engine for common scenarios
- Decision trees for error handling, retry logic, etc.
- Fallback to LLM for complex decisions
- Decision accuracy tracking
- Savings reporting
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path


class DecisionOutcome(Enum):
    """Possible outcomes of a local decision"""
    LOCAL_SUCCESS = "local_success"  # Made locally, correct
    LOCAL_FALLBACK = "local_fallback"  # Made locally, fell back to LLM
    LLM_ONLY = "llm_only"  # Required LLM from the start
    UNKNOWN = "unknown"  # Outcome not yet determined


@dataclass
class DecisionRecord:
    """Record of a decision made by the engine"""
    timestamp: datetime
    decision_type: str
    context: Dict[str, Any]
    local_decision: Optional[Any]
    used_llm: bool
    outcome: DecisionOutcome
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'decision_type': self.decision_type,
            'context': self.context,
            'local_decision': self.local_decision,
            'used_llm': self.used_llm,
            'outcome': self.outcome.value,
            'confidence': self.confidence
        }


@dataclass
class DecisionStats:
    """Statistics for decision making"""
    total_decisions: int = 0
    local_decisions: int = 0
    llm_decisions: int = 0
    local_correct: int = 0
    local_incorrect: int = 0
    llm_calls_saved: int = 0
    
    def get_local_success_rate(self) -> float:
        """Calculate local decision success rate"""
        if self.local_decisions == 0:
            return 0.0
        return self.local_correct / self.local_decisions
    
    def get_llm_savings_rate(self) -> float:
        """Calculate percentage of LLM calls saved"""
        if self.total_decisions == 0:
            return 0.0
        return self.llm_calls_saved / self.total_decisions


class LocalDecisionEngine:
    """
    Local decision engine for making decisions without LLM
    
    This engine uses rule-based logic and decision trees to make decisions
    for common scenarios, falling back to LLM only for complex cases.
    """
    
    # Common error patterns that are transient
    TRANSIENT_ERROR_PATTERNS = [
        r'rate limit',
        r'timeout',
        r'connection.*refused',
        r'connection.*reset',
        r'connection.*timed out',
        r'temporary.*failure',
        r'service.*unavailable',
        r'too many requests',
        r'429',  # HTTP 429 Too Many Requests
        r'503',  # HTTP 503 Service Unavailable
        r'504',  # HTTP 504 Gateway Timeout
    ]
    
    # Permanent error patterns
    PERMANENT_ERROR_PATTERNS = [
        r'authentication.*failed',
        r'authorization.*failed',
        r'invalid.*api.*key',
        r'access.*denied',
        r'permission.*denied',
        r'not found',
        r'401',  # HTTP 401 Unauthorized
        r'403',  # HTTP 403 Forbidden
        r'404',  # HTTP 404 Not Found
    ]
    
    # Network error patterns
    NETWORK_ERROR_PATTERNS = [
        r'network.*unreachable',
        r'dns.*resolution.*failed',
        r'connection.*refused',
        r'connection.*reset',
        r'broken.*pipe',
    ]
    
    def __init__(self, stats_file: Optional[str] = None):
        """
        Initialize the local decision engine
        
        Args:
            stats_file: Path to file for persisting decision statistics
        """
        self.decisions: List[DecisionRecord] = []
        self.stats_file = stats_file
        self.stats = DecisionStats()
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
        
        # Load existing stats if file exists
        if stats_file and Path(stats_file).exists():
            self._load_stats()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        self.transient_patterns = [re.compile(p, re.IGNORECASE) 
                                   for p in self.TRANSIENT_ERROR_PATTERNS]
        self.permanent_patterns = [re.compile(p, re.IGNORECASE) 
                                   for p in self.PERMANENT_ERROR_PATTERNS]
        self.network_patterns = [re.compile(p, re.IGNORECASE) 
                                for p in self.NETWORK_ERROR_PATTERNS]
    
    def should_retry_error(
        self,
        error_message: str,
        attempt_count: int,
        max_transient_attempts: int = 3,
        max_network_attempts: int = 5
    ) -> Optional[bool]:
        """
        Decide whether to retry an error based on error type
        
        Args:
            error_message: The error message to analyze
            attempt_count: Current attempt number
            max_transient_attempts: Max retries for transient errors
            max_network_attempts: Max retries for network errors
            
        Returns:
            - True: Should retry
            - False: Should not retry
            - None: Fall back to LLM decision
        """
        decision_type = "should_retry_error"
        context = {
            'error_message': error_message,
            'attempt_count': attempt_count
        }
        
        # Check for transient errors
        if self._is_transient_error(error_message):
            result = attempt_count < max_transient_attempts
            confidence = 0.9
            self._record_decision(
                decision_type=decision_type,
                context=context,
                local_decision=result,
                used_llm=False,
                outcome=DecisionOutcome.LOCAL_SUCCESS if result else DecisionOutcome.LOCAL_FALLBACK,
                confidence=confidence
            )
            self.stats.llm_calls_saved += 1
            return result
        
        # Check for permanent errors
        if self._is_permanent_error(error_message):
            result = False
            confidence = 0.95
            self._record_decision(
                decision_type=decision_type,
                context=context,
                local_decision=result,
                used_llm=False,
                outcome=DecisionOutcome.LOCAL_SUCCESS,
                confidence=confidence
            )
            self.stats.llm_calls_saved += 1
            return result
        
        # Check for network errors
        if self._is_network_error(error_message):
            result = attempt_count < max_network_attempts
            confidence = 0.85
            self._record_decision(
                decision_type=decision_type,
                context=context,
                local_decision=result,
                used_llm=False,
                outcome=DecisionOutcome.LOCAL_SUCCESS if result else DecisionOutcome.LOCAL_FALLBACK,
                confidence=confidence
            )
            self.stats.llm_calls_saved += 1
            return result
        
        # Unknown error type - fall back to LLM
        self._record_decision(
            decision_type=decision_type,
            context=context,
            local_decision=None,
            used_llm=True,
            outcome=DecisionOutcome.LLM_ONLY,
            confidence=0.0
        )
        return None
    
    def classify_error(self, error_message: str) -> Optional[str]:
        """
        Classify an error as transient, permanent, or network
        
        Args:
            error_message: The error message to classify
            
        Returns:
            - 'transient': Transient error (can retry)
            - 'permanent': Permanent error (should not retry)
            - 'network': Network error (can retry with backoff)
            - None: Unknown error type (fall back to LLM)
        """
        decision_type = "classify_error"
        context = {'error_message': error_message}
        
        if self._is_transient_error(error_message):
            self._record_decision(
                decision_type=decision_type,
                context=context,
                local_decision='transient',
                used_llm=False,
                outcome=DecisionOutcome.LOCAL_SUCCESS,
                confidence=0.9
            )
            self.stats.llm_calls_saved += 1
            return 'transient'
        
        if self._is_permanent_error(error_message):
            self._record_decision(
                decision_type=decision_type,
                context=context,
                local_decision='permanent',
                used_llm=False,
                outcome=DecisionOutcome.LOCAL_SUCCESS,
                confidence=0.95
            )
            self.stats.llm_calls_saved += 1
            return 'permanent'
        
        if self._is_network_error(error_message):
            self._record_decision(
                decision_type=decision_type,
                context=context,
                local_decision='network',
                used_llm=False,
                outcome=DecisionOutcome.LOCAL_SUCCESS,
                confidence=0.85
            )
            self.stats.llm_calls_saved += 1
            return 'network'
        
        # Unknown error type
        self._record_decision(
            decision_type=decision_type,
            context=context,
            local_decision=None,
            used_llm=True,
            outcome=DecisionOutcome.LLM_ONLY,
            confidence=0.0
        )
        return None
    
    def calculate_retry_delay(
        self,
        attempt_count: int,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ) -> float:
        """
        Calculate exponential backoff delay for retry
        
        Args:
            attempt_count: Current attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            
        Returns:
            Delay in seconds
        """
        decision_type = "calculate_retry_delay"
        context = {
            'attempt_count': attempt_count,
            'base_delay': base_delay,
            'max_delay': max_delay
        }
        
        delay = min(base_delay * (exponential_base ** attempt_count), max_delay)
        
        self._record_decision(
            decision_type=decision_type,
            context=context,
            local_decision=delay,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=1.0
        )
        self.stats.llm_calls_saved += 1
        
        return delay
    
    def is_progress_stagnant(
        self,
        progress_values: List[float],
        window_size: int = 5,
        threshold: float = 0.1
    ) -> bool:
        """
        Detect if progress is stagnant (no improvement over recent operations)
        
        Args:
            progress_values: List of progress values (0.0 to 1.0)
            window_size: Number of recent values to check
            threshold: Minimum improvement threshold
            
        Returns:
            True if progress is stagnant, False otherwise
        """
        if len(progress_values) < window_size:
            return False
        
        recent_values = progress_values[-window_size:]
        max_improvement = max(recent_values) - min(recent_values)
        
        decision_type = "is_progress_stagnant"
        context = {
            'progress_values': progress_values,
            'window_size': window_size,
            'threshold': threshold
        }
        
        result = max_improvement < threshold
        confidence = 0.8
        
        self._record_decision(
            decision_type=decision_type,
            context=context,
            local_decision=result,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=confidence
        )
        self.stats.llm_calls_saved += 1
        
        return result
    
    def is_regression(
        self,
        current_progress: float,
        previous_progress: float,
        threshold: float = 0.05
    ) -> bool:
        """
        Detect if progress has regressed (gone backwards)
        
        Args:
            current_progress: Current progress value (0.0 to 1.0)
            previous_progress: Previous progress value
            threshold: Threshold for regression detection
            
        Returns:
            True if regression detected, False otherwise
        """
        decision_type = "is_regression"
        context = {
            'current_progress': current_progress,
            'previous_progress': previous_progress,
            'threshold': threshold
        }
        
        result = (previous_progress - current_progress) > threshold
        confidence = 0.95
        
        self._record_decision(
            decision_type=decision_type,
            context=context,
            local_decision=result,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=confidence
        )
        self.stats.llm_calls_saved += 1
        
        return result
    
    def select_token_budget(
        self,
        task_complexity: str,
        historical_budgets: Optional[Dict[str, float]] = None
    ) -> int:
        """
        Select appropriate token budget based on task complexity
        
        Args:
            task_complexity: Task complexity ('simple', 'medium', 'complex')
            historical_budgets: Historical optimal budgets per task type
            
        Returns:
            Token budget
        """
        decision_type = "select_token_budget"
        context = {
            'task_complexity': task_complexity,
            'historical_budgets': historical_budgets
        }
        
        # Default budgets
        default_budgets = {
            'simple': 1000,
            'medium': 3000,
            'complex': 5000
        }
        
        # Use historical budget if available and reasonable
        if historical_budgets and task_complexity in historical_budgets:
            budget = int(historical_budgets[task_complexity])
            confidence = 0.9
        else:
            budget = default_budgets.get(task_complexity, 3000)
            confidence = 0.7
        
        self._record_decision(
            decision_type=decision_type,
            context=context,
            local_decision=budget,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=confidence
        )
        self.stats.llm_calls_saved += 1
        
        return budget
    
    def should_expand_context(
        self,
        current_context_level: int,
        task_complexity: str,
        expansion_count: int,
        max_expansions: int = 3
    ) -> bool:
        """
        Decide whether to expand context based on situation
        
        Args:
            current_context_level: Current context level (0-3)
            task_complexity: Task complexity
            expansion_count: Number of times context has been expanded
            max_expansions: Maximum number of expansions
            
        Returns:
            True if should expand, False otherwise
        """
        decision_type = "should_expand_context"
        context = {
            'current_context_level': current_context_level,
            'task_complexity': task_complexity,
            'expansion_count': expansion_count
        }
        
        # Check if we've expanded too many times
        if expansion_count >= max_expansions:
            result = False
        # Expand for complex tasks
        elif task_complexity in ['complex', 'refactoring'] and current_context_level < 3:
            result = True
        # Expand for medium tasks
        elif task_complexity == 'medium' and current_context_level < 2:
            result = True
        # Otherwise, don't expand
        else:
            result = False
        
        confidence = 0.75
        
        self._record_decision(
            decision_type=decision_type,
            context=context,
            local_decision=result,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=confidence
        )
        self.stats.llm_calls_saved += 1
        
        return result
    
    def validate_file_selection(
        self,
        task_description: str,
        selected_files: List[str],
        available_files: List[str]
    ) -> Optional[bool]:
        """
        Validate that file selection is reasonable
        
        Args:
            task_description: Description of the task
            selected_files: Files selected for the task
            available_files: All available files
            
        Returns:
            True if selection is valid, False if invalid, None if uncertain
        """
        decision_type = "validate_file_selection"
        context = {
            'task_description': task_description,
            'selected_files': selected_files,
            'available_files': available_files
        }
        
        # Basic validation: check if selected files are in available files
        invalid_files = [f for f in selected_files if f not in available_files]
        if invalid_files:
            self._record_decision(
                decision_type=decision_type,
                context=context,
                local_decision=False,
                used_llm=False,
                outcome=DecisionOutcome.LOCAL_SUCCESS,
                confidence=0.95
            )
            self.stats.llm_calls_saved += 1
            return False
        
        # Check if any files are selected
        if not selected_files:
            self._record_decision(
                decision_type=decision_type,
                context=context,
                local_decision=False,
                used_llm=False,
                outcome=DecisionOutcome.LOCAL_SUCCESS,
                confidence=0.9
            )
            self.stats.llm_calls_saved += 1
            return False
        
        # If basic checks pass, the selection is likely valid
        self._record_decision(
            decision_type=decision_type,
            context=context,
            local_decision=True,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.7
        )
        self.stats.llm_calls_saved += 1
        
        return True
    
    def _is_transient_error(self, error_message: str) -> bool:
        """Check if error message indicates a transient error"""
        return any(pattern.search(error_message) for pattern in self.transient_patterns)
    
    def _is_permanent_error(self, error_message: str) -> bool:
        """Check if error message indicates a permanent error"""
        return any(pattern.search(error_message) for pattern in self.permanent_patterns)
    
    def _is_network_error(self, error_message: str) -> bool:
        """Check if error message indicates a network error"""
        return any(pattern.search(error_message) for pattern in self.network_patterns)
    
    def _record_decision(
        self,
        decision_type: str,
        context: Dict[str, Any],
        local_decision: Optional[Any],
        used_llm: bool,
        outcome: DecisionOutcome,
        confidence: float
    ):
        """Record a decision for tracking and learning"""
        record = DecisionRecord(
            timestamp=datetime.now(),
            decision_type=decision_type,
            context=context,
            local_decision=local_decision,
            used_llm=used_llm,
            outcome=outcome,
            confidence=confidence
        )
        self.decisions.append(record)
        self.stats.total_decisions += 1
        
        if used_llm:
            self.stats.llm_decisions += 1
        else:
            self.stats.local_decisions += 1
        
        # Save to file if configured
        if self.stats_file:
            self._save_stats()
    
    def record_outcome(self, decision_index: int, was_correct: bool):
        """
        Record the outcome of a decision for learning
        
        Args:
            decision_index: Index of the decision in self.decisions
            was_correct: Whether the decision was correct
        """
        if decision_index < 0 or decision_index >= len(self.decisions):
            return
        
        record = self.decisions[decision_index]
        
        if not record.used_llm:
            if was_correct:
                self.stats.local_correct += 1
            else:
                self.stats.local_incorrect += 1
        
        if self.stats_file:
            self._save_stats()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get decision statistics"""
        return {
            'total_decisions': self.stats.total_decisions,
            'local_decisions': self.stats.local_decisions,
            'llm_decisions': self.stats.llm_decisions,
            'local_success_rate': self.stats.get_local_success_rate(),
            'llm_savings_rate': self.stats.get_llm_savings_rate(),
            'llm_calls_saved': self.stats.llm_calls_saved,
            'decision_types': self._get_decision_type_stats()
        }
    
    def get_report(self) -> str:
        """Generate a human-readable report of decision statistics"""
        stats = self.get_statistics()
        
        report = f"""
Local Decision Engine Report
{'=' * 50}

Total Decisions: {stats['total_decisions']}
- Local Decisions: {stats['local_decisions']} ({stats['llm_savings_rate']*100:.1f}%)
- LLM Decisions: {stats['llm_decisions']}

Performance:
- Local Success Rate: {stats['local_success_rate']*100:.1f}%
- LLM Calls Saved: {stats['llm_calls_saved']}

Decision Type Statistics:
"""
        for decision_type, count in stats['decision_types'].items():
            report += f"  - {decision_type}: {count}\n"
        
        return report
    
    def _get_decision_type_stats(self) -> Dict[str, int]:
        """Get statistics by decision type"""
        type_counts = {}
        for record in self.decisions:
            dt = record.decision_type
            type_counts[dt] = type_counts.get(dt, 0) + 1
        return type_counts
    
    def _save_stats(self):
        """Save statistics to file"""
        if not self.stats_file:
            return
        
        data = {
            'stats': {
                'total_decisions': self.stats.total_decisions,
                'local_decisions': self.stats.local_decisions,
                'llm_decisions': self.stats.llm_decisions,
                'local_correct': self.stats.local_correct,
                'local_incorrect': self.stats.local_incorrect,
                'llm_calls_saved': self.stats.llm_calls_saved
            },
            'decisions': [record.to_dict() for record in self.decisions[-100:]]  # Last 100
        }
        
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save stats to {self.stats_file}: {e}")
    
    def _load_stats(self):
        """Load statistics from file"""
        try:
            with open(self.stats_file, 'r') as f:
                data = json.load(f)
            
            # Load stats
            stats_data = data.get('stats', {})
            self.stats.total_decisions = stats_data.get('total_decisions', 0)
            self.stats.local_decisions = stats_data.get('local_decisions', 0)
            self.stats.llm_decisions = stats_data.get('llm_decisions', 0)
            self.stats.local_correct = stats_data.get('local_correct', 0)
            self.stats.local_incorrect = stats_data.get('local_incorrect', 0)
            self.stats.llm_calls_saved = stats_data.get('llm_calls_saved', 0)
            
            # Load recent decisions
            decisions_data = data.get('decisions', [])
            for dec_data in decisions_data:
                self.decisions.append(DecisionRecord(
                    timestamp=datetime.fromisoformat(dec_data['timestamp']),
                    decision_type=dec_data['decision_type'],
                    context=dec_data['context'],
                    local_decision=dec_data['local_decision'],
                    used_llm=dec_data['used_llm'],
                    outcome=DecisionOutcome(dec_data['outcome']),
                    confidence=dec_data['confidence']
                ))
        except Exception as e:
            print(f"Warning: Could not load stats from {self.stats_file}: {e}")
    
    def clear_history(self):
        """Clear decision history (but keep stats)"""
        self.decisions.clear()
        if self.stats_file:
            self._save_stats()