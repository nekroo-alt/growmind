"""
Trap Recovery System for L4D V4

This module implements automatic recovery strategies for detected traps.
When a trap is detected, the recovery engine selects and executes the
appropriate recovery strategy with minimal disruption.

Recovery Strategies:
- Loop: Break loop, change approach, backtrack, or try different strategy
- Dead End: Backtrack to last success, break task smaller, or ask for help
- Circular Reasoning: Document decisions, introduce new context, or change reasoning
- Scope Creep: Freeze scope, break into subtasks, or defer features
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import logging
from datetime import datetime

from logic.trap_detector import (
    TrapType,
    TrapSeverity,
    TrapDetection,
    TrapDetector
)

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Enumeration of recovery strategies."""
    # Loop recovery strategies
    BREAK_LOOP_CHANGE_APPROACH = "break_loop_change_approach"
    BACKTRACK_TO_CHECKPOINT = "backtrack_to_checkpoint"
    TRY_DIFFERENT_STRATEGY = "try_different_strategy"
    
    # Dead end recovery strategies
    BACKTRACK_TO_LAST_SUCCESS = "backtrack_to_last_success"
    BREAK_TASK_SMALLER = "break_task_smaller"
    TRY_ALTERNATIVE_APPROACH = "try_alternative_approach"
    ASK_HUMAN_INTERVENTION = "ask_human_intervention"
    
    # Circular reasoning recovery strategies
    DOCUMENT_DECISIONS = "document_decisions"
    INTRODUCE_NEW_CONTEXT = "introduce_new_context"
    CHANGE_REASONING_STRATEGY = "change_reasoning_strategy"
    
    # Scope creep recovery strategies
    FREEZE_TASK_SCOPE = "freeze_task_scope"
    BREAK_INTO_SUBTASKS = "break_into_subtasks"
    DEFER_OPTIONAL_FEATURES = "defer_optional_features"


class RecoveryStatus(Enum):
    """Status of recovery execution."""
    PENDING = "pending"           # Recovery pending execution
    IN_PROGRESS = "in_progress"   # Recovery in progress
    SUCCESS = "success"           # Recovery completed successfully
    FAILED = "failed"             # Recovery failed
    SKIPPED = "skipped"           # Recovery skipped (e.g., user intervention)


@dataclass
class RecoveryAction:
    """Represents a recovery action that can be executed."""
    strategy: RecoveryStrategy
    description: str
    action_type: str  # 'checkpoint', 'state_change', 'strategy_change', 'intervention'
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_disruption: float = 0.5  # 0-1, where 1 is maximum disruption
    expected_success_rate: float = 0.8  # 0-1, based on historical data
    
    def __repr__(self) -> str:
        return f"RecoveryAction({self.strategy.value}, disruption={self.estimated_disruption:.1f})"


@dataclass
class RecoveryExecution:
    """Result of executing a recovery action."""
    strategy: RecoveryStrategy
    status: RecoveryStatus
    success: bool
    message: str
    checkpoint_before: Optional[str] = None
    checkpoint_after: Optional[str] = None
    time_elapsed: float = 0.0
    resources_used: Dict[str, Any] = field(default_factory=dict)
    recovery_actions: List[Dict[str, Any]] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"RecoveryExecution({self.strategy.value}, {self.status.value}, success={self.success})"


class TrapRecoveryEngine:
    """
    Main trap recovery engine that selects and executes recovery strategies.
    
    This component is part of V4 adaptive reasoning system and provides
    automatic recovery from detected traps with minimal disruption.
    """
    
    def __init__(
        self,
        checkpoint_manager: Optional[Any] = None,
        telemetry_manager: Optional[Any] = None
    ):
        """
        Initialize trap recovery engine.
        
        Args:
            checkpoint_manager: Optional checkpoint manager for creating/restoring checkpoints
            telemetry_manager: Optional telemetry manager for logging recovery operations
        """
        self.trap_detector = TrapDetector()
        self.checkpoint_manager = checkpoint_manager
        self.telemetry_manager = telemetry_manager
        self.logger = logger
        
        # Track recovery success rates for learning
        self.recovery_history: Dict[RecoveryStrategy, List[bool]] = {}
        
        # Initialize recovery strategy mappings
        self._initialize_recovery_strategies()
    
    def _initialize_recovery_strategies(self):
        """Initialize recovery strategy mappings for each trap type."""
        self.recovery_strategies = {
            TrapType.INFINITE_LOOP: [
                RecoveryAction(
                    strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
                    description="Break the loop by trying a different approach",
                    action_type="strategy_change",
                    parameters={"preserve_context": True},
                    estimated_disruption=0.3,
                    expected_success_rate=0.7
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.BACKTRACK_TO_CHECKPOINT,
                    description="Backtrack to the last checkpoint before the loop",
                    action_type="checkpoint",
                    parameters={"force": False},
                    estimated_disruption=0.5,
                    expected_success_rate=0.85
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.TRY_DIFFERENT_STRATEGY,
                    description="Switch to a different reasoning strategy (e.g., conservative -> aggressive)",
                    action_type="strategy_change",
                    parameters={"change_strategy": True},
                    estimated_disruption=0.4,
                    expected_success_rate=0.75
                )
            ],
            
            TrapType.DEAD_END: [
                RecoveryAction(
                    strategy=RecoveryStrategy.BACKTRACK_TO_LAST_SUCCESS,
                    description="Backtrack to the last successful state",
                    action_type="checkpoint",
                    parameters={"last_success": True},
                    estimated_disruption=0.6,
                    expected_success_rate=0.9
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.BREAK_TASK_SMALLER,
                    description="Break the current task into smaller, manageable subtasks",
                    action_type="state_change",
                    parameters={"task_breakdown": True},
                    estimated_disruption=0.4,
                    expected_success_rate=0.8
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.TRY_ALTERNATIVE_APPROACH,
                    description="Try an alternative approach or implementation strategy",
                    action_type="strategy_change",
                    parameters={"alternative_approach": True},
                    estimated_disruption=0.5,
                    expected_success_rate=0.7
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.ASK_HUMAN_INTERVENTION,
                    description="Request human intervention and guidance",
                    action_type="intervention",
                    parameters={"human_help": True},
                    estimated_disruption=0.9,
                    expected_success_rate=0.95
                )
            ],
            
            TrapType.CIRCULAR_REASONING: [
                RecoveryAction(
                    strategy=RecoveryStrategy.DOCUMENT_DECISIONS,
                    description="Document all decisions permanently to prevent revisiting",
                    action_type="state_change",
                    parameters={"document_decisions": True},
                    estimated_disruption=0.2,
                    expected_success_rate=0.85
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.INTRODUCE_NEW_CONTEXT,
                    description="Introduce new context or information to break the cycle",
                    action_type="strategy_change",
                    parameters={"new_context": True},
                    estimated_disruption=0.4,
                    expected_success_rate=0.7
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.CHANGE_REASONING_STRATEGY,
                    description="Change the reasoning strategy (e.g., from analytical to heuristic)",
                    action_type="strategy_change",
                    parameters={"change_reasoning": True},
                    estimated_disruption=0.5,
                    expected_success_rate=0.75
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.ASK_HUMAN_INTERVENTION,
                    description="Request human intervention to resolve circular reasoning",
                    action_type="intervention",
                    parameters={"human_help": True},
                    estimated_disruption=0.9,
                    expected_success_rate=0.95
                )
            ],
            
            TrapType.SCOPE_CREEP: [
                RecoveryAction(
                    strategy=RecoveryStrategy.FREEZE_TASK_SCOPE,
                    description="Freeze the task scope and prevent further expansion",
                    action_type="state_change",
                    parameters={"freeze_scope": True},
                    estimated_disruption=0.3,
                    expected_success_rate=0.85
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.BREAK_INTO_SUBTASKS,
                    description="Break the expanded task into smaller subtasks",
                    action_type="state_change",
                    parameters={"task_breakdown": True},
                    estimated_disruption=0.4,
                    expected_success_rate=0.8
                ),
                RecoveryAction(
                    strategy=RecoveryStrategy.DEFER_OPTIONAL_FEATURES,
                    description="Defer optional features to a future task",
                    action_type="state_change",
                    parameters={"defer_features": True},
                    estimated_disruption=0.3,
                    expected_success_rate=0.9
                )
            ]
        }
    
    def select_recovery_strategy(
        self,
        trap_detection: TrapDetection,
        prefer_low_disruption: bool = True,
        prefer_high_success: bool = True
    ) -> Optional[RecoveryAction]:
        """
        Select the best recovery strategy for a detected trap.
        
        Selection algorithm:
        1. Get all available strategies for trap type
        2. Score each strategy based on:
           - Historical success rate (if available)
           - Expected success rate (default)
           - Disruption level (lower is better if prefer_low_disruption)
        3. Return highest-scoring strategy
        
        Args:
            trap_detection: Detected trap with type and severity
            prefer_low_disruption: Prefer strategies with low disruption
            prefer_high_success: Prefer strategies with high success rate
        
        Returns:
            Selected RecoveryAction, or None if no strategy available
        """
        trap_type = trap_detection.trap_type
        severity = trap_detection.severity
        
        # Get available strategies for this trap type
        available_strategies = self.recovery_strategies.get(trap_type, [])
        
        if not available_strategies:
            self.logger.warning(f"No recovery strategies available for trap type: {trap_type}")
            return None
        
        # Score each strategy
        scored_strategies = []
        for strategy in available_strategies:
            score = self._score_recovery_strategy(
                strategy,
                severity,
                prefer_low_disruption,
                prefer_high_success
            )
            scored_strategies.append((score, strategy))
        
        # Sort by score (descending)
        scored_strategies.sort(key=lambda x: x[0], reverse=True)
        
        # Return highest-scoring strategy
        selected_score, selected_strategy = scored_strategies[0]
        
        self.logger.info(
            f"Selected recovery strategy: {selected_strategy.strategy.value} "
            f"(score: {selected_score:.2f}, disruption: {selected_strategy.estimated_disruption:.1f})"
        )
        
        return selected_strategy
    
    def _score_recovery_strategy(
        self,
        recovery_action: RecoveryAction,
        severity: TrapSeverity,
        prefer_low_disruption: bool,
        prefer_high_success: bool
    ) -> float:
        """
        Score a recovery strategy based on multiple factors.
        
        Scoring formula:
        score = w1 * success_rate + w2 * (1 - disruption) + w3 * severity_adjustment
        
        Where:
        - success_rate: Historical or expected success rate (0-1)
        - disruption: Disruption level (0-1), so (1 - disruption) is benefit
        - severity_adjustment: Bonus/penalty based on severity
        
        Args:
            recovery_action: Recovery action to score
            severity: Trap severity
            prefer_low_disruption: Whether to prefer low-disruption strategies
            prefer_high_success: Whether to prefer high-success strategies
        
        Returns:
            Strategy score (higher is better)
        """
        # Get historical success rate if available
        strategy = recovery_action.strategy
        if strategy in self.recovery_history and self.recovery_history[strategy]:
            historical_success = sum(self.recovery_history[strategy]) / len(self.recovery_history[strategy])
            success_rate = 0.7 * historical_success + 0.3 * recovery_action.expected_success_rate
        else:
            success_rate = recovery_action.expected_success_rate
        
        # Calculate base score
        weights = {"success": 0.6, "disruption": 0.4}
        
        if prefer_high_success:
            weights["success"] = 0.7
            weights["disruption"] = 0.3
        
        if prefer_low_disruption:
            weights["disruption"] = 0.5
            weights["success"] = 0.5
        
        success_score = success_rate * weights["success"]
        disruption_score = (1 - recovery_action.estimated_disruption) * weights["disruption"]
        
        # Severity adjustment
        severity_multiplier = {
            TrapSeverity.WARNING: 1.0,
            TrapSeverity.CRITICAL: 1.1,  # Slight preference for more aggressive strategies
            TrapSeverity.BLOCKING: 1.2   # Strong preference for more aggressive strategies
        }.get(severity, 1.0)
        
        # Higher disruption strategies get slight boost for critical/blocking traps
        if severity in [TrapSeverity.CRITICAL, TrapSeverity.BLOCKING]:
            disruption_boost = recovery_action.estimated_disruption * 0.1 * severity_multiplier
        else:
            disruption_boost = 0
        
        total_score = (success_score + disruption_score + disruption_boost) * severity_multiplier
        
        return total_score
    
    def execute_recovery(
        self,
        recovery_action: RecoveryAction,
        trap_detection: TrapDetection,
        context: Optional[Dict[str, Any]] = None
    ) -> RecoveryExecution:
        """
        Execute a recovery action to resolve a detected trap.
        
        Recovery execution process:
        1. Create checkpoint before recovery
        2. Execute recovery action based on type
        3. Validate recovery success
        4. Create checkpoint after recovery (if successful)
        5. Update recovery history for learning
        6. Log recovery in telemetry
        
        Args:
            recovery_action: Recovery action to execute
            trap_detection: Detected trap that triggered recovery
            context: Optional context for recovery execution
        
        Returns:
            RecoveryExecution with status and results
        """
        self.logger.info(f"Executing recovery: {recovery_action.strategy.value}")
        
        # Initialize execution result
        execution = RecoveryExecution(
            strategy=recovery_action.strategy,
            status=RecoveryStatus.IN_PROGRESS,
            success=False,
            message=""
        )
        
        try:
            # Step 1: Create checkpoint before recovery
            checkpoint_before = self._create_checkpoint("before_recovery")
            execution.checkpoint_before = checkpoint_before
            
            # If checkpoint creation failed and this is a critical operation, mark as failed
            if checkpoint_before is None and recovery_action.action_type == "checkpoint":
                execution.status = RecoveryStatus.FAILED
                execution.success = False
                execution.message = "Failed to create required checkpoint for recovery"
                self.logger.warning(f"Recovery failed: Could not create checkpoint for {recovery_action.strategy.value}")
                self._update_recovery_history(recovery_action.strategy, execution.success)
                self._log_recovery_to_telemetry(execution, trap_detection, context)
                return execution
            
            # Step 2: Execute recovery based on action type
            recovery_result = self._execute_recovery_action(
                recovery_action,
                trap_detection,
                context or {}
            )
            
            execution.recovery_actions = recovery_result.get("actions", [])
            
            # Step 3: Validate recovery success
            recovery_successful = recovery_result.get("success", False)
            execution.message = recovery_result.get("message", "")
            
            if recovery_successful:
                execution.status = RecoveryStatus.SUCCESS
                execution.success = True
                
                # Step 4: Create checkpoint after successful recovery
                checkpoint_after = self._create_checkpoint("after_recovery")
                execution.checkpoint_after = checkpoint_after
                
                self.logger.info(f"Recovery successful: {recovery_action.strategy.value}")
            else:
                execution.status = RecoveryStatus.FAILED
                execution.success = False
                
                # Rollback to checkpoint before recovery
                if checkpoint_before and self.checkpoint_manager:
                    self._restore_checkpoint(checkpoint_before)
                    execution.message += " Rolled back to pre-recovery state."
                
                self.logger.warning(f"Recovery failed: {recovery_action.strategy.value}")
            
            # Step 5: Update recovery history for learning
            self._update_recovery_history(recovery_action.strategy, execution.success)
            
            # Step 6: Log recovery in telemetry
            self._log_recovery_to_telemetry(execution, trap_detection, context)
            
        except Exception as e:
            execution.status = RecoveryStatus.FAILED
            execution.success = False
            execution.message = f"Recovery execution failed: {str(e)}"
            
            # Rollback on error
            if execution.checkpoint_before and self.checkpoint_manager:
                self._restore_checkpoint(execution.checkpoint_before)
            
            self.logger.error(f"Recovery execution error: {e}", exc_info=True)
        
        return execution
    
    def _execute_recovery_action(
        self,
        recovery_action: RecoveryAction,
        trap_detection: TrapDetection,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute specific recovery action based on type.
        
        Args:
            recovery_action: Recovery action to execute
            trap_detection: Detected trap
            context: Execution context
        
        Returns:
            Result dictionary with success, message, and actions taken
        """
        actions_taken = []
        
        if recovery_action.action_type == "checkpoint":
            # Checkpoint-based recovery (backtrack)
            result = self._execute_checkpoint_recovery(recovery_action, trap_detection, context)
            actions_taken.append({"type": "checkpoint", "details": result.get("details", "")})
        
        elif recovery_action.action_type == "state_change":
            # State-based recovery (change approach, break task, etc.)
            result = self._execute_state_change_recovery(recovery_action, trap_detection, context)
            actions_taken.append({"type": "state_change", "details": result.get("details", "")})
        
        elif recovery_action.action_type == "strategy_change":
            # Strategy-based recovery (change reasoning strategy)
            result = self._execute_strategy_change_recovery(recovery_action, trap_detection, context)
            actions_taken.append({"type": "strategy_change", "details": result.get("details", "")})
        
        elif recovery_action.action_type == "intervention":
            # Human intervention recovery
            result = self._execute_intervention_recovery(recovery_action, trap_detection, context)
            actions_taken.append({"type": "intervention", "details": result.get("details", "")})
        
        else:
            result = {
                "success": False,
                "message": f"Unknown recovery action type: {recovery_action.action_type}",
                "details": f"Cannot execute recovery action with type: {recovery_action.action_type}"
            }
        
        result["actions"] = actions_taken
        return result
    
    def _execute_checkpoint_recovery(
        self,
        recovery_action: RecoveryAction,
        trap_detection: TrapDetection,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute checkpoint-based recovery (backtrack)."""
        strategy = recovery_action.strategy
        
        if strategy == RecoveryStrategy.BACKTRACK_TO_CHECKPOINT:
            # Backtrack to last checkpoint
            if self.checkpoint_manager:
                latest_checkpoint = self._get_latest_checkpoint()
                if latest_checkpoint:
                    success = self._restore_checkpoint(latest_checkpoint)
                    if success:
                        return {
                            "success": True,
                            "message": "Successfully backtracked to last checkpoint",
                            "details": f"Restored checkpoint: {latest_checkpoint}"
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Failed to restore checkpoint",
                            "details": f"Checkpoint restore failed for: {latest_checkpoint}"
                        }
                else:
                    return {
                        "success": False,
                        "message": "No checkpoint available for restoration",
                        "details": "No checkpoints found in system"
                    }
            else:
                return {
                    "success": False,
                    "message": "Checkpoint manager not available",
                    "details": "Cannot execute checkpoint recovery without checkpoint manager"
                }
        
        elif strategy == RecoveryStrategy.BACKTRACK_TO_LAST_SUCCESS:
            # Backtrack to last successful state
            if self.checkpoint_manager:
                success_checkpoint = self._find_last_success_checkpoint(trap_detection)
                if success_checkpoint:
                    success = self._restore_checkpoint(success_checkpoint)
                    if success:
                        return {
                            "success": True,
                            "message": "Successfully backtracked to last successful state",
                            "details": f"Restored success checkpoint: {success_checkpoint}"
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Failed to restore success checkpoint",
                            "details": f"Checkpoint restore failed for: {success_checkpoint}"
                        }
                else:
                    return {
                        "success": False,
                        "message": "No successful checkpoint found",
                        "details": "Could not find checkpoint from successful state"
                    }
            else:
                return {
                    "success": False,
                    "message": "Checkpoint manager not available",
                    "details": "Cannot execute checkpoint recovery without checkpoint manager"
                }
        
        else:
            return {
                "success": False,
                "message": f"Unknown checkpoint recovery strategy: {strategy}",
                "details": f"Strategy {strategy} is not a checkpoint-based strategy"
            }
    
    def _execute_state_change_recovery(
        self,
        recovery_action: RecoveryAction,
        trap_detection: TrapDetection,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute state-based recovery (change approach, break task, etc.)."""
        strategy = recovery_action.strategy
        
        if strategy == RecoveryStrategy.BREAK_TASK_SMALLER:
            # Break task into smaller subtasks
            current_task = context.get("current_task", {})
            task_breakdown = self._generate_task_breakdown(current_task)
            
            return {
                "success": True,
                "message": "Task broken into smaller subtasks",
                "details": f"Generated {len(task_breakdown)} subtasks from current task",
                "subtasks": task_breakdown
            }
        
        elif strategy == RecoveryStrategy.DOCUMENT_DECISIONS:
            # Document decisions permanently
            decisions = context.get("decision_history", [])
            documentation = self._document_decisions(decisions)
            
            return {
                "success": True,
                "message": "Decisions documented permanently",
                "details": f"Documented {len(decisions)} decisions",
                "documentation": documentation
            }
        
        elif strategy == RecoveryStrategy.FREEZE_TASK_SCOPE:
            # Freeze task scope
            current_scope = context.get("task_scope", {})
            frozen_scope = self._freeze_task_scope(current_scope)
            
            return {
                "success": True,
                "message": "Task scope frozen",
                "details": f"Frozen scope with {len(frozen_scope.get('requirements', []))} requirements",
                "frozen_scope": frozen_scope
            }
        
        elif strategy == RecoveryStrategy.DEFER_OPTIONAL_FEATURES:
            # Defer optional features
            optional_features = context.get("optional_features", [])
            deferred_features = self._defer_optional_features(optional_features)
            
            return {
                "success": True,
                "message": "Optional features deferred",
                "details": f"Deferred {len(deferred_features)} optional features",
                "deferred_features": deferred_features
            }
        
        else:
            return {
                "success": False,
                "message": f"Unknown state change recovery strategy: {strategy}",
                "details": f"Strategy {strategy} is not a state change strategy"
            }
    
    def _execute_strategy_change_recovery(
        self,
        recovery_action: RecoveryAction,
        trap_detection: TrapDetection,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute strategy-based recovery (change reasoning strategy)."""
        strategy = recovery_action.strategy
        
        if strategy == RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH:
            # Change approach to break loop
            current_approach = context.get("current_approach", {})
            new_approach = self._generate_alternative_approach(current_approach, trap_detection)
            
            return {
                "success": True,
                "message": "Changed approach to break loop",
                "details": f"Switched from {current_approach.get('type', 'unknown')} to {new_approach.get('type', 'unknown')}",
                "new_approach": new_approach
            }
        
        elif strategy == RecoveryStrategy.TRY_DIFFERENT_STRATEGY:
            # Switch to different reasoning strategy
            current_strategy = context.get("reasoning_strategy", "balanced")
            new_strategy = self._switch_reasoning_strategy(current_strategy)
            
            return {
                "success": True,
                "message": f"Switched reasoning strategy from {current_strategy} to {new_strategy}",
                "details": f"Changed reasoning strategy to: {new_strategy}",
                "new_strategy": new_strategy
            }
        
        elif strategy == RecoveryStrategy.INTRODUCE_NEW_CONTEXT:
            # Introduce new context to break circular reasoning
            existing_context = context.get("context", {})
            new_context = self._generate_new_context(existing_context, trap_detection)
            
            return {
                "success": True,
                "message": "Introduced new context to break circular reasoning",
                "details": f"Added {len(new_context)} new context items",
                "new_context": new_context
            }
        
        elif strategy == RecoveryStrategy.CHANGE_REASONING_STRATEGY:
            # Change reasoning strategy
            current_reasoning = context.get("reasoning_strategy", "balanced")
            new_reasoning = self._change_reasoning_strategy(current_reasoning, trap_detection)
            
            return {
                "success": True,
                "message": f"Changed reasoning strategy from {current_reasoning} to {new_reasoning}",
                "details": f"Reasoning strategy changed to: {new_reasoning}",
                "new_reasoning": new_reasoning
            }
        
        elif strategy == RecoveryStrategy.TRY_ALTERNATIVE_APPROACH:
            # Try alternative approach
            current_approach = context.get("current_approach", {})
            alternative_approach = self._generate_alternative_approach(current_approach, trap_detection)
            
            return {
                "success": True,
                "message": "Trying alternative approach",
                "details": f"Alternative approach: {alternative_approach.get('type', 'unknown')}",
                "alternative_approach": alternative_approach
            }
        
        else:
            return {
                "success": False,
                "message": f"Unknown strategy change recovery: {strategy}",
                "details": f"Strategy {strategy} is not a strategy change recovery"
            }
    
    def _execute_intervention_recovery(
        self,
        recovery_action: RecoveryAction,
        trap_detection: TrapDetection,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute human intervention recovery."""
        strategy = recovery_action.strategy
        
        if strategy == RecoveryStrategy.ASK_HUMAN_INTERVENTION:
            # Request human intervention
            intervention_request = self._generate_intervention_request(trap_detection, context)
            
            return {
                "success": True,
                "message": "Human intervention requested",
                "details": "Awaiting human guidance to resolve trap",
                "intervention_request": intervention_request
            }
        
        else:
            return {
                "success": False,
                "message": f"Unknown intervention recovery: {strategy}",
                "details": f"Strategy {strategy} is not an intervention recovery"
            }
    
    # ========== HELPER METHODS ==========
    
    def _create_checkpoint(self, name: str) -> Optional[str]:
        """Create a checkpoint with the given name."""
        if not self.checkpoint_manager:
            return None
        
        try:
            checkpoint_id = self.checkpoint_manager.create(name=name)
            self.logger.info(f"Created checkpoint: {checkpoint_id}")
            return checkpoint_id
        except Exception as e:
            self.logger.error(f"Failed to create checkpoint: {e}")
            return None
    
    def _restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore from a checkpoint."""
        if not self.checkpoint_manager:
            return False
        
        try:
            self.checkpoint_manager.restore(checkpoint_id=checkpoint_id)
            self.logger.info(f"Restored checkpoint: {checkpoint_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to restore checkpoint {checkpoint_id}: {e}")
            return False
    
    def _get_latest_checkpoint(self) -> Optional[str]:
        """Get the latest checkpoint ID."""
        if not self.checkpoint_manager:
            return None
        
        try:
            checkpoints = self.checkpoint_manager.list_checkpoints()
            if checkpoints:
                return checkpoints[0]["checkpoint_id"]  # Most recent first
        except Exception as e:
            self.logger.error(f"Failed to get latest checkpoint: {e}")
        
        return None
    
    def _find_last_success_checkpoint(self, trap_detection: TrapDetection) -> Optional[str]:
        """Find the last checkpoint before the trap was detected."""
        # This is a simplified implementation
        # In a real system, we would search through checkpoints for the last successful state
        return self._get_latest_checkpoint()
    
    def _generate_task_breakdown(self, current_task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a breakdown of the current task into smaller subtasks."""
        # This is a placeholder implementation
        # In a real system, we would use the planner to generate subtasks
        return [
            {"id": "subtask_1", "description": "Analyze current task structure"},
            {"id": "subtask_2", "description": "Identify logical subcomponents"},
            {"id": "subtask_3", "description": "Create independent subtasks"}
        ]
    
    def _document_decisions(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Document decisions permanently."""
        # This is a placeholder implementation
        # In a real system, we would write decisions to a persistent store
        return {
            "documented": len(decisions),
            "timestamp": datetime.now().isoformat(),
            "decisions": decisions
        }
    
    def _freeze_task_scope(self, current_scope: Dict[str, Any]) -> Dict[str, Any]:
        """Freeze the task scope."""
        # This is a placeholder implementation
        # In a real system, we would save the current scope and prevent modifications
        return {
            "frozen": True,
            "timestamp": datetime.now().isoformat(),
            "requirements": current_scope.get("requirements", [])
        }
    
    def _defer_optional_features(self, optional_features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Defer optional features."""
        # This is a placeholder implementation
        # In a real system, we would move optional features to a future task
        return optional_features
    
    def _generate_alternative_approach(
        self,
        current_approach: Dict[str, Any],
        trap_detection: TrapDetection
    ) -> Dict[str, Any]:
        """Generate an alternative approach to the current one."""
        # This is a placeholder implementation
        # In a real system, we would use the LLM to generate alternatives
        approach_types = ["analytical", "heuristic", "incremental", "holistic"]
        current_type = current_approach.get("type", "unknown")
        
        # Pick a different approach type
        alternative_types = [t for t in approach_types if t != current_type]
        alternative_type = alternative_types[0] if alternative_types else "analytical"
        
        return {
            "type": alternative_type,
            "reasoning": "Alternative approach to break loop",
            "trap_detection": trap_detection.trap_type.value
        }
    
    def _switch_reasoning_strategy(self, current_strategy: str) -> str:
        """Switch to a different reasoning strategy."""
        strategies = ["conservative", "balanced", "aggressive"]
        
        # Rotate through strategies
        if current_strategy in strategies:
            current_index = strategies.index(current_strategy)
            new_index = (current_index + 1) % len(strategies)
            return strategies[new_index]
        
        return "balanced"
    
    def _generate_new_context(
        self,
        existing_context: Dict[str, Any],
        trap_detection: TrapDetection
    ) -> Dict[str, Any]:
        """Generate new context to break circular reasoning."""
        # This is a placeholder implementation
        # In a real system, we would query higher context levels or use the LLM
        return {
            "trap_type": trap_detection.trap_type.value,
            "suggestion": "Introduce new perspective or information",
            "timestamp": datetime.now().isoformat()
        }
    
    def _change_reasoning_strategy(
        self,
        current_reasoning: str,
        trap_detection: TrapDetection
    ) -> str:
        """Change the reasoning strategy."""
        strategies = ["conservative", "balanced", "aggressive"]
        
        # Rotate through strategies
        if current_reasoning in strategies:
            current_index = strategies.index(current_reasoning)
            new_index = (current_index + 1) % len(strategies)
            return strategies[new_index]
        
        return "balanced"
    
    def _generate_intervention_request(
        self,
        trap_detection: TrapDetection,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a human intervention request."""
        return {
            "trap_type": trap_detection.trap_type.value,
            "severity": trap_detection.severity.value,
            "confidence": trap_detection.confidence,
            "evidence": trap_detection.evidence,
            "suggestion": trap_detection.suggestion,
            "context": {
                "current_task": context.get("current_task"),
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _update_recovery_history(self, strategy: RecoveryStrategy, success: bool):
        """Update recovery history for learning."""
        if strategy not in self.recovery_history:
            self.recovery_history[strategy] = []
        
        self.recovery_history[strategy].append(success)
        
        # Keep only last 100 recovery attempts for each strategy
        if len(self.recovery_history[strategy]) > 100:
            self.recovery_history[strategy] = self.recovery_history[strategy][-100:]
        
        # Calculate and log success rate
        if self.recovery_history[strategy]:
            success_rate = sum(self.recovery_history[strategy]) / len(self.recovery_history[strategy])
            self.logger.debug(
                f"Recovery history updated: {strategy.value} "
                f"(success_rate: {success_rate:.1%}, attempts: {len(self.recovery_history[strategy])})"
            )
    
    def _log_recovery_to_telemetry(
        self,
        execution: RecoveryExecution,
        trap_detection: TrapDetection,
        context: Optional[Dict[str, Any]]
    ):
        """Log recovery execution to telemetry."""
        if not self.telemetry_manager:
            return
        
        try:
            # Log recovery operation
            self.telemetry_manager.start_operation(
                operation_type="trap_recovery",
                operation_id=f"recovery_{execution.strategy.value}_{datetime.now().timestamp()}",
                parent_id=None,
                metadata={
                    "strategy": execution.strategy.value,
                    "trap_type": trap_detection.trap_type.value,
                    "trap_severity": trap_detection.severity.value,
                    "trap_confidence": trap_detection.confidence,
                    "success": execution.success,
                    "status": execution.status.value,
                    "message": execution.message,
                    "checkpoint_before": execution.checkpoint_before,
                    "checkpoint_after": execution.checkpoint_after,
                    "time_elapsed": execution.time_elapsed
                }
            )
            
            # Record metrics
            self.telemetry_manager.record_metric(
                name="trap_recovery_success",
                value=1 if execution.success else 0,
                operation_type="trap_recovery",
                labels={
                    "strategy": execution.strategy.value,
                    "trap_type": trap_detection.trap_type.value
                }
            )
            
            self.telemetry_manager.record_metric(
                name="trap_recovery_time",
                value=execution.time_elapsed,
                operation_type="trap_recovery",
                labels={
                    "strategy": execution.strategy.value,
                    "trap_type": trap_detection.trap_type.value
                }
            )
            
            # End operation
            self.telemetry_manager.end_operation(
                operation_id=f"recovery_{execution.strategy.value}_{datetime.now().timestamp()}",
                status="success" if execution.success else "failure"
            )
            
            self.logger.info(f"Recovery logged to telemetry: {execution.strategy.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to log recovery to telemetry: {e}")
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recovery performance.
        
        Returns:
            Dictionary with recovery statistics
        """
        stats = {
            "total_recovery_attempts": 0,
            "overall_success_rate": 0.0,
            "strategy_statistics": {}
        }
        
        total_attempts = 0
        total_successes = 0
        
        for strategy, outcomes in self.recovery_history.items():
            attempts = len(outcomes)
            successes = sum(outcomes)
            success_rate = successes / attempts if attempts > 0 else 0
            
            stats["strategy_statistics"][strategy.value] = {
                "attempts": attempts,
                "successes": successes,
                "success_rate": success_rate
            }
            
            total_attempts += attempts
            total_successes += successes
        
        stats["total_recovery_attempts"] = total_attempts
        stats["overall_success_rate"] = total_successes / total_attempts if total_attempts > 0 else 0
        
        return stats
    
    def reset_recovery_history(self):
        """Reset recovery history (for testing purposes)."""
        self.recovery_history = {}
        self.logger.info("Recovery history reset")


def get_trap_recovery(
    checkpoint_manager: Optional[Any] = None,
    telemetry_manager: Optional[Any] = None
) -> TrapRecoveryEngine:
    """
    Get singleton TrapRecoveryEngine instance
    
    Args:
        checkpoint_manager: Optional checkpoint manager
        telemetry_manager: Optional telemetry manager
        
    Returns:
        TrapRecoveryEngine instance
    """
    if not hasattr(get_trap_recovery, '_instance'):
        get_trap_recovery._instance = TrapRecoveryEngine(
            checkpoint_manager=checkpoint_manager,
            telemetry_manager=telemetry_manager
        )
        logger.info("Created singleton TrapRecoveryEngine instance")
    
    return get_trap_recovery._instance


def reset_trap_recovery():
    """
    Reset singleton TrapRecoveryEngine instance
    Useful for testing or reinitialization
    """
    if hasattr(get_trap_recovery, '_instance'):
        del get_trap_recovery._instance
        logger.info("Reset singleton TrapRecoveryEngine instance")


def create_trap_recovery_engine(
    checkpoint_manager: Optional[Any] = None,
    telemetry_manager: Optional[Any] = None
) -> TrapRecoveryEngine:
    """
    Factory function to create a TrapRecoveryEngine instance.
    
    Args:
        checkpoint_manager: Optional checkpoint manager
        telemetry_manager: Optional telemetry manager
    
    Returns:
        Configured TrapRecoveryEngine instance
    """
    return TrapRecoveryEngine(
        checkpoint_manager=checkpoint_manager,
        telemetry_manager=telemetry_manager
    )
