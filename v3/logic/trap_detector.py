"""
Trap Detection System for L4D V4

This module defines the taxonomy of traps and anti-patterns that can occur
during autonomous development, along with detection criteria, recovery strategies,
and prevention mechanisms.

Trap Types:
- Infinite Loop: Repeating same action without progress
- Dead End: Actions that cannot lead to goal
- Circular Reasoning: Reasoning that loops back to start
- Scope Creep: Continuously expanding task scope

Anti-Patterns:
- Over-optimization: Optimizing beyond necessary level
- Premature Optimization: Optimizing too early
- Gold Plating: Adding unnecessary features
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class TrapType(Enum):
    """Classification of different trap types."""
    INFINITE_LOOP = "infinite_loop"
    DEAD_END = "dead_end"
    CIRCULAR_REASONING = "circular_reasoning"
    SCOPE_CREEP = "scope_creep"


class AntiPatternType(Enum):
    """Classification of common anti-patterns."""
    OVER_OPTIMIZATION = "over_optimization"
    PREMATURE_OPTIMIZATION = "premature_optimization"
    GOLD_PLATING = "gold_plating"


class TrapSeverity(Enum):
    """Severity level of detected trap."""
    WARNING = "warning"          # Minor issue, monitor
    CRITICAL = "critical"        # Requires immediate attention
    BLOCKING = "blocking"        # Blocks progress, must resolve


@dataclass
class TrapDefinition:
    """Definition of a trap type with detection and recovery information."""
    trap_type: TrapType
    name: str
    description: str
    detection_criteria: Dict[str, Any]
    recovery_strategies: List[str]
    prevention_strategies: List[str]
    examples: List[str]
    
    def __repr__(self) -> str:
        return f"TrapDefinition({self.trap_type.value}: {self.name})"


@dataclass
class AntiPatternDefinition:
    """Definition of an anti-pattern with examples."""
    anti_pattern_type: AntiPatternType
    name: str
    description: str
    symptoms: List[str]
    consequences: List[str]
    prevention: List[str]
    examples: List[str]
    
    def __repr__(self) -> str:
        return f"AntiPatternDefinition({self.anti_pattern_type.value}: {self.name})"


@dataclass
class TrapDetection:
    """Result of trap detection."""
    trap_type: TrapType
    severity: TrapSeverity
    confidence: float
    evidence: Dict[str, Any]
    suggestion: str
    
    def __repr__(self) -> str:
        return f"TrapDetection({self.trap_type.value}, {self.severity.value}, conf={self.confidence:.2f})"


class TrapDetector:
    """
    Main trap detector that manages trap definitions and detection logic.
    
    This component is part of the V4 adaptive reasoning system and provides
    comprehensive trap detection capabilities with recovery and prevention strategies.
    """
    
    def __init__(self):
        """Initialize trap detector with all trap definitions."""
        self.trap_definitions = self._initialize_trap_definitions()
        self.anti_pattern_definitions = self._initialize_anti_pattern_definitions()
        self.logger = logger
    
    def _initialize_trap_definitions(self) -> Dict[TrapType, TrapDefinition]:
        """Initialize all trap type definitions."""
        return {
            TrapType.INFINITE_LOOP: TrapDefinition(
                trap_type=TrapType.INFINITE_LOOP,
                name="Infinite Loop",
                description="Repeating the same action without making progress",
                detection_criteria={
                    "repetition_threshold": 3,  # Same action repeated 3+ times
                    "pattern_threshold": 5,    # Similar actions repeated 5+ times
                    "error_loop_threshold": 3,  # Same error from same action 3+ times
                    "detection_window": 10    # Look at last N operations
                },
                recovery_strategies=[
                    "break_loop_change_approach",
                    "backtrack_to_checkpoint",
                    "try_different_strategy",
                    "ask_human_intervention"
                ],
                prevention_strategies=[
                    "track_attempted_actions",
                    "warn_before_repetition",
                    "validate_progress_per_operation"
                ],
                examples=[
                    "Keep adding the same import statement to a file",
                    "Repeatedly fix the same bug with the same solution",
                    "Continuously retry failed HTTP request without backoff",
                    "Keep adding the same method call with different arguments"
                ]
            ),
            
            TrapType.DEAD_END: TrapDefinition(
                trap_type=TrapType.DEAD_END,
                name="Dead End",
                description="Actions that cannot lead to the goal",
                detection_criteria={
                    "no_progress_threshold": 5,    # No progress for 5+ operations
                    "exhausted_options": True,       # All attempted actions failed
                    "resource_exhaustion": True,     # Out of tokens, time, compute
                    "goal_unreachable": True        # Analysis shows goal impossible
                },
                recovery_strategies=[
                    "backtrack_to_last_success",
                    "break_task_smaller",
                    "try_alternative_approach",
                    "ask_human_intervention"
                ],
                prevention_strategies=[
                    "validate_progress_per_operation",
                    "check_resource_availability",
                    "analyze_action_space"
                ],
                examples=[
                    "Trying to fix a bug by modifying code that's not the root cause",
                    "Attempting to optimize a function that's already optimal",
                    "Trying to implement a feature with deprecated API",
                    "Continuing with approach that consistently fails tests"
                ]
            ),
            
            TrapType.CIRCULAR_REASONING: TrapDefinition(
                trap_type=TrapType.CIRCULAR_REASONING,
                name="Circular Reasoning",
                description="Reasoning that loops back to starting point",
                detection_criteria={
                    "decision_cycle_detected": True,    # A → B → C → A pattern
                    "revisiting_rejected": True,        # Revisiting rejected options
                    "contradictory_decisions": True,   # Making contradictory decisions
                    "cycle_detection_window": 15         # Look at last N decisions
                },
                recovery_strategies=[
                    "document_decisions_permanently",
                    "introduce_new_context",
                    "change_reasoning_strategy",
                    "ask_human_intervention"
                ],
                prevention_strategies=[
                    "maintain_decision_history",
                    "document_decision_rationale",
                    "track_rejected_options"
                ],
                examples=[
                    "Choosing strategy A, then B, then A again",
                    "Rejecting an approach, then reconsidering it",
                    "Making contradictory decisions about error handling",
                    "Revisiting previously discarded implementation options"
                ]
            ),
            
            TrapType.SCOPE_CREEP: TrapDefinition(
                trap_type=TrapType.SCOPE_CREEP,
                name="Scope Creep",
                description="Continuously expanding task scope without completion",
                detection_criteria={
                    "expansion_count_threshold": 3,    # Task expanded 3+ times
                    "expansion_frequency": 2.0,        # Expansions per hour
                    "size_increase_ratio": 2.0,        # Task size doubled
                    "no_completion_threshold": 10       # No completion for 10+ operations
                },
                recovery_strategies=[
                    "freeze_task_scope",
                    "break_into_subtasks",
                    "defer_optional_features",
                    "ask_human_intervention"
                ],
                prevention_strategies=[
                    "define_clear_boundaries",
                    "require_scope_change_approval",
                    "track_initial_vs_current_scope"
                ],
                examples=[
                    "Adding 'nice-to-have' features while implementing core functionality",
                    "Expanding task to fix related bugs",
                    "Adding documentation while writing code",
                    "Refactoring unrelated code during implementation"
                ]
            )
        }
    
    def _initialize_anti_pattern_definitions(self) -> Dict[AntiPatternType, AntiPatternDefinition]:
        """Initialize all anti-pattern definitions."""
        return {
            AntiPatternType.OVER_OPTIMIZATION: AntiPatternDefinition(
                anti_pattern_type=AntiPatternType.OVER_OPTIMIZATION,
                name="Over-Optimization",
                description="Optimizing beyond necessary level for current requirements",
                symptoms=[
                    "Spending excessive time on micro-optimizations",
                    "Preemptively optimizing non-critical paths",
                    "Implementing complex solutions for simple problems",
                    "Obsessing over premature performance gains"
                ],
                consequences=[
                    "Increased code complexity",
                    "Longer development time",
                    "Harder to maintain",
                    "Diminishing returns on optimization effort"
                ],
                prevention=[
                    "Profile before optimizing",
                    "Focus on bottlenecks first",
                    "Set optimization goals and limits",
                    "Prioritize readability over micro-optimizations"
                ],
                examples=[
                    "Rewriting a function in C when Python is fast enough",
                    "Implementing custom caching for rarely called functions",
                    "Using complex bit manipulation for simple arithmetic",
                    "Over-engineering data structures for small datasets"
                ]
            ),
            
            AntiPatternType.PREMATURE_OPTIMIZATION: AntiPatternDefinition(
                anti_pattern_type=AntiPatternType.PREMATURE_OPTIMIZATION,
                name="Premature Optimization",
                description="Optimizing before the problem is fully understood",
                symptoms=[
                    "Optimizing before measuring performance",
                    "Making assumptions about performance",
                    "Optimizing code that may change",
                    "Ignoring YAGNI (You Aren't Gonna Need It) principle"
                ],
                consequences=[
                    "Wasted time on unnecessary optimizations",
                    "Code harder to understand",
                    "Potential for introducing bugs",
                    "Delayed delivery of features"
                ],
                prevention=[
                    "Profile first, optimize later",
                    "Write clear code first",
                    "Measure actual performance bottlenecks",
                    "Optimize based on requirements, not assumptions"
                ],
                examples=[
                    "Optimizing loop that runs once per day",
                    "Implementing lazy loading for small datasets",
                    "Caching results that are fast to compute",
                    "Using asynchronous code for synchronous operations"
                ]
            ),
            
            AntiPatternType.GOLD_PLATING: AntiPatternDefinition(
                anti_pattern_type=AntiPatternType.GOLD_PLATING,
                name="Gold Plating",
                description="Adding unnecessary features or polish beyond requirements",
                symptoms=[
                    "Adding 'nice-to-have' features",
                    "Over-polishing UI/UX",
                    "Adding comprehensive error handling for unlikely cases",
                    "Implementing edge case handling prematurely"
                ],
                consequences=[
                    "Increased development time",
                    "Scope creep",
                    "Increased complexity",
                    "Delayed delivery"
                ],
                prevention=[
                    "Stick to defined acceptance criteria",
                    "Get sign-off before adding features",
                    "Prioritize core functionality",
                    "Defer enhancements to future iterations"
                ],
                examples=[
                    "Adding animations to CLI tool",
                    "Implementing custom themes for internal tool",
                    "Adding extensive logging for simple script",
                    "Creating configuration for hardcoded values"
                ]
            )
        }
    
    def get_trap_definition(self, trap_type: TrapType) -> Optional[TrapDefinition]:
        """
        Get trap definition by type.
        
        Args:
            trap_type: Type of trap
        
        Returns:
            TrapDefinition if found, None otherwise
        """
        return self.trap_definitions.get(trap_type)
    
    def get_anti_pattern_definition(
        self,
        anti_pattern_type: AntiPatternType
    ) -> Optional[AntiPatternDefinition]:
        """
        Get anti-pattern definition by type.
        
        Args:
            anti_pattern_type: Type of anti-pattern
        
        Returns:
            AntiPatternDefinition if found, None otherwise
        """
        return self.anti_pattern_definitions.get(anti_pattern_type)
    
    def list_all_traps(self) -> List[TrapDefinition]:
        """Get list of all trap definitions."""
        return list(self.trap_definitions.values())
    
    def list_all_anti_patterns(self) -> List[AntiPatternDefinition]:
        """Get list of all anti-pattern definitions."""
        return list(self.anti_pattern_definitions.values())
    
    def check_detection_criteria(
        self,
        trap_type: TrapType,
        criteria_name: str,
        value: Any
    ) -> bool:
        """
        Check if value meets detection criteria for a trap type.
        
        Args:
            trap_type: Type of trap
            criteria_name: Name of criteria to check
            value: Value to check against criteria
        
        Returns:
            True if value meets criteria, False otherwise
        """
        definition = self.get_trap_definition(trap_type)
        if not definition:
            return False
        
        criteria_value = definition.detection_criteria.get(criteria_name)
        
        # Handle different comparison types
        if isinstance(criteria_value, (int, float)):
            # Check if value meets threshold
            return value >= criteria_value
        elif isinstance(criteria_value, bool):
            # Boolean criteria
            return value == criteria_value
        else:
            # String or other type - exact match
            return value == criteria_value
    
    def get_recovery_strategies(self, trap_type: TrapType) -> List[str]:
        """
        Get recovery strategies for a trap type.
        
        Args:
            trap_type: Type of trap
        
        Returns:
            List of recovery strategies
        """
        definition = self.get_trap_definition(trap_type)
        if not definition:
            return []
        return definition.recovery_strategies
    
    def get_prevention_strategies(self, trap_type: TrapType) -> List[str]:
        """
        Get prevention strategies for a trap type.
        
        Args:
            trap_type: Type of trap
        
        Returns:
            List of prevention strategies
        """
        definition = self.get_trap_definition(trap_type)
        if not definition:
            return []
        return definition.prevention_strategies
    
    def get_examples(self, trap_type: TrapType) -> List[str]:
        """
        Get examples for a trap type.
        
        Args:
            trap_type: Type of trap
        
        Returns:
            List of examples
        """
        definition = self.get_trap_definition(trap_type)
        if not definition:
            return []
        return definition.examples
    
    def format_trap_report(
        self,
        trap_type: TrapType,
        severity: TrapSeverity,
        confidence: float,
        evidence: Dict[str, Any]
    ) -> str:
        """
        Format a human-readable trap detection report.
        
        Args:
            trap_type: Type of trap detected
            severity: Severity of trap
            confidence: Detection confidence
            evidence: Evidence supporting detection
        
        Returns:
            Formatted report string
        """
        definition = self.get_trap_definition(trap_type)
        if not definition:
            return f"Unknown trap type: {trap_type}"
        
        report = []
        report.append(f"Trap Detected: {definition.name}")
        report.append(f"Severity: {severity.value.upper()}")
        report.append(f"Confidence: {confidence:.1%}")
        report.append(f"\nDescription: {definition.description}")
        report.append(f"\nRecovery Strategies:")
        for i, strategy in enumerate(definition.recovery_strategies, 1):
            report.append(f"  {i}. {strategy}")
        report.append(f"\nPrevention Strategies:")
        for i, strategy in enumerate(definition.prevention_strategies, 1):
            report.append(f"  {i}. {strategy}")
        report.append(f"\nEvidence:")
        for key, value in evidence.items():
            report.append(f"  - {key}: {value}")
        
        return "\n".join(report)
    
    def get_trap_summary(self, trap_type: TrapType) -> str:
        """
        Get a brief summary of a trap type.
        
        Args:
            trap_type: Type of trap
        
        Returns:
            Brief summary string
        """
        definition = self.get_trap_definition(trap_type)
        if not definition:
            return f"Unknown trap type: {trap_type}"
        
        return (
            f"{definition.name}: {definition.description}\n"
            f"Detection: {len(definition.detection_criteria)} criteria, "
            f"Recovery: {len(definition.recovery_strategies)} strategies, "
            f"Prevention: {len(definition.prevention_strategies)} strategies"
        )
    
    def get_all_trap_summaries(self) -> str:
        """Get summaries of all trap types."""
        summaries = ["Trap Types Summary", "=" * 50, ""]
        for trap_type, definition in self.trap_definitions.items():
            summaries.append(self.get_trap_summary(trap_type))
            summaries.append("")
        return "\n".join(summaries)
    
    def get_all_anti_pattern_summaries(self) -> str:
        """Get summaries of all anti-pattern types."""
        summaries = ["Anti-Patterns Summary", "=" * 50, ""]
        for anti_pattern_type, definition in self.anti_pattern_definitions.items():
            summaries.append(
                f"{definition.name}: {definition.description}\n"
                f"Symptoms: {len(definition.symptoms)}, "
                f"Prevention: {len(definition.prevention)}"
            )
            summaries.append("")
        return "\n".join(summaries)


def create_trap_detector() -> TrapDetector:
    """
    Factory function to create a TrapDetector instance.
    
    Returns:
        Configured TrapDetector instance
    """
    return TrapDetector()