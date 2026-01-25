"""
Token Budget Manager Module (V5)

Implements adaptive token budget management for cost optimization.
Dynamically adjusts token budget based on task complexity, learns optimal budgets
from historical data, and optimizes token usage through intelligent pruning.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskComplexityLevel(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class BudgetAllocation:
    """Token budget allocation for a task."""
    
    initial_budget: int
    current_budget: int
    used_tokens: int = 0
    expansion_count: int = 0
    max_expansions: int = 3
    task_type: str = "unknown"
    complexity: TaskComplexityLevel = TaskComplexityLevel.MEDIUM
    
    @property
    def remaining_tokens(self) -> int:
        """Get remaining tokens."""
        return self.current_budget - self.used_tokens
    
    @property
    def utilization_percentage(self) -> float:
        """Get budget utilization percentage."""
        if self.current_budget == 0:
            return 100.0
        return (self.used_tokens / self.current_budget) * 100
    
    @property
    def can_expand(self) -> bool:
        """Check if budget can be expanded further."""
        return self.expansion_count < self.max_expansions
    
    def expand_budget(self, expansion_factor: float = 1.5) -> int:
        """
        Expand token budget.
        
        Args:
            expansion_factor: Multiplier for budget expansion
            
        Returns:
            New budget value
        """
        if not self.can_expand:
            return self.current_budget
        
        old_budget = self.current_budget
        self.current_budget = int(self.current_budget * expansion_factor)
        self.expansion_count += 1
        
        logger.info(
            f"Budget expanded: {old_budget} -> {self.current_budget} tokens "
            f"(expansion #{self.expansion_count})"
        )
        
        return self.current_budget
    
    def use_tokens(self, tokens: int):
        """
        Record token usage.
        
        Args:
            tokens: Number of tokens used
        """
        self.used_tokens += tokens
        logger.debug(f"Token usage: {tokens} (total: {self.used_tokens}/{self.current_budget})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'initial_budget': self.initial_budget,
            'current_budget': self.current_budget,
            'used_tokens': self.used_tokens,
            'remaining_tokens': self.remaining_tokens,
            'utilization_percentage': round(self.utilization_percentage, 2),
            'expansion_count': self.expansion_count,
            'max_expansions': self.max_expansions,
            'task_type': self.task_type,
            'complexity': self.complexity.value
        }


@dataclass
class TokenUsageStats:
    """Token usage statistics for a task type."""
    
    task_type: str
    complexity: TaskComplexityLevel
    total_tasks: int = 0
    total_tokens_used: int = 0
    total_budget_allocated: int = 0
    successful_tasks: int = 0
    avg_tokens_per_task: float = 0.0
    avg_budget_per_task: float = 0.0
    success_rate: float = 0.0
    last_updated: Optional[datetime] = None
    
    def update_stats(self, tokens_used: int, budget_allocated: int, success: bool):
        """
        Update statistics with new task data.
        
        Args:
            tokens_used: Tokens actually used
            budget_allocated: Budget allocated for task
            success: Whether task was successful
        """
        self.total_tasks += 1
        self.total_tokens_used += tokens_used
        self.total_budget_allocated += budget_allocated
        
        if success:
            self.successful_tasks += 1
        
        # Recalculate averages
        self.avg_tokens_per_task = self.total_tokens_used / self.total_tasks
        self.avg_budget_per_task = self.total_budget_allocated / self.total_tasks
        self.success_rate = (self.successful_tasks / self.total_tasks) * 100
        self.last_updated = datetime.now()
    
    def get_recommended_budget(self, complexity: TaskComplexityLevel) -> int:
        """
        Get recommended budget based on historical data.
        
        Args:
            complexity: Task complexity level
            
        Returns:
            Recommended token budget
        """
        if self.total_tasks < 3:
            # Not enough data, return default
            return TaskComplexityAnalyzer.get_default_budget(complexity)
        
        # Use average + buffer (20%)
        recommended = int(self.avg_tokens_per_task * 1.2)
        
        # Add complexity-specific adjustments
        if complexity == TaskComplexityLevel.COMPLEX:
            recommended = int(recommended * 1.5)
        elif complexity == TaskComplexityLevel.SIMPLE:
            recommended = int(recommended * 0.8)
        
        # Ensure minimum budget
        min_budget = TaskComplexityAnalyzer.get_default_budget(complexity)
        return max(recommended, min_budget)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'task_type': self.task_type,
            'complexity': self.complexity.value,
            'complexity': self.complexity.value,
            'total_tasks': self.total_tasks,
            'total_tokens_used': self.total_tokens_used,
            'total_budget_allocated': self.total_budget_allocated,
            'successful_tasks': self.successful_tasks,
            'avg_tokens_per_task': round(self.avg_tokens_per_task, 2),
            'avg_budget_per_task': round(self.avg_budget_per_task, 2),
            'success_rate': round(self.success_rate, 2),
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class TaskComplexityAnalyzer:
    """Task complexity level and defaults."""
    
    @staticmethod
    def estimate_complexity(task_description: str, task_type: str = "general") -> TaskComplexityLevel:
        """
        Estimate task complexity from description.
        
        Args:
            task_description: Description of the task
            task_type: Type of task (bug_fix, feature, refactor, etc.)
            
        Returns:
            Estimated complexity level
        """
        # Keywords that indicate complexity
        complex_keywords = [
            'architecture', 'refactor', 'redesign', 'rewrite',
            'integration', 'system', 'multiple', 'complex',
            'performance', 'optimization', 'migration', 'upgrade'
        ]
        
        simple_keywords = [
            'fix bug', 'fix typo', 'update', 'change', 'rename',
            'add simple', 'remove', 'delete', 'simple', 'minor'
        ]
        
        desc_lower = task_description.lower()
        
        # Count complexity indicators
        complex_count = sum(1 for kw in complex_keywords if kw in desc_lower)
        simple_count = sum(1 for kw in simple_keywords if kw in desc_lower)
        
        # Task type adjustments
        if task_type in ['bug_fix', 'simple_change']:
            simple_count += 1
        elif task_type in ['feature', 'refactor', 'system_upgrade']:
            complex_count += 1
        
        # Determine complexity
        if complex_count > simple_count:
            return TaskComplexityLevel.COMPLEX
        elif simple_count > complex_count:
            return TaskComplexityLevel.SIMPLE
        else:
            return TaskComplexityLevel.MEDIUM
    
    @staticmethod
    def get_default_budget(complexity: TaskComplexityLevel) -> int:
        """
        Get default token budget for complexity level.
        
        Args:
            complexity: Task complexity level
            
        Returns:
            Default token budget
        """
        defaults = {
            TaskComplexityLevel.SIMPLE: 1000,
            TaskComplexityLevel.MEDIUM: 3000,
            TaskComplexityLevel.COMPLEX: 5000
        }
        return defaults.get(complexity, 3000)
    
    @staticmethod
    def from_string(value: str) -> TaskComplexityLevel:
        """Convert string to TaskComplexityLevel enum."""
        try:
            return TaskComplexityLevel(value.lower())
        except ValueError:
            return TaskComplexityLevel.MEDIUM


class TokenBudgetManager:
    """
    Manages adaptive token budgets for LLM operations.
    
    Features:
    - Dynamic budgeting based on task complexity
    - Progressive budget expansion when needed
    - Budget learning from historical data
    - Token optimization through context pruning
    - Alerting when approaching budget limits
    """
    
    def __init__(self, 
                 db_path: str = 'telemetry.db',
                 max_total_budget: Optional[int] = None,
                 alert_threshold: float = 0.8,
                 expansion_factor: float = 1.5):
        """
        Initialize token budget manager.
        
        Args:
            db_path: Path to telemetry database for storing stats
            max_total_budget: Maximum total budget across all tasks (optional)
            alert_threshold: Percentage threshold for budget alerts (0-1)
            expansion_factor: Multiplier for budget expansion
        """
        self.db_path = db_path
        self.max_total_budget = max_total_budget
        self.alert_threshold = alert_threshold
        self.expansion_factor = expansion_factor
        
        # Current budget allocation
        self.current_allocation: Optional[BudgetAllocation] = None
        
        # Historical statistics cache
        self.stats_cache: Dict[str, TokenUsageStats] = {}
        
        # Database setup
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables for budget tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Token usage history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                task_type TEXT,
                complexity TEXT,
                initial_budget INTEGER,
                final_budget INTEGER,
                tokens_used INTEGER,
                expansion_count INTEGER,
                success INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Token budget recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_recommendations (
                task_type TEXT,
                complexity TEXT,
                recommended_budget INTEGER,
                total_tasks INTEGER,
                avg_tokens_per_task REAL,
                success_rate REAL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (task_type, complexity)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def allocate_budget(self, 
                      task_description: str,
                      task_type: str = "general",
                      custom_budget: Optional[int] = None) -> BudgetAllocation:
        """
        Allocate token budget for a new task.
        
        Args:
            task_description: Description of the task
            task_type: Type of task (bug_fix, feature, refactor, etc.)
            custom_budget: Custom budget override (optional)
            
        Returns:
            BudgetAllocation for the task
        """
        # Estimate complexity
        complexity = TaskComplexityAnalyzer.estimate_complexity(
            task_description, task_type
        )
        
        # Determine budget
        if custom_budget:
            budget = custom_budget
        else:
            # Get recommended budget from historical data
            budget = self.get_recommended_budget(task_type, complexity)
        
        # Check against max total budget
        if self.max_total_budget and budget > self.max_total_budget:
            logger.warning(
                f"Requested budget {budget} exceeds max_total_budget "
                f"{self.max_total_budget}, using max_total_budget"
            )
            budget = self.max_total_budget
        
        # Create allocation
        self.current_allocation = BudgetAllocation(
            initial_budget=budget,
            current_budget=budget,
            task_type=task_type,
            complexity=complexity
        )
        
        logger.info(
            f"Allocated budget: {budget} tokens for {task_type} task "
            f"(complexity: {complexity.value})"
        )
        
        return self.current_allocation
    
    def get_recommended_budget(self, 
                             task_type: str,
                             complexity: TaskComplexityLevel) -> int:
        """
        Get recommended budget based on historical data.
        
        Args:
            task_type: Type of task
            complexity: Task complexity level
            
        Returns:
            Recommended token budget
        """
        # Check cache first
        cache_key = f"{task_type}:{complexity.value}"
        if cache_key in self.stats_cache:
            return self.stats_cache[cache_key].get_recommended_budget(complexity)
        
        # Load from database
        stats = self._load_stats(task_type, complexity)
        self.stats_cache[cache_key] = stats
        
        return stats.get_recommended_budget(complexity)
    
    def check_budget_alert(self) -> Optional[str]:
        """
        Check if budget alert is needed.
        
        Returns:
            Alert message or None if no alert needed
        """
        if not self.current_allocation:
            return None
        
        allocation = self.current_allocation
        
        if allocation.utilization_percentage >= self.alert_threshold * 100:
            return (
                f"BUDGET ALERT: Used {allocation.utilization_percentage:.1f}% "
                f"of budget ({allocation.used_tokens}/{allocation.current_budget} tokens). "
                f"Consider expanding budget or optimizing context."
            )
        
        return None
    
    def should_expand_budget(self, 
                          task_progress: float,
                          token_usage_rate: float) -> bool:
        """
        Determine if budget should be expanded.
        
        Args:
            task_progress: Progress percentage (0-1)
            token_usage_rate: Tokens used per progress unit
            
        Returns:
            True if budget should be expanded
        """
        if not self.current_allocation:
            return False
        
        allocation = self.current_allocation
        
        # Can't expand if already at max
        if not allocation.can_expand:
            return False
        
        # Check if budget is running low but progress is slow
        tokens_needed_for_completion = (token_usage_rate * (1 - task_progress))
        remaining_tokens = allocation.remaining_tokens
        
        if tokens_needed_for_completion > remaining_tokens * 1.5:
            logger.info(
                f"Budget expansion recommended: need ~{tokens_needed_for_completion} tokens "
                f"but only {remaining_tokens} remaining"
            )
            return True
        
        return False
    
    def expand_budget(self, reason: str = "Low budget") -> int:
        """
        Expand current token budget.
        
        Args:
            reason: Reason for expansion
            
        Returns:
            New budget value
        """
        if not self.current_allocation:
            raise ValueError("No active budget allocation to expand")
        
        if not self.current_allocation.can_expand:
            raise ValueError(
                f"Cannot expand budget: already expanded "
                f"{self.current_allocation.expansion_count} times "
                f"(max: {self.current_allocation.max_expansions})"
            )
        
        old_budget = self.current_allocation.current_budget
        new_budget = self.current_allocation.expand_budget(self.expansion_factor)
        
        logger.info(f"Budget expanded: {reason}")
        
        return new_budget
    
    def record_token_usage(self, tokens: int):
        """
        Record token usage for current task.
        
        Args:
            tokens: Number of tokens used
        """
        if not self.current_allocation:
            logger.warning("No active budget allocation to record usage")
            return
        
        self.current_allocation.use_tokens(tokens)
        
        # Check for budget alert
        alert = self.check_budget_alert()
        if alert:
            logger.warning(alert)
    
    def complete_task(self, 
                   task_id: str,
                   success: bool = True,
                   notes: str = ""):
        """
        Complete current task and record statistics.
        
        Args:
            task_id: Task identifier
            success: Whether task was successful
            notes: Optional notes about task completion
        """
        if not self.current_allocation:
            raise ValueError("No active budget allocation to complete")
        
        allocation = self.current_allocation
        
        # Record in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO token_usage_history (
                task_id, task_type, complexity, initial_budget,
                final_budget, tokens_used, expansion_count, success
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            allocation.task_type,
            allocation.complexity.value,
            allocation.initial_budget,
            allocation.current_budget,
            allocation.used_tokens,
            allocation.expansion_count,
            1 if success else 0
        ))
        
        conn.commit()
        conn.close()
        
        # Update recommendations
        self._update_recommendations(allocation, success)
        
        logger.info(
            f"Task completed: {task_id} (success: {success}), "
            f"tokens: {allocation.used_tokens}/{allocation.current_budget}"
        )
        
        # Clear allocation
        self.current_allocation = None
    
    def _update_recommendations(self, allocation: BudgetAllocation, success: bool):
        """
        Update budget recommendations based on completed task.
        
        Args:
            allocation: Budget allocation that was used
            success: Whether task was successful
        """
        # Load existing stats
        cache_key = f"{allocation.task_type}:{allocation.complexity.value}"
        stats = self.stats_cache.get(cache_key) or self._load_stats(
            allocation.task_type, allocation.complexity
        )
        
        # Update with new data
        stats.update_stats(allocation.used_tokens, allocation.current_budget, success)
        
        # Update cache
        self.stats_cache[cache_key] = stats
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO budget_recommendations (
                task_type, complexity, recommended_budget, total_tasks,
                avg_tokens_per_task, success_rate, last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            stats.task_type,
            stats.complexity.value,
            stats.get_recommended_budget(stats.complexity),
            stats.total_tasks,
            stats.avg_tokens_per_task,
            stats.success_rate,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _load_stats(self, 
                   task_type: str,
                   complexity: TaskComplexityLevel) -> TokenUsageStats:
        """
        Load statistics for task type and complexity.
        
        Args:
            task_type: Type of task
            complexity: Task complexity level
            
        Returns:
            TokenUsageStats object
        """
        stats = TokenUsageStats(task_type=task_type, complexity=complexity)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT initial_budget, final_budget, tokens_used, success
            FROM token_usage_history
            WHERE task_type = ? AND complexity = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """, (task_type, complexity.value))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Update stats with historical data
        for row in rows:
            initial_budget, final_budget, tokens_used, success = row
            stats.update_stats(tokens_used, final_budget, bool(success))
        
        return stats
    
    def get_usage_report(self, 
                        task_type: Optional[str] = None,
                        complexity: Optional[TaskComplexityLevel] = None) -> Dict[str, Any]:
        """
        Generate token usage report.
        
        Args:
            task_type: Filter by task type (optional)
            complexity: Filter by complexity (optional)
            
        Returns:
            Usage report dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM token_usage_history WHERE 1=1"
        params = []
        
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)
        
        if complexity:
            query += " AND complexity = ?"
            params.append(complexity.value)
        
        cursor.execute(query + " ORDER BY timestamp DESC", params)
        rows = cursor.fetchall()
        
        # Calculate statistics
        total_tasks = len(rows)
        if total_tasks == 0:
            return {
                'total_tasks': 0,
                'total_tokens': 0,
                'avg_tokens_per_task': 0,
                'success_rate': 0
            }
        
        total_tokens = sum(row[5] for row in rows)  # tokens_used
        successful_tasks = sum(1 for row in rows if row[7] == 1)  # success
        
        conn.close()
        
        return {
            'total_tasks': total_tasks,
            'total_tokens': total_tokens,
            'avg_tokens_per_task': total_tokens / total_tasks,
            'success_rate': (successful_tasks / total_tasks) * 100,
            'history': [
                {
                    'task_id': row[1],
                    'task_type': row[2],
                    'complexity': row[3],
                    'initial_budget': row[4],
                    'final_budget': row[5],
                    'tokens_used': row[6],
                    'expansion_count': row[7],
                    'success': bool(row[8]),
                    'timestamp': row[9]
                }
                for row in rows
            ]
        }
    
    def get_recommendations_report(self) -> Dict[str, Any]:
        """
        Generate budget recommendations report.
        
        Returns:
            Recommendations report dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM budget_recommendations ORDER BY task_type, complexity")
        rows = cursor.fetchall()
        
        conn.close()
        
        recommendations = {}
        for row in rows:
            recommendations[f"{row[0]}:{row[1]}"] = {
                'task_type': row[0],
                'complexity': row[1],
                'recommended_budget': row[2],
                'total_tasks': row[3],
                'avg_tokens_per_task': row[4],
                'success_rate': row[5],
                'last_updated': row[6]
            }
        
        return recommendations
    
    def optimize_context_tokens(self, 
                             context_items: List[Dict[str, Any]],
                             max_tokens: int) -> List[Dict[str, Any]]:
        """
        Optimize context by pruning low-value items.
        
        Args:
            context_items: List of context items with 'tokens' and 'relevance' keys
            max_tokens: Maximum tokens to include
            
        Returns:
            Optimized list of context items
        """
        if not context_items:
            return context_items
        
        # Sort by relevance score (highest first)
        sorted_items = sorted(
            context_items,
            key=lambda x: x.get('relevance', 0),
            reverse=True
        )
        
        optimized = []
        total_tokens = 0
        
        for item in sorted_items:
            item_tokens = item.get('tokens', 0)
            
            # Check if adding this item exceeds budget
            if total_tokens + item_tokens > max_tokens:
                # Check if it's high-relevance (always include)
                if item.get('relevance', 0) >= 0.8:
                    optimized.append(item)
                    total_tokens += item_tokens
                continue
            
            optimized.append(item)
            total_tokens += item_tokens
        
        logger.info(
            f"Context optimization: {len(context_items)} -> {len(optimized)} items, "
            f"{sum(i.get('tokens', 0) for i in context_items)} -> "
            f"{sum(i.get('tokens', 0) for i in optimized)} tokens"
        )
        
        return optimized
    
    def get_current_allocation(self) -> Optional[BudgetAllocation]:
        """Get current budget allocation."""
        return self.current_allocation
    
    def get_remaining_tokens(self) -> int:
        """Get remaining tokens in current allocation."""
        if not self.current_allocation:
            return 0
        return self.current_allocation.remaining_tokens
    
    def get_utilization(self) -> float:
        """Get current budget utilization percentage."""
        if not self.current_allocation:
            return 0.0
        return self.current_allocation.utilization_percentage


# Global token budget manager instance
_token_budget_manager: Optional[TokenBudgetManager] = None


def get_token_budget_manager() -> TokenBudgetManager:
    """
    Get global token budget manager instance.
    
    Returns:
        TokenBudgetManager instance
    """
    global _token_budget_manager
    if _token_budget_manager is None:
        _token_budget_manager = TokenBudgetManager()
    return _token_budget_manager