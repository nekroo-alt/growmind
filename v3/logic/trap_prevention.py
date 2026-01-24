"""
Trap Prevention System for L4D V4

This module implements proactive prevention mechanisms to avoid traps
before they occur. It tracks attempted actions, validates progress,
maintains decision history, freezes task scope, and provides warnings
for high-risk actions.

Key Prevention Strategies:
- Action History Tracking: Prevent loops by tracking attempted actions
- Progress Validation: Prevent dead ends by early progress validation
- Decision Documentation: Prevent circular reasoning by maintaining history
- Scope Freeze: Prevent scope creep by freezing task scope
- Warning System: Warn before high-risk actions
- Learning: Learn from past traps to prevent recurrence
"""

from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
import hashlib
import json

from .trap_detector import TrapType, TrapSeverity, TrapDetector

logger = logging.getLogger(__name__)


class PreventionLevel(Enum):
    """Level of prevention intervention."""
    INFO = "info"           # Informational warning
    WARNING = "warning"       # Warning, may proceed
    BLOCKING = "blocking"     # Action should be blocked


class PreventionType(Enum):
    """Types of prevention mechanisms."""
    ACTION_REPETITION = "action_repetition"
    PROGRESS_VALIDATION = "progress_validation"
    DECISION_CYCLE = "decision_cycle"
    SCOPE_CREEP = "scope_creep"
    HIGH_RISK_ACTION = "high_risk_action"
    PATTERN_DETECTED = "pattern_detected"


@dataclass
class PreventionAction:
    """Action taken by prevention system."""
    prevention_type: PreventionType
    level: PreventionLevel
    message: str
    suggestion: str
    blocked: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __repr__(self) -> str:
        status = "BLOCKED" if self.blocked else "ALLOWED"
        return f"PreventionAction({self.prevention_type.value.upper()}, {self.level.value.upper()}, {status})"


@dataclass
class TrapPattern:
    """Learned trap pattern from past occurrences."""
    pattern_id: str
    trap_type: TrapType
    task_type: str
    pattern_signature: str
    occurrence_count: int = 0
    last_occurrence: Optional[datetime] = None
    confidence: float = 0.0
    context_features: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"TrapPattern({self.trap_type.value}, count={self.occurrence_count}, conf={self.confidence:.2f})"


class TrapPrevention:
    """
    Main trap prevention system that proactively prevents traps.
    
    This component is part of V4 adaptive reasoning system and provides
    comprehensive prevention capabilities with learning from past traps.
    """
    
    def __init__(
        self,
        max_history_size: int = 100,
        progress_minimal_threshold: float = 0.1,
        progress_expected_threshold: float = 0.3,
        max_scope_expansions: int = 3,
        learning_enabled: bool = True
    ):
        """
        Initialize trap prevention system.
        
        Args:
            max_history_size: Maximum number of items to keep in history
            progress_minimal_threshold: Minimal progress threshold (0.1 = 10%)
            progress_expected_threshold: Expected progress threshold (0.3 = 30%)
            max_scope_expansions: Maximum number of scope expansions allowed
            learning_enabled: Enable learning from past traps
        """
        self.max_history_size = max_history_size
        self.progress_minimal_threshold = progress_minimal_threshold
        self.progress_expected_threshold = progress_expected_threshold
        self.max_scope_expansions = max_scope_expansions
        self.learning_enabled = learning_enabled
        
        # Action history for loop prevention
        self.action_history: deque = deque(maxlen=max_history_size)
        self.action_fingerprints: Dict[str, List[datetime]] = defaultdict(list)
        
        # Decision history for circular reasoning prevention
        self.decision_history: deque = deque(maxlen=max_history_size)
        self.decision_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.rejected_options: Dict[str, List[datetime]] = defaultdict(list)
        
        # Progress tracking for dead end prevention
        self.progress_history: deque = deque(maxlen=max_history_size)
        self.last_significant_progress: Optional[datetime] = None
        
        # Scope tracking for scope creep prevention
        self.initial_scope: Optional[Dict[str, Any]] = None
        self.current_scope: Optional[Dict[str, Any]] = None
        self.scope_expansion_count: int = 0
        self.scope_changes: List[Dict[str, Any]] = []
        
        # Trap pattern learning
        self.trap_patterns: Dict[str, TrapPattern] = {}
        self.task_trap_stats: Dict[str, Dict[TrapType, int]] = defaultdict(lambda: defaultdict(int))
        
        # Warning callbacks
        self.warning_callbacks: List[Callable[[PreventionAction], None]] = []
        
        # Initialize trap detector for analysis
        self.trap_detector = TrapDetector()
        
        self.logger = logger
    
    # ========== ACTION HISTORY TRACKING (Prevent Loops) ==========
    
    def track_action(self, action: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Track an action for loop prevention.
        
        Args:
            action: Action taken (string, dict, or any object)
            metadata: Additional metadata about the action
        """
        action_record = {
            "action": str(action),
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.action_history.append(action_record)
        
        # Track action fingerprint
        fingerprint = self._calculate_action_fingerprint(action)
        self.action_fingerprints[fingerprint].append(datetime.now())
        
        # Cleanup old fingerprints
        self._cleanup_old_fingerprints()
    
    def check_action_repetition(
        self,
        action: Any,
        threshold: int = 3
    ) -> Optional[PreventionAction]:
        """
        Check if action would create a loop.
        
        Args:
            action: Action being considered
            threshold: Maximum allowed repetitions
        
        Returns:
            PreventionAction if repetition detected, None otherwise
        """
        fingerprint = self._calculate_action_fingerprint(action)
        repetitions = len(self.action_fingerprints.get(fingerprint, []))
        
        if repetitions >= threshold:
            level = PreventionLevel.BLOCKING if repetitions >= threshold + 2 else PreventionLevel.WARNING
            
            return PreventionAction(
                prevention_type=PreventionType.ACTION_REPETITION,
                level=level,
                message=f"Action '{str(action)[:50]}...' has been attempted {repetitions} times (threshold: {threshold})",
                suggestion=f"This action appears to be repeating. Consider:\n"
                          f"  1. Trying a different approach\n"
                          f"  2. Investigating why this action is being repeated\n"
                          f"  3. Backtracking to a different state",
                blocked=(level == PreventionLevel.BLOCKING)
            )
        
        return None
    
    def _calculate_action_fingerprint(self, action: Any) -> str:
        """
        Calculate a fingerprint for an action.
        
        Args:
            action: Action to fingerprint
        
        Returns:
            Fingerprint string
        """
        # Convert action to string and normalize
        action_str = str(action).strip().lower()
        
        # Remove variable parts (timestamps, IDs, etc.)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', action_str)
        normalized = re.sub(r'\d+', 'NUM', normalized)
        normalized = re.sub(r'[a-f0-9]{8,}', 'ID', normalized)
        
        # Create hash
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _cleanup_old_fingerprints(self, max_age_hours: int = 24) -> None:
        """Clean up old action fingerprints."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        for fingerprint in list(self.action_fingerprints.keys()):
            self.action_fingerprints[fingerprint] = [
                ts for ts in self.action_fingerprints[fingerprint]
                if ts > cutoff
            ]
            
            if not self.action_fingerprints[fingerprint]:
                del self.action_fingerprints[fingerprint]
    
    # ========== PROGRESS VALIDATION (Prevent Dead Ends) ==========
    
    def track_progress(self, progress: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Track progress for dead end prevention.
        
        Args:
            progress: Progress value (0-1)
            metadata: Additional metadata about progress
        """
        progress_record = {
            "progress": max(0.0, min(1.0, progress)),
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.progress_history.append(progress_record)
        
        # Track significant progress
        if progress >= self.progress_expected_threshold:
            self.last_significant_progress = datetime.now()
    
    def check_progress_validation(
        self,
        progress: float,
        window: int = 5
    ) -> Optional[PreventionAction]:
        """
        Check if progress meets minimum threshold.
        
        Args:
            progress: Progress value (0-1)
            window: Number of recent operations to check
        
        Returns:
            PreventionAction if progress is too low, None otherwise
        """
        if progress < self.progress_minimal_threshold:
            # Check if we've had low progress for consecutive operations
            recent_progress = [
                p["progress"] for p in self.progress_history
            ][-window:] if self.progress_history else []
            
            low_progress_count = sum(1 for p in recent_progress if p < self.progress_minimal_threshold)
            
            level = PreventionLevel.WARNING if low_progress_count == window - 1 else PreventionLevel.BLOCKING
            
            return PreventionAction(
                prevention_type=PreventionType.PROGRESS_VALIDATION,
                level=level,
                message=f"Progress ({progress:.1%}) is below minimal threshold ({self.progress_minimal_threshold:.1%}). Low progress count: {low_progress_count}/{window}",
                suggestion=f"Progress is insufficient. Consider:\n"
                          f"  1. Backtracking to last successful state\n"
                          f"  2. Breaking task into smaller subtasks\n"
                          f"  3. Trying a different approach\n"
                          f"  4. Checking if goal is achievable with current constraints",
                blocked=(level == PreventionLevel.BLOCKING)
            )
        
        return None
    
    def check_progress_stagnation(
        self,
        stagnation_threshold_minutes: int = 15
    ) -> Optional[PreventionAction]:
        """
        Check if progress has stagnated.
        
        Args:
            stagnation_threshold_minutes: Minutes since last significant progress
        
        Returns:
            PreventionAction if stagnated, None otherwise
        """
        if self.last_significant_progress:
            time_since_progress = datetime.now() - self.last_significant_progress
            minutes_since_progress = time_since_progress.total_seconds() / 60
            
            if minutes_since_progress >= stagnation_threshold_minutes:
                level = PreventionLevel.BLOCKING if minutes_since_progress >= stagnation_threshold_minutes * 2 else PreventionLevel.WARNING
                
                return PreventionAction(
                    prevention_type=PreventionType.PROGRESS_VALIDATION,
                    level=level,
                    message=f"No significant progress for {minutes_since_progress:.1f} minutes (threshold: {stagnation_threshold_minutes} minutes)",
                    suggestion=f"Progress has stagnated. Consider:\n"
                              f"  1. Backtracking to last successful checkpoint\n"
                              f"  2. Requesting human intervention\n"
                              f"  3. Breaking current task into smaller steps",
                    blocked=(level == PreventionLevel.BLOCKING)
                )
        
        return None
    
    # ========== DECISION HISTORY (Prevent Circular Reasoning) ==========
    
    def track_decision(
        self,
        decision: Any,
        reasoning: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        alternatives: Optional[List[str]] = None
    ) -> None:
        """
        Track a decision for circular reasoning prevention.
        
        Args:
            decision: Decision made
            reasoning: Reasoning behind the decision
            depends_on: List of decisions this decision depends on
            alternatives: List of alternative options considered
        """
        decision_id = self._calculate_decision_fingerprint(decision)
        
        decision_record = {
            "decision": str(decision),
            "decision_id": decision_id,
            "reasoning": reasoning or {},
            "depends_on": depends_on or [],
            "alternatives": alternatives or [],
            "timestamp": datetime.now()
        }
        self.decision_history.append(decision_record)
        
        # Track decision dependencies
        for dep_id in (depends_on or []):
            self.decision_dependencies[decision_id].add(dep_id)
        
        # Track rejected options
        for alternative in (alternatives or []):
            alt_fingerprint = self._calculate_decision_fingerprint(alternative)
            self.rejected_options[alt_fingerprint].append(datetime.now())
    
    def check_decision_cycle(
        self,
        decision: Any,
        depends_on: Optional[List[str]] = None
    ) -> Optional[PreventionAction]:
        """
        Check if decision would create a cycle.
        
        Args:
            decision: Decision being considered
            depends_on: Dependencies of this decision
        
        Returns:
            PreventionAction if cycle detected, None otherwise
        """
        decision_id = self._calculate_decision_fingerprint(decision)
        
        # Check if this decision would create a dependency cycle
        if depends_on:
            for dep_id in depends_on:
                if self._would_create_cycle(decision_id, dep_id):
                    return PreventionAction(
                        prevention_type=PreventionType.DECISION_CYCLE,
                        level=PreventionLevel.BLOCKING,
                        message=f"Decision '{str(decision)[:50]}...' would create a dependency cycle",
                        suggestion=f"This decision depends on '{dep_id[:20]}...' which would create a circular dependency. Break cycle by:\n"
                                  f"  1. Removing one of dependencies\n"
                                  f"  2. Restructuring decision hierarchy\n"
                                  f"  3. Creating a separate independent decision",
                        blocked=True
                    )
        
        return None
    
    def check_revisiting_rejected(self, decision: Any) -> Optional[PreventionAction]:
        """
        Check if decision was previously rejected.
        
        Args:
            decision: Decision being considered
        
        Returns:
            PreventionAction if revisiting rejected option, None otherwise
        """
        decision_fingerprint = self._calculate_decision_fingerprint(decision)
        rejection_count = len(self.rejected_options.get(decision_fingerprint, []))
        
        if rejection_count > 0:
            last_rejection = self.rejected_options[decision_fingerprint][-1]
            time_since_rejection = datetime.now() - last_rejection
            
            # Warn if recently rejected
            if time_since_rejection < timedelta(minutes=30):
                return PreventionAction(
                    prevention_type=PreventionType.DECISION_CYCLE,
                    level=PreventionLevel.WARNING,
                    message=f"Decision '{str(decision)[:50]}...' was rejected {rejection_count} time(s) as recently as {time_since_rejection.total_seconds()/60:.1f} minutes ago",
                    suggestion=f"This decision was previously rejected. Consider:\n"
                              f"  1. Reviewing why it was rejected\n"
                              f"  2. Checking if conditions have changed\n"
                              f"  3. Exploring alternative approaches\n"
                              f"  4. Documenting decision rationale to prevent revisit",
                    blocked=False
                )
        
        return None
    
    def _calculate_decision_fingerprint(self, decision: Any) -> str:
        """
        Calculate a fingerprint for a decision.
        
        Args:
            decision: Decision to fingerprint
        
        Returns:
            Fingerprint string
        """
        decision_str = str(decision).strip().lower()
        return hashlib.md5(decision_str.encode()).hexdigest()
    
    def _would_create_cycle(self, decision_id: str, dep_id: str) -> bool:
        """
        Check if adding dependency would create a cycle.
        
        Args:
            decision_id: New decision ID (the one we're adding a dependency to)
            dep_id: Dependency ID (the one we're adding as a dependency)
        
        Returns:
            True if cycle would be created, False otherwise
        """
        # The dependencies dict represents: X -> {Y} means "X depends on Y"
        # We're adding: decision_id depends on dep_id
        # This would create a cycle if dep_id can already reach decision_id
        # Example: A <- B (B depends on A)
        #          Adding A depends on B creates: A <- B and B <- A (cycle!)
        #          Because we're adding: A -> B and we already have B -> A
        
        # Special case: if decision_id and dep_id are the same, definitely a cycle
        if decision_id == dep_id:
            return True
        
        # Check if dep_id already depends on decision_id (direct cycle)
        if dep_id in self.decision_dependencies and decision_id in self.decision_dependencies[dep_id]:
            return True
        
        # Check if dep_id can reach decision_id through existing dependencies (indirect cycle)
        # This finds all decisions that dep_id indirectly depends on
        return self._can_reach_reverse(dep_id, decision_id)
    
    def _can_reach(self, start_id: str, target_id: str) -> bool:
        """
        Check if start_id can reach target_id through dependencies.
        
        Args:
            start_id: Starting decision ID
            target_id: Target decision ID
        
        Returns:
            True if path exists, False otherwise
        """
        # If start_id doesn't exist in dependencies, can't reach anything
        if start_id not in self.decision_dependencies:
            return False
        
        if start_id == target_id:
            return True
        
        visited = set()
        
        def dfs(current_id: str) -> bool:
            """Depth-first search to find path."""
            if current_id == target_id:
                return True
            if current_id in visited:
                return False
            
            visited.add(current_id)
            
            # Follow all dependencies from current_id
            for next_id in self.decision_dependencies.get(current_id, set()):
                if dfs(next_id):
                    return True
            
            return False
        
        return dfs(start_id)
    
    def _can_reach_reverse(self, start_id: str, target_id: str) -> bool:
        """
        Check if start_id can reach target_id through reverse dependencies.
        This finds all decisions that depend on start_id.
        
        Args:
            start_id: Starting decision ID
            target_id: Target decision ID
        
        Returns:
            True if path exists, False otherwise
        """
        if start_id == target_id:
            return True
        
        visited = set()
        
        def dfs_reverse(current_id: str) -> bool:
            """Depth-first search to find path through reverse dependencies."""
            if current_id == target_id:
                return True
            if current_id in visited:
                return False
            
            visited.add(current_id)
            
            # Find all decisions that depend on current_id
            for decision_id, dependencies in self.decision_dependencies.items():
                if current_id in dependencies:
                    if dfs_reverse(decision_id):
                        return True
            
            return False
        
        return dfs_reverse(start_id)
    
    # ========== SCOPE FREEZE (Prevent Scope Creep) ==========
    
    def initialize_scope(self, scope: Dict[str, Any]) -> None:
        """
        Initialize and freeze task scope.
        
        Args:
            scope: Initial task scope
        """
        self.initial_scope = scope.copy()
        self.current_scope = scope.copy()
        self.scope_expansion_count = 0
        self.scope_changes = []
        
        self.logger.info(f"Task scope initialized: {json.dumps(scope, indent=2)}")
    
    def check_scope_expansion(
        self,
        new_scope: Dict[str, Any],
        require_approval: bool = False
    ) -> Optional[PreventionAction]:
        """
        Check if scope change is an expansion.
        
        Args:
            new_scope: Proposed new scope
            require_approval: Whether to require human approval
        
        Returns:
            PreventionAction if expansion detected, None otherwise
        """
        if self.current_scope is None:
            self.initialize_scope(new_scope)
            return None
        
        # Check for scope expansion
        expansion_changes = self._detect_scope_changes(
            self.current_scope,
            new_scope
        )
        
        if expansion_changes:
            self.scope_expansion_count += 1
            self.scope_changes.append({
                "changes": expansion_changes,
                "timestamp": datetime.now(),
                "expansion_number": self.scope_expansion_count
            })
            
            # Update current scope if not blocked
            self.current_scope = new_scope.copy()
            
            # Check if we've exceeded maximum expansions
            if self.scope_expansion_count >= self.max_scope_expansions:
                return PreventionAction(
                    prevention_type=PreventionType.SCOPE_CREEP,
                    level=PreventionLevel.BLOCKING,
                    message=f"Scope has expanded {self.scope_expansion_count} times (maximum: {self.max_scope_expansions})",
                    suggestion=f"Scope creep detected. To prevent further expansion:\n"
                              f"  1. Freeze current scope and break remaining work into separate tasks\n"
                              f"  2. Defer non-critical additions to future iterations\n"
                              f"  3. Request human approval for critical scope changes\n"
                              f"  4. Re-evaluate task priorities",
                    blocked=True
                )
            else:
                level = PreventionLevel.WARNING if require_approval else PreventionLevel.INFO
                
                return PreventionAction(
                    prevention_type=PreventionType.SCOPE_CREEP,
                    level=level,
                    message=f"Scope expanded ({self.scope_expansion_count}/{self.max_scope_expansions} expansions): {len(expansion_changes)} changes",
                    suggestion=f"Scope is expanding. Changes detected:\n" + 
                              "\n".join(f"  - {change}" for change in expansion_changes[:5]) +
                              f"\n\nConsider freezing scope and breaking into separate tasks.",
                    blocked=False
                )
        
        return None
    
    def _detect_scope_changes(
        self,
        old_scope: Dict[str, Any],
        new_scope: Dict[str, Any]
    ) -> List[str]:
        """
        Detect scope changes (expansions).
        
        Args:
            old_scope: Previous scope
            new_scope: New scope
        
        Returns:
            List of expansion change descriptions
        """
        changes = []
        
        # Check for new keys (expansion)
        new_keys = set(new_scope.keys()) - set(old_scope.keys())
        for key in new_keys:
            changes.append(f"Added requirement: {key} = {new_scope[key]}")
        
        # Check for value changes
        for key in set(old_scope.keys()) & set(new_scope.keys()):
            old_val = old_scope[key]
            new_val = new_scope[key]
            
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                if new_val > old_val * 1.1:  # 10% increase
                    changes.append(f"Increased requirement: {key} from {old_val} to {new_val}")
            elif isinstance(old_val, list) and isinstance(new_val, list):
                if len(new_val) > len(old_val):
                    new_items = set(new_val) - set(old_val)
                    changes.append(f"Added items to {key}: {new_items}")
            elif old_val != new_val:
                changes.append(f"Changed requirement: {key} from {old_val} to {new_val}")
        
        return changes
    
    # ========== HIGH-RISK ACTION WARNING ==========
    
    def check_high_risk_action(
        self,
        action: Any,
        risk_factors: Optional[Dict[str, Any]] = None
    ) -> Optional[PreventionAction]:
        """
        Check if action has high risk factors.
        
        Args:
            action: Action being considered
            risk_factors: Dictionary of risk factors with values
        
        Returns:
            PreventionAction if high risk detected, None otherwise
        """
        if not risk_factors:
            return None
        
        risk_score = 0.0
        risk_descriptions = []
        
        # Analyze risk factors
        if risk_factors.get("destructive", False):
            risk_score += 0.5
            risk_descriptions.append("Destructive operation (modifies/deletes data)")
        
        if risk_factors.get("irreversible", False):
            risk_score += 0.4
            risk_descriptions.append("Irreversible operation (cannot be easily undone)")
        
        if risk_factors.get("external_resource", False):
            risk_score += 0.3
            risk_descriptions.append("External resource access (network/external API)")
        
        if risk_factors.get("large_scale", False):
            risk_score += 0.3
            risk_descriptions.append("Large-scale operation (affects many files/components)")
        
        if risk_factors.get("experimental", False):
            risk_score += 0.2
            risk_descriptions.append("Experimental/untested approach")
        
        if risk_factors.get("complexity", 0) > 7:
            risk_score += 0.3
            risk_descriptions.append(f"High complexity (score: {risk_factors['complexity']})")
        
        # Check if high risk
        if risk_score >= 0.5:
            level = PreventionLevel.BLOCKING if risk_score >= 0.8 else PreventionLevel.WARNING
            
            return PreventionAction(
                prevention_type=PreventionType.HIGH_RISK_ACTION,
                level=level,
                message=f"High-risk action detected: '{str(action)[:50]}...' (risk score: {risk_score:.2f})",
                suggestion=f"This action has the following risk factors:\n" + 
                          "\n".join(f"  - {desc}" for desc in risk_descriptions) +
                          f"\n\nRecommendations:\n"
                          f"  1. Create checkpoint before proceeding\n"
                          f"  2. Review and test in isolated environment\n"
                          f"  3. Have rollback plan ready\n"
                          f"  4. Consider human approval for critical actions",
                blocked=(level == PreventionLevel.BLOCKING)
            )
        
        return None
    
    # ========== LEARNING FROM PAST TRAPS ==========
    
    def record_trap_occurrence(
        self,
        trap_type: TrapType,
        task_type: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Record trap occurrence for learning.
        
        Args:
            trap_type: Type of trap that occurred
            task_type: Type of task being performed
            context: Context in which trap occurred
        """
        # Update task statistics
        self.task_trap_stats[task_type][trap_type] += 1
        
        # Create or update pattern
        pattern_signature = self._calculate_pattern_signature(trap_type, context)
        
        if pattern_signature in self.trap_patterns:
            pattern = self.trap_patterns[pattern_signature]
            pattern.occurrence_count += 1
            pattern.last_occurrence = datetime.now()
            
            # Update confidence based on recurrence
            pattern.confidence = min(0.95, 0.5 + pattern.occurrence_count * 0.1)
        else:
            pattern = TrapPattern(
                pattern_id=pattern_signature,
                trap_type=trap_type,
                task_type=task_type,
                pattern_signature=pattern_signature,
                occurrence_count=1,
                last_occurrence=datetime.now(),
                confidence=0.5,
                context_features=self._extract_context_features(context)
            )
            self.trap_patterns[pattern_signature] = pattern
        
        self.logger.info(
            f"Recorded trap occurrence: {trap_type.value} for task {task_type}. "
            f"Pattern confidence: {pattern.confidence:.2f}"
        )
    
    def check_pattern_match(
        self,
        task_type: str,
        current_context: Dict[str, Any]
    ) -> Optional[PreventionAction]:
        """
        Check if current context matches a known trap pattern.
        
        Args:
            task_type: Type of task being performed
            current_context: Current context
        
        Returns:
            PreventionAction if pattern match found, None otherwise
        """
        if not self.learning_enabled:
            return None
        
        # Calculate current context signature
        current_signature = self._calculate_context_signature(current_context)
        
        # Check for pattern matches
        for pattern_id, pattern in self.trap_patterns.items():
            if pattern.task_type != task_type:
                continue
            
            # Calculate current context features for comparison
            current_features = self._extract_context_features(current_context)
            
            # Compare signatures and features
            similarity = self._calculate_signature_similarity(
                current_signature,
                pattern.pattern_signature,
                current_features,
                pattern.context_features
            )
            
            # If high similarity and high confidence, warn about potential trap
            if similarity >= 0.7 and pattern.confidence >= 0.7:
                level = PreventionLevel.BLOCKING if similarity >= 0.9 and pattern.confidence >= 0.9 else PreventionLevel.WARNING
                
                trap_def = self.trap_detector.get_trap_definition(pattern.trap_type)
                prevention_strategies = trap_def.prevention_strategies if trap_def else []
                
                return PreventionAction(
                    prevention_type=PreventionType.PATTERN_DETECTED,
                    level=level,
                    message=f"Current context matches known trap pattern ({pattern.trap_type.value}) with {similarity:.1%} similarity. Pattern confidence: {pattern.confidence:.1%} (occurred {pattern.occurrence_count} times)",
                    suggestion=f"This situation has led to a {pattern.trap_type.value} in the past.\n"
                              f"Prevention strategies:\n" +
                              "\n".join(f"  {i+1}. {s}" for i, s in enumerate(prevention_strategies)) +
                              f"\n\nContext features:\n" +
                              "\n".join(f"  - {k}: {v}" for k, v in pattern.context_features.items()),
                    blocked=(level == PreventionLevel.BLOCKING)
                )
        
        return None
    
    def _calculate_pattern_signature(
        self,
        trap_type: TrapType,
        context: Dict[str, Any]
    ) -> str:
        """Calculate signature for trap pattern."""
        features = self._extract_context_features(context)
        signature_data = {
            "trap_type": trap_type.value,
            "features": features
        }
        return hashlib.md5(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()
    
    def _calculate_context_signature(self, context: Dict[str, Any]) -> str:
        """Calculate signature for current context."""
        features = self._extract_context_features(context)
        return hashlib.md5(json.dumps(features, sort_keys=True).encode()).hexdigest()
    
    def _extract_context_features(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant features from context."""
        features = {}
        
        # Extract key features
        feature_keys = [
            "task_type", "action_type", "error_type",
            "decision_type", "resource_state", "progress_rate"
        ]
        
        for key in feature_keys:
            if key in context:
                features[key] = context[key]
        
        # Extract numerical features
        for key, value in context.items():
            if isinstance(value, (int, float)) and key not in features:
                features[key] = value
        
        return features
    
    def _calculate_signature_similarity(
        self,
        sig1: str,
        sig2: str,
        features1: Optional[Dict[str, Any]] = None,
        features2: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate similarity between signatures and features.
        
        Args:
            sig1: First signature
            sig2: Second signature
            features1: Features of first signature
            features2: Features of second signature
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Exact match
        if sig1 == sig2:
            return 1.0
        
        # If no features provided, can't do sophisticated matching
        if not features1 or not features2:
            return 0.0
        
        # Compare feature sets
        keys1 = set(features1.keys())
        keys2 = set(features2.keys())
        
        if not keys1 or not keys2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = keys1 & keys2
        union = keys1 | keys2
        
        if not union:
            return 0.0
        
        # Calculate base similarity from key overlap
        jaccard_sim = len(intersection) / len(union)
        
        # Check value matches for intersecting keys
        value_matches = 0
        for key in intersection:
            if features1.get(key) == features2.get(key):
                value_matches += 1
        
        if intersection:
            value_sim = value_matches / len(intersection)
        else:
            value_sim = 0.0
        
        # Combine similarities
        return (jaccard_sim + value_sim) / 2.0
    
    # ========== WARNING SYSTEM ==========
    
    def add_warning_callback(self, callback: Callable[[PreventionAction], None]) -> None:
        """
        Add a callback function for prevention warnings.
        
        Args:
            callback: Function to call when prevention action occurs
        """
        self.warning_callbacks.append(callback)
    
    def trigger_prevention_action(self, action: PreventionAction) -> None:
        """
        Trigger prevention action and notify callbacks.
        
        Args:
            action: Prevention action to trigger
        """
        self.logger.warning(
            f"Prevention action triggered: {action.prevention_type.value}, "
            f"level={action.level.value}, blocked={action.blocked}"
        )
        
        # Notify all callbacks
        for callback in self.warning_callbacks:
            try:
                callback(action)
            except Exception as e:
                self.logger.error(f"Error in warning callback: {e}")
    
    # ========== UTILITY METHODS ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get prevention system statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "action_history_size": len(self.action_history),
            "decision_history_size": len(self.decision_history),
            "progress_history_size": len(self.progress_history),
            "unique_action_fingerprints": len(self.action_fingerprints),
            "rejected_options_count": len(self.rejected_options),
            "scope_expansion_count": self.scope_expansion_count,
            "trap_patterns_count": len(self.trap_patterns),
            "task_trap_stats": dict(self.task_trap_stats)
        }
    
    def reset(self) -> None:
        """Reset all prevention state."""
        self.action_history.clear()
        self.action_fingerprints.clear()
        self.decision_history.clear()
        self.decision_dependencies.clear()
        self.rejected_options.clear()
        self.progress_history.clear()
        self.last_significant_progress = None
        self.initial_scope = None
        self.current_scope = None
        self.scope_expansion_count = 0
        self.scope_changes.clear()
        
        self.logger.info("Trap prevention system reset")


def create_trap_prevention(
    max_history_size: int = 100,
    progress_minimal_threshold: float = 0.1,
    progress_expected_threshold: float = 0.3,
    max_scope_expansions: int = 3,
    learning_enabled: bool = True
) -> TrapPrevention:
    """
    Factory function to create a TrapPrevention instance.
    
    Args:
        max_history_size: Maximum number of items to keep in history
        progress_minimal_threshold: Minimal progress threshold (0.1 = 10%)
        progress_expected_threshold: Expected progress threshold (0.3 = 30%)
        max_scope_expansions: Maximum number of scope expansions allowed
        learning_enabled: Enable learning from past traps
    
    Returns:
        Configured TrapPrevention instance
    """
    return TrapPrevention(
        max_history_size=max_history_size,
        progress_minimal_threshold=progress_minimal_threshold,
        progress_expected_threshold=progress_expected_threshold,
        max_scope_expansions=max_scope_expansions,
        learning_enabled=learning_enabled
    )


# Required import for regex
import re