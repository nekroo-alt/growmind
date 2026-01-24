"""
Context Expander - V4 Adaptive Reasoning System

This module implements intelligent context expansion based on task needs.
It starts with minimal context (L0) and progressively expands to higher
levels (L1, L2, L3) as needed based on sufficiency checks.

The system learns optimal context levels for different task types over time
to minimize context usage while ensuring adequate information for decision making.
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading

from data.context_hierarchy import ContextHierarchyManager, ContextLevel
from core.logging_config import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    """Enumeration of common task types."""
    TASK_BREAKDOWN = "task_breakdown"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    REFACTORING = "refactoring"
    ERROR_RECOVERY = "error_recovery"
    TESTING = "testing"
    CODE_REVIEW = "code_review"
    CONTEXT_COLLECTION = "context_collection"
    PLANNING = "planning"
    ANALYSIS = "analysis"


@dataclass
class ContextSufficiencyResult:
    """Result of context sufficiency check."""
    is_sufficient: bool
    confidence: float
    reasons: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)


@dataclass
class ExpansionDecision:
    """Record of a context expansion decision."""
    timestamp: float
    task_type: str
    initial_level: str
    final_level: str
    reasons: List[str]
    success: bool = False
    time_elapsed: float = 0.0


class ContextExpander:
    """
    Implements intelligent context expansion based on task needs.
    
    Features:
    - Start with L0 context (minimal)
    - Expand to higher levels if insufficient
    - Track sufficiency of each context level
    - Learn optimal context levels per task type
    - Log expansion decisions in telemetry
    
    Context Level Hierarchy:
    - L0 (Immediate): Current action, current state, last error
    - L1 (Recent): Last 10 actions, last 5 errors, recent telemetry
    - L2 (Session): Session history, task progress, patterns
    - L3 (Project): Project state, architecture, long-term patterns
    """
    
    # Default optimal context levels per task type
    DEFAULT_OPTIMAL_LEVELS = {
        TaskType.TASK_BREAKDOWN: ContextLevel.L1,
        TaskType.IMPLEMENTATION: ContextLevel.L0,
        TaskType.VERIFICATION: ContextLevel.L1,
        TaskType.REFACTORING: ContextLevel.L2,
        TaskType.ERROR_RECOVERY: ContextLevel.L2,
        TaskType.TESTING: ContextLevel.L1,
        TaskType.CODE_REVIEW: ContextLevel.L1,
        TaskType.CONTEXT_COLLECTION: ContextLevel.L0,
        TaskType.PLANNING: ContextLevel.L2,
        TaskType.ANALYSIS: ContextLevel.L2,
    }
    
    # Minimum required elements per level
    MINIMUM_ELEMENTS = {
        ContextLevel.L0: ['current_action', 'current_state'],
        ContextLevel.L1: ['current_action', 'recent_actions', 'recent_errors'],
        ContextLevel.L2: ['actions', 'errors', 'task_progress'],
        ContextLevel.L3: ['state', 'architecture', 'patterns'],
    }
    
    # Maximum expansion attempts (to prevent infinite loops)
    MAX_EXPANSION_ATTEMPTS = 4
    
    def __init__(
        self,
        context_manager: ContextHierarchyManager,
        telemetry_manager: Optional[Any] = None,
        learning_rate: float = 0.1
    ):
        """
        Initialize ContextExpander.
        
        Args:
            context_manager: ContextHierarchyManager instance
            telemetry_manager: Optional TelemetryManager for tracking
            learning_rate: Learning rate for adapting optimal levels (0.0-1.0)
        """
        self.context_manager = context_manager
        self.telemetry_manager = telemetry_manager
        self.learning_rate = learning_rate
        
        self._lock = threading.RLock()
        
        # Learned optimal levels per task type
        self._optimal_levels: Dict[str, str] = {
            task_type.value: level.value
            for task_type, level in self.DEFAULT_OPTIMAL_LEVELS.items()
        }
        
        # Success rates per task type per level
        self._success_rates: Dict[Tuple[str, str], float] = {}
        
        # Expansion history for analysis
        self._expansion_history: List[ExpansionDecision] = []
        
        # Task type aliases for flexibility
        self._task_type_aliases = {
            'planner': TaskType.PLANNING,
            'implementor': TaskType.IMPLEMENTATION,
            'verifier': TaskType.VERIFICATION,
            'dispatcher': TaskType.CONTEXT_COLLECTION,
            'retro': TaskType.ANALYSIS,
        }
        
        logger.info(f"ContextExpander initialized with learning_rate={learning_rate}")
    
    def _resolve_task_type(self, task_type: str) -> TaskType:
        """
        Resolve task type string to enum, handling aliases.
        
        Args:
            task_type: Task type string or alias
        
        Returns:
            TaskType enum value
        """
        # Check direct enum match
        try:
            return TaskType(task_type)
        except ValueError:
            pass
        
        # Check aliases
        if task_type.lower() in self._task_type_aliases:
            return self._task_type_aliases[task_type.lower()]
        
        # Default to IMPLEMENTATION
        logger.warning(f"Unknown task type '{task_type}', defaulting to IMPLEMENTATION")
        return TaskType.IMPLEMENTATION
    
    def get_context(
        self,
        task_type: str,
        max_levels: int = 4,
        force_expand: bool = False
    ) -> Tuple[Dict[str, Any], str]:
        """
        Get context with adaptive expansion based on task needs.
        
        Args:
            task_type: Type of task (e.g., "implementation", "planning")
            max_levels: Maximum number of levels to try (1-4)
            force_expand: Force expansion even if initial level is sufficient
        
        Returns:
            Tuple of (context_dict, final_level)
        """
        task_enum = self._resolve_task_type(task_type)
        task_key = task_enum.value
        
        # Get learned optimal level for this task type
        with self._lock:
            initial_level = self._optimal_levels.get(task_key, ContextLevel.L0)
        
        # Start expansion from optimal level
        level = initial_level
        ctx = None
        
        # Track expansion decision
        decision = ExpansionDecision(
            timestamp=time.time(),
            task_type=task_key,
            initial_level=level,
            final_level=level,
            reasons=[]
        )
        
        attempts = 0
        start_time = time.time()
        
        try:
            # Try up to max_levels or until context is sufficient
            while attempts < min(max_levels, self.MAX_EXPANSION_ATTEMPTS):
                attempts += 1
                
                logger.debug(
                    f"Context expansion attempt {attempts}: "
                    f"trying level {level} for task {task_key}"
                )
                
                # Get context at current level
                ctx = self._get_context_at_level(level)
                
                # Check if context is sufficient
                is_sufficient = self._is_context_sufficient(
                    ctx, task_enum, level
                )
                
                if is_sufficient and not force_expand:
                    decision.final_level = level
                    decision.reasons.append(
                        f"Context at {level} is sufficient for {task_key}"
                    )
                    logger.info(
                        f"Context sufficient at {level} for {task_key} "
                        f"(attempts={attempts})"
                    )
                    break
                
                # Context insufficient, try next level
                reasons = self._get_insufficiency_reasons(ctx, task_enum, level)
                decision.reasons.extend(reasons)
                
                next_level = self._get_next_level(level)
                if not next_level:
                    logger.warning(f"Already at highest level {level}, cannot expand")
                    decision.reasons.append(f"Already at highest level {level}")
                    break
                
                level = next_level
                decision.reasons.append(
                    f"Expanded from {self._get_prev_level(level) or 'unknown'} to {level}"
                )
            
            # Record success/failure
            decision.success = True
            decision.time_elapsed = time.time() - start_time
            
            # Log expansion decision
            self._record_expansion_decision(decision)
            
            # Update optimal level learning
            self._update_optimal_level(task_enum, decision)
            
            # Track in telemetry if available
            if self.telemetry_manager:
                try:
                    self.telemetry_manager.record_event(
                        "context_expansion",
                        "info",
                        f"Expanded from {decision.initial_level} to {decision.final_level} "
                        f"for task {task_key}",
                        context={
                            'task_type': task_key,
                            'initial_level': decision.initial_level,
                            'final_level': decision.final_level,
                            'attempts': attempts,
                            'reasons': decision.reasons
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to record context expansion in telemetry: {e}")
            
            return ctx, decision.final_level
            
        except Exception as e:
            logger.error(f"Error during context expansion: {e}", exc_info=True)
            decision.success = False
            decision.time_elapsed = time.time() - start_time
            decision.reasons.append(f"Error: {str(e)}")
            self._record_expansion_decision(decision)
            
            # Return best effort context
            return ctx or {}, level
    
    def _get_context_at_level(self, level: str) -> Dict[str, Any]:
        """
        Get context dictionary for a specific level.
        
        Args:
            level: Context level (L0, L1, L2, L3)
        
        Returns:
            Context dictionary
        """
        if level == ContextLevel.L0:
            return {
                'level': level,
                'current_action': self.context_manager.get_current_action(),
                'timestamp': time.time()
            }
        
        elif level == ContextLevel.L1:
            return {
                'level': level,
                'current_action': self.context_manager.get_current_action(),
                'recent_actions': self.context_manager.get_recent_actions(count=10),
                'timestamp': time.time()
            }
        
        elif level == ContextLevel.L2:
            return {
                'level': level,
                **self.context_manager.get_session_context()
            }
        
        elif level == ContextLevel.L3:
            return {
                'level': level,
                **self.context_manager.get_project_context()
            }
        
        else:
            logger.warning(f"Unknown context level: {level}")
            return {'level': level, 'timestamp': time.time()}
    
    def _is_context_sufficient(
        self,
        ctx: Dict[str, Any],
        task_type: TaskType,
        level: str
    ) -> bool:
        """
        Check if context is sufficient for the given task type.
        
        Args:
            ctx: Context dictionary
            task_type: Task type enum
            level: Context level
        
        Returns:
            True if context is sufficient
        """
        # Check minimum required elements
        required_elements = self.MINIMUM_ELEMENTS.get(level, [])
        missing_elements = []
        
        for element in required_elements:
            if element not in ctx or ctx[element] is None:
                missing_elements.append(element)
        
        if missing_elements:
            logger.debug(
                f"Context at {level} missing elements: {missing_elements}"
            )
            return False
        
        # Check task-specific requirements
        if task_type == TaskType.IMPLEMENTATION:
            # Implementation needs current action at minimum
            if not ctx.get('current_action'):
                logger.debug("Implementation task requires current_action")
                return False
        
        elif task_type == TaskType.TASK_BREAKDOWN:
            # Task breakdown benefits from recent actions
            if level == ContextLevel.L0:
                recent_actions = ctx.get('recent_actions', [])
                if not recent_actions:
                    logger.debug("Task breakdown needs recent actions")
                    return False
        
        elif task_type == TaskType.VERIFICATION:
            # Verification needs recent context
            if level == ContextLevel.L0:
                recent_actions = ctx.get('recent_actions', [])
                if len(recent_actions) < 3:
                    logger.debug("Verification needs more recent context")
                    return False
        
        elif task_type == TaskType.ERROR_RECOVERY:
            # Error recovery benefits from session context
            if level in [ContextLevel.L0, ContextLevel.L1]:
                logger.debug("Error recovery benefits from session context")
                return False
        
        return True
    
    def _get_insufficiency_reasons(
        self,
        ctx: Dict[str, Any],
        task_type: TaskType,
        level: str
    ) -> List[str]:
        """
        Get reasons why context is insufficient.
        
        Args:
            ctx: Context dictionary
            task_type: Task type enum
            level: Context level
        
        Returns:
            List of insufficiency reasons
        """
        reasons = []
        
        # Check missing required elements
        required_elements = self.MINIMUM_ELEMENTS.get(level, [])
        for element in required_elements:
            if element not in ctx or ctx[element] is None:
                reasons.append(f"Missing required element: {element}")
        
        # Check task-specific insufficiency
        if task_type == TaskType.TASK_BREAKDOWN and level == ContextLevel.L0:
            reasons.append("Task breakdown needs recent actions (L1+)")
        
        elif task_type == TaskType.VERIFICATION and level == ContextLevel.L0:
            reasons.append("Verification needs more context (L1+)")
        
        elif task_type == TaskType.ERROR_RECOVERY and level in [ContextLevel.L0, ContextLevel.L1]:
            reasons.append("Error recovery benefits from session context (L2+)")
        
        elif task_type == TaskType.REFACTORING and level in [ContextLevel.L0, ContextLevel.L1]:
            reasons.append("Refactoring needs broader context (L2+)")
        
        return reasons
    
    def _get_next_level(self, current_level: str) -> Optional[str]:
        """
        Get next higher context level.
        
        Args:
            current_level: Current context level
        
        Returns:
            Next level or None if already at highest
        """
        levels = [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]
        
        try:
            index = levels.index(current_level)
            if index < len(levels) - 1:
                return levels[index + 1]
        except ValueError:
            pass
        
        return None
    
    def _get_prev_level(self, current_level: str) -> Optional[str]:
        """
        Get previous lower context level.
        
        Args:
            current_level: Current context level
        
        Returns:
            Previous level or None if already at lowest
        """
        levels = [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]
        
        try:
            index = levels.index(current_level)
            if index > 0:
                return levels[index - 1]
        except ValueError:
            pass
        
        return None
    
    def _record_expansion_decision(self, decision: ExpansionDecision):
        """
        Record expansion decision for analysis.
        
        Args:
            decision: Expansion decision to record
        """
        with self._lock:
            self._expansion_history.append(decision)
            
            # Keep only last 1000 decisions
            if len(self._expansion_history) > 1000:
                self._expansion_history = self._expansion_history[-1000:]
            
            logger.debug(
                f"Recorded expansion decision: {decision.task_type} "
                f"{decision.initial_level} -> {decision.final_level}"
            )
    
    def _update_optimal_level(self, task_type: TaskType, decision: ExpansionDecision):
        """
        Update optimal level based on expansion decision.
        
        Args:
            task_type: Task type enum
            decision: Expansion decision
        """
        with self._lock:
            task_key = task_type.value
            current_optimal = self._optimal_levels.get(task_key, ContextLevel.L0)
            
            # If expansion was successful at a level higher than optimal,
            # suggest increasing optimal level gradually
            if decision.success and decision.final_level != current_optimal:
                # Only adjust if we consistently need higher level
                recent_decisions = [
                    d for d in self._expansion_history[-20:]
                    if d.task_type == task_key and d.success
                ]
                
                if len(recent_decisions) >= 5:
                    # Count how many needed to expand
                    expansions_needed = sum(
                        1 for d in recent_decisions
                        if d.final_level > current_optimal
                    )
                    
                    if expansions_needed >= len(recent_decisions) * 0.7:
                        # 70% of recent decisions needed higher level
                        new_optimal = decision.final_level
                        self._optimal_levels[task_key] = new_optimal
                        logger.info(
                            f"Updated optimal level for {task_key}: "
                            f"{current_optimal} -> {new_optimal} "
                            f"(learning_rate={self.learning_rate})"
                        )
    
    def report_outcome(
        self,
        task_type: str,
        context_level: str,
        success: bool,
        time_elapsed: float
    ):
        """
        Report outcome of a task to improve learning.
        
        Args:
            task_type: Type of task
            context_level: Context level used
            success: Whether task was successful
            time_elapsed: Time taken for task
        """
        task_enum = self._resolve_task_type(task_type)
        task_key = task_enum.value
        
        with self._lock:
            key = (task_key, context_level)
            
            # Initialize or update success rate
            if key not in self._success_rates:
                self._success_rates[key] = 1.0 if success else 0.0
            else:
                current_rate = self._success_rates[key]
                # Update using exponential moving average
                new_rate = (1 - self.learning_rate) * current_rate + \
                            self.learning_rate * (1.0 if success else 0.0)
                self._success_rates[key] = new_rate
            
            logger.debug(
                f"Reported outcome for {task_key} at {context_level}: "
                f"success={success}, rate={self._success_rates[key]:.2f}"
            )
    
    def get_optimal_level(self, task_type: str) -> str:
        """
        Get learned optimal context level for a task type.
        
        Args:
            task_type: Type of task
        
        Returns:
            Optimal context level
        """
        task_enum = self._resolve_task_type(task_type)
        task_key = task_enum.value
        
        with self._lock:
            return self._optimal_levels.get(task_key, ContextLevel.L0)
    
    def get_success_rate(self, task_type: str, level: str) -> float:
        """
        Get success rate for a task type at a specific level.
        
        Args:
            task_type: Type of task
            level: Context level
        
        Returns:
            Success rate (0.0-1.0)
        """
        task_enum = self._resolve_task_type(task_type)
        task_key = task_enum.value
        
        with self._lock:
            return self._success_rates.get((task_key, level), 0.0)
    
    def get_expansion_stats(self) -> Dict[str, Any]:
        """
        Get statistics about context expansion decisions.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            if not self._expansion_history:
                return {
                    'total_decisions': 0,
                    'avg_expansions': 0.0,
                    'expansion_rate': 0.0
                }
            
            total = len(self._expansion_history)
            expansions = sum(
                1 for d in self._expansion_history
                if d.final_level != d.initial_level
            )
            
            # Calculate average number of expansions
            levels_order = [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]
            avg_expansions = sum(
                levels_order.index(d.final_level) - levels_order.index(d.initial_level)
                for d in self._expansion_history
            ) / total
            
            return {
                'total_decisions': total,
                'expansions': expansions,
                'expansion_rate': expansions / total,
                'avg_expansions': avg_expansions,
                'optimal_levels': self._optimal_levels.copy(),
                'recent_decisions': [
                    {
                        'timestamp': d.timestamp,
                        'task_type': d.task_type,
                        'initial_level': d.initial_level,
                        'final_level': d.final_level,
                        'success': d.success
                    }
                    for d in self._expansion_history[-10:]
                ]
            }
    
    def reset_optimal_levels(self):
        """Reset optimal levels to defaults."""
        with self._lock:
            self._optimal_levels = {
                task_type.value: level.value
                for task_type, level in self.DEFAULT_OPTIMAL_LEVELS.items()
            }
            logger.info("Reset optimal levels to defaults")


# Global instance for singleton pattern
_context_expander_instance = None


def get_context_expander(
    context_hierarchy_manager=None,
    telemetry_manager=None
) -> ContextExpander:
    """
    Get or create singleton ContextExpander instance
    
    Args:
        context_hierarchy_manager: Manager for accessing hierarchical context
        telemetry_manager: Manager for tracking expansion operations
        
    Returns:
        ContextExpander instance
    """
    global _context_expander_instance
    
    if _context_expander_instance is None:
        _context_expander_instance = ContextExpander(
            context_manager=context_hierarchy_manager,
            telemetry_manager=telemetry_manager
        )
        logger.info("Created singleton ContextExpander instance")
    
    return _context_expander_instance


def reset_context_expander():
    """
    Reset singleton ContextExpander instance
    Useful for testing or reinitialization
    """
    global _context_expander_instance
    _context_expander_instance = None
    logger.info("Reset singleton ContextExpander instance")
