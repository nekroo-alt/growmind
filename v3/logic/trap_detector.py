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

from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta

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
    
    # ========== LOOP DETECTION METHODS (Task 4.2) ==========
    
    def detect_exact_action_loop(
        self,
        action_history: List[Dict[str, Any]],
        window: Optional[int] = None
    ) -> Optional[TrapDetection]:
        """
        Detect exact action repetitions (same action 3+ times).
        
        Args:
            action_history: List of action records with 'action' field
            window: Number of recent actions to check (default from detection_criteria)
        
        Returns:
            TrapDetection if loop detected, None otherwise
        """
        loop_def = self.get_trap_definition(TrapType.INFINITE_LOOP)
        if not loop_def:
            return None
        
        if window is None:
            window = loop_def.detection_criteria.get("detection_window", 10)
        threshold = loop_def.detection_criteria.get("repetition_threshold", 3)
        
        # Check last N actions
        recent_actions = action_history[-window:] if len(action_history) > window else action_history
        
        # Count action occurrences
        action_counts = Counter(
            action.get("action", str(action)) 
            for action in recent_actions
        )
        
        # Check for exact repetition
        for action, count in action_counts.items():
            if count >= threshold:
                severity = TrapSeverity.CRITICAL if count >= 5 else TrapSeverity.WARNING
                confidence = min(0.9, 0.5 + (count - threshold) * 0.1)
                
                return TrapDetection(
                    trap_type=TrapType.INFINITE_LOOP,
                    severity=severity,
                    confidence=confidence,
                    evidence={
                        "loop_type": "exact_action_loop",
                        "action": action,
                        "repetition_count": count,
                        "threshold": threshold,
                        "window": window,
                        "recent_actions": [str(a.get("action", a)) for a in recent_actions[-threshold:]]
                    },
                    suggestion=f"Action '{action}' repeated {count} times. Try a different approach."
                )
        
        return None
    
    def detect_similar_action_pattern(
        self,
        action_history: List[Dict[str, Any]],
        similarity_threshold: float = 0.8,
        window: Optional[int] = None
    ) -> Optional[TrapDetection]:
        """
        Detect similar action patterns (similar actions 5+ times).
        
        Args:
            action_history: List of action records with 'action' field
            similarity_threshold: Minimum similarity score (0-1)
            window: Number of recent actions to check
        
        Returns:
            TrapDetection if loop detected, None otherwise
        """
        loop_def = self.get_trap_definition(TrapType.INFINITE_LOOP)
        if not loop_def:
            return None
        
        if window is None:
            window = loop_def.detection_criteria.get("detection_window", 10)
        threshold = loop_def.detection_criteria.get("pattern_threshold", 5)
        
        recent_actions = action_history[-window:] if len(action_history) > window else action_history
        
        # Group actions by similarity
        action_groups = defaultdict(list)
        
        for i, action_record in enumerate(recent_actions):
            action = str(action_record.get("action", action_record))
            found_group = False
            
            # Check if action is similar to any existing group
            for group_key in action_groups:
                similarity = self._calculate_similarity(action, group_key)
                if similarity >= similarity_threshold:
                    action_groups[group_key].append({
                        "action": action,
                        "index": i,
                        "similarity": similarity
                    })
                    found_group = True
                    break
            
            # Create new group if not similar to any existing group
            if not found_group:
                action_groups[action].append({
                    "action": action,
                    "index": i,
                    "similarity": 1.0
                })
        
        # Check for pattern repetition
        for group_key, group_actions in action_groups.items():
            if len(group_actions) >= threshold:
                severity = TrapSeverity.CRITICAL if len(group_actions) >= 7 else TrapSeverity.WARNING
                avg_similarity = sum(a["similarity"] for a in group_actions) / len(group_actions)
                confidence = min(0.95, 0.6 + (len(group_actions) - threshold) * 0.05)
                
                return TrapDetection(
                    trap_type=TrapType.INFINITE_LOOP,
                    severity=severity,
                    confidence=confidence,
                    evidence={
                        "loop_type": "similar_action_pattern",
                        "pattern_key": group_key,
                        "pattern_count": len(group_actions),
                        "threshold": threshold,
                        "avg_similarity": avg_similarity,
                        "window": window,
                        "actions_in_pattern": [a["action"] for a in group_actions]
                    },
                    suggestion=f"Similar action pattern detected {len(group_actions)} times. Actions appear to be repeating with {avg_similarity:.1%} similarity. Consider changing approach."
                )
        
        return None
    
    def detect_error_loop(
        self,
        action_history: List[Dict[str, Any]],
        window: Optional[int] = None
    ) -> Optional[TrapDetection]:
        """
        Detect repeated failures (same error 3+ times from same action).
        
        Args:
            action_history: List of action records with 'action' and 'error' fields
            window: Number of recent actions to check
        
        Returns:
            TrapDetection if loop detected, None otherwise
        """
        loop_def = self.get_trap_definition(TrapType.INFINITE_LOOP)
        if not loop_def:
            return None
        
        if window is None:
            window = loop_def.detection_criteria.get("detection_window", 10)
        threshold = loop_def.detection_criteria.get("error_loop_threshold", 3)
        
        recent_actions = action_history[-window:] if len(action_history) > window else action_history
        
        # Track action-error pairs
        action_error_counts = defaultdict(int)
        action_error_details = defaultdict(list)
        
        for action_record in recent_actions:
            action = str(action_record.get("action", action_record))
            error = action_record.get("error")
            
            if error:
                error_key = str(error)
                pair_key = f"{action}::{error_key}"
                action_error_counts[pair_key] += 1
                action_error_details[pair_key].append({
                    "action": action,
                    "error": error_key,
                    "timestamp": action_record.get("timestamp", datetime.now().isoformat())
                })
        
        # Check for error loops
        for pair_key, count in action_error_counts.items():
            if count >= threshold:
                action, error = pair_key.split("::", 1)
                severity = TrapSeverity.CRITICAL if count >= 5 else TrapSeverity.WARNING
                confidence = min(0.9, 0.5 + (count - threshold) * 0.1)
                
                return TrapDetection(
                    trap_type=TrapType.INFINITE_LOOP,
                    severity=severity,
                    confidence=confidence,
                    evidence={
                        "loop_type": "error_loop",
                        "action": action,
                        "error": error,
                        "error_count": count,
                        "threshold": threshold,
                        "window": window,
                        "error_occurrences": action_error_details[pair_key]
                    },
                    suggestion=f"Action '{action}' has failed {count} times with error: '{error}'. Current approach is not working. Try a different solution."
                )
        
        return None
    
    def detect_reasoning_loop(
        self,
        decision_history: List[Dict[str, Any]],
        window: Optional[int] = None
    ) -> Optional[TrapDetection]:
        """
        Detect repeated reasoning (same decision factors).
        
        Args:
            decision_history: List of decision records with 'reasoning' or 'factors' field
            window: Number of recent decisions to check
        
        Returns:
            TrapDetection if loop detected, None otherwise
        """
        loop_def = self.get_trap_definition(TrapType.CIRCULAR_REASONING)
        if not loop_def:
            return None
        
        if window is None:
            window = loop_def.detection_criteria.get("cycle_detection_window", 15)
        threshold = 3  # Same reasoning 3+ times
        
        recent_decisions = decision_history[-window:] if len(decision_history) > window else decision_history
        
        # Extract and normalize reasoning/factors
        reasoning_patterns = []
        for decision in recent_decisions:
            reasoning = decision.get("reasoning") or decision.get("factors", {})
            reasoning_key = self._normalize_reasoning(reasoning)
            reasoning_patterns.append(reasoning_key)
        
        # Count reasoning patterns
        reasoning_counts = Counter(reasoning_patterns)
        
        # Check for repeated reasoning
        for reasoning, count in reasoning_counts.items():
            if count >= threshold and reasoning != "{}":  # Skip empty reasoning
                severity = TrapSeverity.CRITICAL if count >= 5 else TrapSeverity.WARNING
                confidence = min(0.85, 0.5 + (count - threshold) * 0.1)
                
                return TrapDetection(
                    trap_type=TrapType.CIRCULAR_REASONING,
                    severity=severity,
                    confidence=confidence,
                    evidence={
                        "loop_type": "reasoning_loop",
                        "reasoning_pattern": reasoning,
                        "repetition_count": count,
                        "threshold": threshold,
                        "window": window,
                        "decision_indices": [
                            i for i, r in enumerate(reasoning_patterns) 
                            if r == reasoning
                        ]
                    },
                    suggestion=f"Decision reasoning has repeated {count} times. Consider introducing new information or changing perspective."
                )
        
        return None
    
    def detect_infinite_recursion(
        self,
        decision_history: List[Dict[str, Any]],
        max_depth: int = 10
    ) -> Optional[TrapDetection]:
        """
        Detect infinite recursion in reasoning (decision depth too high).
        
        Args:
            decision_history: List of decision records with parent-child relationships
            max_depth: Maximum allowed decision depth
        
        Returns:
            TrapDetection if infinite recursion detected, None otherwise
        """
        # Build decision dependency graph
        decision_graph = {}
        for decision in decision_history:
            decision_id = decision.get("decision_id", id(decision))
            parent_id = decision.get("parent_id")
            decision_graph[decision_id] = parent_id
        
        # Check for cycles using DFS
        global_visited = set()
        has_any_cycle = False
        
        def check_cycle(node_id, recursion_stack):
            if node_id in recursion_stack:
                return True  # Cycle detected
            if node_id in global_visited:
                return False  # Already processed, no cycle
            
            global_visited.add(node_id)
            recursion_stack.add(node_id)
            
            parent_id = decision_graph.get(node_id)
            if parent_id:
                if check_cycle(parent_id, recursion_stack):
                    return True
            
            recursion_stack.remove(node_id)
            return False
        
        # Check for cycles
        for node_id in decision_graph:
            if check_cycle(node_id, set()):
                has_any_cycle = True
                break
        
        if has_any_cycle:
            return TrapDetection(
                trap_type=TrapType.CIRCULAR_REASONING,
                severity=TrapSeverity.CRITICAL,
                confidence=0.95,
                evidence={
                    "loop_type": "infinite_recursion",
                    "cycle_detected": True,
                    "decision_count": len(decision_history)
                },
                suggestion="Circular dependency detected in decision graph. Break cycle by documenting decisions or introducing new context."
            )
        
        # Calculate depth for each node independently
        def calculate_depth(node_id, current_depth=0):
            parent_id = decision_graph.get(node_id)
            if parent_id is None:
                return current_depth
            return calculate_depth(parent_id, current_depth + 1)
        
        max_actual_depth = 0
        for node_id in decision_graph:
            depth = calculate_depth(node_id)
            max_actual_depth = max(max_actual_depth, depth)
        
        if max_actual_depth >= max_depth:
            return TrapDetection(
                trap_type=TrapType.CIRCULAR_REASONING,
                severity=TrapSeverity.WARNING,
                confidence=0.8,
                evidence={
                    "loop_type": "excessive_depth",
                    "depth": max_actual_depth,
                    "max_allowed_depth": max_depth,
                    "decision_count": len(decision_history)
                },
                suggestion=f"Decision depth ({max_actual_depth}) exceeds threshold ({max_depth}). Consider simplifying decision hierarchy."
            )
        
        return None
    
    def detect_all_loops(
        self,
        action_history: Optional[List[Dict[str, Any]]] = None,
        decision_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[TrapDetection]:
        """
        Run all loop detection algorithms.
        
        Args:
            action_history: List of action records for action-based detection
            decision_history: List of decision records for reasoning-based detection
        
        Returns:
            List of all detected loops
        """
        detections = []
        
        if action_history:
            # Detect action-based loops
            exact_loop = self.detect_exact_action_loop(action_history)
            if exact_loop:
                detections.append(exact_loop)
            
            similar_loop = self.detect_similar_action_pattern(action_history)
            if similar_loop:
                detections.append(similar_loop)
            
            error_loop = self.detect_error_loop(action_history)
            if error_loop:
                detections.append(error_loop)
        
        if decision_history:
            # Detect reasoning-based loops
            reasoning_loop = self.detect_reasoning_loop(decision_history)
            if reasoning_loop:
                detections.append(reasoning_loop)
            
            recursion_loop = self.detect_infinite_recursion(decision_history)
            if recursion_loop:
                detections.append(recursion_loop)
        
        return detections
    
    # ========== DEAD END DETECTION METHODS (Task 4.3) ==========
    
    def detect_dead_end_no_progress(
        self,
        progress_history: List[Dict[str, Any]],
        threshold: Optional[int] = None
    ) -> Optional[TrapDetection]:
        """
        Detect dead end: no progress for extended period.
        
        Args:
            progress_history: List of progress records with 'progress' field (0-1)
            threshold: Number of operations with no progress (default from detection_criteria)
        
        Returns:
            TrapDetection if dead end detected, None otherwise
        """
        dead_end_def = self.get_trap_definition(TrapType.DEAD_END)
        if not dead_end_def:
            return None
        
        if threshold is None:
            threshold = dead_end_def.detection_criteria.get("no_progress_threshold", 5)
        
        if not progress_history:
            return None
        
        # Count operations with no meaningful progress across ALL operations
        # This is different from window-based detection - we check all operations
        no_progress_count = 0
        total_progress = 0.0
        progress_values = []
        
        for record in progress_history:
            progress = record.get("progress", 0)
            progress_values.append(progress)
            total_progress += progress
            
            # Consider progress < 5% as no meaningful progress
            if progress < 0.05:
                no_progress_count += 1
        
        # Check if we've had no progress for N operations
        if no_progress_count >= threshold:
            severity = TrapSeverity.BLOCKING if no_progress_count >= 10 else TrapSeverity.CRITICAL
            avg_progress = total_progress / len(progress_history) if progress_history else 0
            confidence = min(0.95, 0.6 + (no_progress_count - threshold) * 0.05)
            
            return TrapDetection(
                trap_type=TrapType.DEAD_END,
                severity=severity,
                confidence=confidence,
                evidence={
                    "dead_end_type": "no_progress",
                    "no_progress_count": no_progress_count,
                    "threshold": threshold,
                    "total_operations": len(progress_history),
                    "avg_progress": avg_progress,
                    "progress_values": progress_values[-threshold:],
                    "latest_progress": progress_values[-1] if progress_values else 0
                },
                suggestion=f"No meaningful progress detected for {no_progress_count} consecutive operations (threshold: {threshold}). Average progress: {avg_progress:.1%}. Consider backtracking to last successful state or trying a different approach."
            )
        
        return None
    
    def detect_dead_end_exhausted_options(
        self,
        action_history: List[Dict[str, Any]],
        available_actions: List[str],
        window: int = 20
    ) -> Optional[TrapDetection]:
        """
        Detect dead end: all attempted actions failed (exhausted action space).
        
        Args:
            action_history: List of action records with 'action' and 'success' fields
            available_actions: List of all possible actions that could be taken
            window: Number of recent actions to analyze
        
        Returns:
            TrapDetection if dead end detected, None otherwise
        """
        if not action_history:
            return None
        
        # Get recent actions based on window
        recent_actions = action_history[-window:] if len(action_history) > window else action_history
        attempts_analyzed = len(recent_actions)
        
        # Track attempted actions and their success
        attempted_actions = set()
        failed_action_count = 0  # Count of failed attempts (not unique actions)
        success_count = 0
        
        for record in recent_actions:
            action = str(record.get("action", record))
            success = record.get("success", True)
            
            attempted_actions.add(action)
            
            if not success:
                failed_action_count += 1
            else:
                success_count += 1
        
        # Check if all available actions have been attempted
        if available_actions and attempted_actions:
            unattempted_actions = set(available_actions) - attempted_actions
            all_attempted = len(unattempted_actions) == 0
        else:
            all_attempted = False
        
        # Check if we're approaching exhaustion (e.g., 90%+ attempted)
        if available_actions and attempted_actions:
            attempted_ratio = len(attempted_actions) / len(available_actions)
            near_exhaustion = attempted_ratio >= 0.9
        else:
            attempted_ratio = 0
            near_exhaustion = False
        
        # Check failure rate
        total_attempts = len(recent_actions)
        failure_rate = failed_action_count / total_attempts if total_attempts > 0 else 0
        
        # Detect dead end if:
        # 1. All actions attempted AND high failure rate
        # 2. Near exhaustion AND very high failure rate
        if (all_attempted and failure_rate >= 0.8) or (near_exhaustion and failure_rate >= 0.95):
            severity = TrapSeverity.BLOCKING if failure_rate >= 0.9 else TrapSeverity.CRITICAL
            confidence = min(0.95, 0.7 + failure_rate * 0.2)
            
            self.logger.debug(
                f"Dead end (exhausted_options) detected: all_attempted={all_attempted}, "
                f"failure_rate={failure_rate:.3f}, near_exhaustion={near_exhaustion}, "
                f"attempts_analyzed={attempts_analyzed}"
            )
            
            return TrapDetection(
                trap_type=TrapType.DEAD_END,
                severity=severity,
                confidence=confidence,
                evidence={
                    "dead_end_type": "exhausted_options",
                    "attempted_actions": len(attempted_actions),
                    "total_available": len(available_actions) if available_actions else 0,
                    "attempted_ratio": attempted_ratio,
                    "failed_action_count": failed_action_count,
                    "success_count": success_count,
                    "failure_rate": failure_rate,
                    "all_attempted": all_attempted,
                    "near_exhaustion": near_exhaustion,
                    "attempts_analyzed": attempts_analyzed
                },
                suggestion=f"Action space appears exhausted ({attempted_ratio:.1%} attempted, {failure_rate:.1%} failure rate). {failed_action_count} out of {total_attempts} recent actions have failed. Consider breaking task into smaller subtasks or asking for human intervention to explore new options."
            )
        
        self.logger.debug(
            f"Dead end (exhausted_options) NOT detected: all_attempted={all_attempted}, "
            f"failure_rate={failure_rate:.3f}, near_exhaustion={near_exhaustion}"
        )
        
        return None
    
    def detect_dead_end_resource_exhaustion(
        self,
        resource_metrics: Dict[str, Any],
        token_threshold: Optional[int] = None,
        time_threshold: Optional[float] = None
    ) -> Optional[TrapDetection]:
        """
        Detect dead end: resource exhaustion (tokens, time, compute).
        
        Args:
            resource_metrics: Dictionary with resource metrics:
                - tokens_used: Total tokens used
                - tokens_budget: Total token budget
                - time_elapsed: Time elapsed in seconds
                - time_budget: Total time budget in seconds
                - compute_usage: Compute resource usage percentage
            token_threshold: Minimum remaining tokens threshold (default 1000)
            time_threshold: Minimum remaining time threshold in seconds (default 300)
        
        Returns:
            TrapDetection if dead end detected, None otherwise
        """
        if not resource_metrics:
            return None
        
        if token_threshold is None:
            token_threshold = 1000
        if time_threshold is None:
            time_threshold = 300  # 5 minutes
        
        exhausted_resources = []
        resource_status = {}
        
        # Check token exhaustion
        tokens_used = resource_metrics.get("tokens_used", 0)
        tokens_budget = resource_metrics.get("tokens_budget", 0)
        if tokens_budget > 0:
            tokens_remaining = tokens_budget - tokens_used
            tokens_percentage = (tokens_remaining / tokens_budget) * 100
            resource_status["tokens_remaining"] = tokens_remaining
            resource_status["tokens_percentage"] = tokens_percentage
            
            if tokens_remaining <= token_threshold or tokens_percentage <= 5:
                exhausted_resources.append("tokens")
        
        # Check time exhaustion
        time_elapsed = resource_metrics.get("time_elapsed", 0)
        time_budget = resource_metrics.get("time_budget", 0)
        if time_budget > 0:
            time_remaining = time_budget - time_elapsed
            time_percentage = (time_remaining / time_budget) * 100
            resource_status["time_remaining"] = time_remaining
            resource_status["time_percentage"] = time_percentage
            
            if time_remaining <= time_threshold or time_percentage <= 5:
                exhausted_resources.append("time")
        
        # Check compute exhaustion
        compute_usage = resource_metrics.get("compute_usage", 0)
        if compute_usage >= 90:
            exhausted_resources.append("compute")
            resource_status["compute_usage"] = compute_usage
        
        # Detect dead end if any critical resource is exhausted
        if exhausted_resources:
            severity = TrapSeverity.BLOCKING
            confidence = 0.9
            
            return TrapDetection(
                trap_type=TrapType.DEAD_END,
                severity=severity,
                confidence=confidence,
                evidence={
                    "dead_end_type": "resource_exhaustion",
                    "exhausted_resources": exhausted_resources,
                    "resource_status": resource_status
                },
                suggestion=f"Resource exhaustion detected: {', '.join(exhausted_resources)}. {self._format_resource_exhaustion_message(exhausted_resources, resource_status)}"
            )
        
        return None
    
    def detect_dead_end_goal_unreachable(
        self,
        action_history: List[Dict[str, Any]],
        goal_state: Dict[str, Any],
        current_state: Dict[str, Any],
        window: int = 15
    ) -> Optional[TrapDetection]:
        """
        Detect dead end: analysis shows goal appears impossible to reach.
        
        This method analyzes whether the gap between current state and goal
        can be closed with available actions.
        
        Args:
            action_history: List of action records
            goal_state: Target state dictionary with required conditions
            current_state: Current state dictionary
            window: Number of recent actions to analyze
        
        Returns:
            TrapDetection if dead end detected, None otherwise
        """
        if not goal_state or not current_state:
            return None
        
        # Get recent actions
        recent_actions = action_history[-window:] if len(action_history) > window else action_history
        
        # Calculate state gap
        state_gap = self._calculate_state_gap(current_state, goal_state)
        
        # Calculate recent progress rate
        progress_rates = []
        for i in range(1, len(recent_actions)):
            prev_state = recent_actions[i-1].get("state_after", {})
            curr_state = recent_actions[i].get("state_after", {})
            
            if prev_state and curr_state and goal_state:
                prev_gap = self._calculate_state_gap(prev_state, goal_state)
                curr_gap = self._calculate_state_gap(curr_state, goal_state)
                
                if prev_gap > 0:
                    progress_rate = (prev_gap - curr_gap) / prev_gap
                    progress_rates.append(progress_rate)
        
        # Analyze if goal is reachable
        avg_progress_rate = sum(progress_rates) / len(progress_rates) if progress_rates else 0
        
        # Detect dead end if:
        # 1. State gap is large and not decreasing
        # 2. Progress rate is zero or negative
        # 3. Recent actions show no movement toward goal
        if (state_gap > 0.5 and avg_progress_rate <= 0.01) or \
           (len(progress_rates) >= 5 and all(rate <= 0 for rate in progress_rates[-5:])):
            severity = TrapSeverity.BLOCKING if avg_progress_rate <= 0 else TrapSeverity.CRITICAL
            confidence = min(0.9, 0.6 + (1 - state_gap) * 0.2)
            
            return TrapDetection(
                trap_type=TrapType.DEAD_END,
                severity=severity,
                confidence=confidence,
                evidence={
                    "dead_end_type": "goal_unreachable",
                    "state_gap": state_gap,
                    "avg_progress_rate": avg_progress_rate,
                    "recent_progress_rates": progress_rates[-10:] if progress_rates else [],
                    "actions_analyzed": len(recent_actions),
                    "current_state": current_state,
                    "goal_state": goal_state
                },
                suggestion=f"Goal appears unreachable with current approach. State gap: {state_gap:.1%}, avg progress rate: {avg_progress_rate:.2%}. Current actions are not effectively moving toward goal. Consider backtracking, changing strategy, or breaking task into smaller subgoals."
            )
        
        return None
    
    def detect_all_dead_ends(
        self,
        progress_history: Optional[List[Dict[str, Any]]] = None,
        action_history: Optional[List[Dict[str, Any]]] = None,
        available_actions: Optional[List[str]] = None,
        resource_metrics: Optional[Dict[str, Any]] = None,
        goal_state: Optional[Dict[str, Any]] = None,
        current_state: Optional[Dict[str, Any]] = None
    ) -> List[TrapDetection]:
        """
        Run all dead end detection algorithms.
        
        Args:
            progress_history: List of progress records for no-progress detection
            action_history: List of action records for exhausted options detection
            available_actions: List of all possible actions for exhausted options detection
            resource_metrics: Resource metrics for resource exhaustion detection
            goal_state: Target state for goal unreachable detection
            current_state: Current state for goal unreachable detection
        
        Returns:
            List of all detected dead ends
        """
        detections = []
        
        if progress_history:
            # Detect no progress dead end
            no_progress = self.detect_dead_end_no_progress(progress_history)
            if no_progress:
                detections.append(no_progress)
        
        if action_history and available_actions:
            # Detect exhausted options dead end
            exhausted = self.detect_dead_end_exhausted_options(
                action_history,
                available_actions
            )
            if exhausted:
                detections.append(exhausted)
        
        if resource_metrics:
            # Detect resource exhaustion dead end
            resource_dead_end = self.detect_dead_end_resource_exhaustion(resource_metrics)
            if resource_dead_end:
                detections.append(resource_dead_end)
        
        if action_history and goal_state and current_state:
            # Detect goal unreachable dead end
            goal_unreachable = self.detect_dead_end_goal_unreachable(
                action_history,
                goal_state,
                current_state
            )
            if goal_unreachable:
                detections.append(goal_unreachable)
        
        return detections
    
    def _format_resource_exhaustion_message(
        self,
        exhausted_resources: List[str],
        resource_status: Dict[str, Any]
    ) -> str:
        """
        Format a human-readable resource exhaustion message.
        
        Args:
            exhausted_resources: List of exhausted resource types
            resource_status: Detailed resource status
        
        Returns:
            Formatted message string
        """
        messages = []
        
        for resource in exhausted_resources:
            if resource == "tokens":
                remaining = resource_status.get("tokens_remaining", 0)
                percentage = resource_status.get("tokens_percentage", 0)
                messages.append(f"Tokens: {remaining} remaining ({percentage:.1f}%)")
            elif resource == "time":
                remaining = resource_status.get("time_remaining", 0)
                percentage = resource_status.get("time_percentage", 0)
                minutes = remaining / 60
                messages.append(f"Time: {minutes:.1f} minutes remaining ({percentage:.1f}%)")
            elif resource == "compute":
                usage = resource_status.get("compute_usage", 0)
                messages.append(f"Compute: {usage:.1f}% used")
        
        base_msg = ". ".join(messages)
        return base_msg + ". Consider backtracking to checkpoint or requesting additional resources."
    
    def _calculate_state_gap(
        self,
        current_state: Dict[str, Any],
        goal_state: Dict[str, Any]
    ) -> float:
        """
        Calculate the gap between current state and goal state.
        
        Gap is calculated as:
        - For each key in goal_state, compare to current_state
        - Normalize to 0-1 range (0 = at goal, 1 = far from goal)
        
        Args:
            current_state: Current state dictionary
            goal_state: Goal state dictionary
        
        Returns:
            State gap between 0 and 1
        """
        if not goal_state:
            return 0.0
        
        gaps = []
        
        for key, goal_value in goal_state.items():
            current_value = current_state.get(key)
            
            if isinstance(goal_value, bool):
                # Boolean: gap is 1 if not matched, 0 if matched
                gap = 0.0 if current_value == goal_value else 1.0
                gaps.append(gap)
            
            elif isinstance(goal_value, (int, float)):
                # Numeric: normalize gap
                if current_value is None:
                    gap = 1.0
                else:
                    # Assume goal_value is target, current should be close
                    # If both are zero, gap is 0
                    if goal_value == 0 and current_value == 0:
                        gap = 0.0
                    elif goal_value == 0:
                        gap = abs(current_value)
                    else:
                        gap = abs(goal_value - current_value) / max(abs(goal_value), 1.0)
                gaps.append(min(gap, 1.0))
            
            elif isinstance(goal_value, (list, set, dict)):
                # Collection: check if current is subset or matches
                if isinstance(goal_value, set):
                    if isinstance(current_value, set):
                        missing = goal_value - current_value
                        gap = len(missing) / len(goal_value) if goal_value else 0
                    else:
                        gap = 1.0
                elif isinstance(goal_value, list):
                    if isinstance(current_value, list):
                        gap = len(set(goal_value) - set(current_value)) / len(goal_value) if goal_value else 0
                    else:
                        gap = 1.0
                else:  # dict
                    if isinstance(current_value, dict):
                        gap = 1.0 - (len(current_value) / len(goal_value) if goal_value else 0)
                    else:
                        gap = 1.0
                gaps.append(gap)
            
            else:
                # String or other: exact match required
                gap = 0.0 if current_value == goal_value else 1.0
                gaps.append(gap)
        
        # Average gap across all keys
        return sum(gaps) / len(gaps) if gaps else 0.0
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings.
        
        Uses a combination of:
        - Jaccard similarity for word sets
        - Character n-gram overlap
        
        Args:
            str1: First string
            str2: Second string
        
        Returns:
            Similarity score between 0 and 1
        """
        # Convert to lowercase and tokenize
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity for word sets
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard = len(intersection) / len(union)
        
        # Character n-gram similarity (n=2)
        def get_ngrams(s, n):
            return set(s[i:i+n] for i in range(len(s)-n+1))
        
        ngrams1 = get_ngrams(str1.lower(), 2)
        ngrams2 = get_ngrams(str2.lower(), 2)
        
        if not ngrams1 and not ngrams2:
            ngram_sim = 1.0
        elif not ngrams1 or not ngrams2:
            ngram_sim = 0.0
        else:
            ngram_intersection = ngrams1.intersection(ngrams2)
            ngram_union = ngrams1.union(ngrams2)
            ngram_sim = len(ngram_intersection) / len(ngram_union)
        
        # Weighted average (70% Jaccard, 30% n-gram)
        return 0.7 * jaccard + 0.3 * ngram_sim
    
    def _normalize_reasoning(self, reasoning: Any) -> str:
        """
        Normalize reasoning factors for comparison.
        
        Args:
            reasoning: Reasoning data (dict, list, or string)
        
        Returns:
            Normalized string representation
        """
        if isinstance(reasoning, dict):
            # Sort keys and create canonical representation
            items = []
            for key in sorted(reasoning.keys()):
                value = reasoning[key]
                if isinstance(value, (list, dict)):
                    items.append(f"{key}:{str(value)}")
                else:
                    items.append(f"{key}:{value}")
            return "{" + ",".join(items) + "}"
        elif isinstance(reasoning, list):
            # Sort and join list items
            return "[" + ",".join(sorted(str(item) for item in reasoning)) + "]"
        else:
            # String or other type
            return str(reasoning).strip().lower()


def create_trap_detector() -> TrapDetector:
    """
    Factory function to create a TrapDetector instance.
    
    Returns:
        Configured TrapDetector instance
    """
    return TrapDetector()