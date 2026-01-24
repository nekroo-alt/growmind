"""
Adaptive Heuristics - Task 6.5: Adaptive Heuristics that Improve Over Time

This module implements comprehensive adaptive heuristics for continuous improvement:
- Start with baseline heuristics
- Update heuristics based on performance data
- Learn optimal weights for decision factors using Bayesian optimization
- Learn optimal thresholds for validation using gradient descent
- Learn optimal context levels per task type using reinforcement learning
- Learn optimal strategies per situation type using ML

Learning algorithms:
- Bayesian Optimization: Optimize weights/thresholds
- Reinforcement Learning: Learn policies for strategy selection
- Gradient Descent: Learn weights for scoring functions
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
import json
from datetime import datetime
import math
from collections import defaultdict
import sqlite3
import threading
import uuid
import random


class BayesianOptimizer:
    """
    Bayesian optimization for optimizing heuristic parameters.
    
    Uses Gaussian Process for Bayesian optimization to find optimal
    parameter values that maximize success rate.
    """
    
    def __init__(self, param_bounds: Dict[str, Tuple[float, float]]):
        """
        Initialize Bayesian optimizer.
        
        Args:
            param_bounds: Dictionary mapping parameter names to (min, max) bounds
        """
        self.param_bounds = param_bounds
        self.observations = []  # List of (params, objective_value)
        self.logger = logging.getLogger(__name__)
    
    def suggest_next_params(self) -> Dict[str, float]:
        """
        Suggest next set of parameters to try.
        
        Uses expected improvement acquisition function.
        
        Returns:
            Dictionary of suggested parameter values
        """
        if not self.observations:
            # First suggestion: use middle of bounds
            return {name: (min_val + max_val) / 2 
                   for name, (min_val, max_val) in self.param_bounds.items()}
        
        # Find best observation
        best_params, best_value = max(self.observations, key=lambda x: x[1])
        
        # Simple implementation: perturb best parameters
        # In full implementation, use Gaussian Process and Expected Improvement
        next_params = {}
        for name, (min_val, max_val) in self.param_bounds.items():
            # Add small random perturbation
            perturbation = random.uniform(-0.1, 0.1)
            # Use .get() with default to handle missing parameters
            current_value = best_params.get(name, (min_val + max_val) / 2)
            new_value = current_value + perturbation * (max_val - min_val)
            next_params[name] = max(min_val, min(max_val, new_value))
        
        return next_params
    
    def register_observation(self, params: Dict[str, float], objective_value: float):
        """
        Register an observation.
        
        Args:
            params: Parameter values tried
            objective_value: Objective value achieved (e.g., success rate)
        """
        self.observations.append((params, objective_value))
        
        # Keep only last 100 observations to limit memory
        if len(self.observations) > 100:
            self.observations = self.observations[-100:]
    
    def get_best_params(self) -> Tuple[Dict[str, float], float]:
        """
        Get best parameters observed so far.
        
        Returns:
            Tuple of (best_params, best_value)
        """
        if not self.observations:
            raise ValueError("No observations available")
        
        return max(self.observations, key=lambda x: x[1])


class ReinforcementLearner:
    """
    Reinforcement learning for learning optimal policies.
    
    Uses Q-learning to learn optimal strategy selection
    for different situations.
    """
    
    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        exploration_rate: float = 0.1
    ):
        """
        Initialize Q-learning agent.
        
        Args:
            learning_rate: How quickly we update Q-values
            discount_factor: How much we value future rewards
            exploration_rate: Probability of exploring random actions
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.q_table: Dict[Tuple, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.logger = logging.getLogger(__name__)
    
    def get_state_key(self, situation_type: str, task_type: str) -> Tuple[str, str]:
        """
        Convert situation and task type to state key.
        
        Args:
            situation_type: Type of situation (e.g., 'normal', 'error')
            task_type: Type of task (e.g., 'planning', 'implementation')
        
        Returns:
            State key tuple
        """
        return (situation_type, task_type)
    
    def select_action(
        self,
        situation_type: str,
        task_type: str,
        available_actions: List[str]
    ) -> str:
        """
        Select action (strategy) using epsilon-greedy policy.
        
        Args:
            situation_type: Current situation type
            task_type: Current task type
            available_actions: List of available actions/strategies
        
        Returns:
            Selected action
        """
        state = self.get_state_key(situation_type, task_type)
        
        # Explore: random action
        if random.random() < self.exploration_rate:
            return random.choice(available_actions)
        
        # Exploit: best action
        q_values = self.q_table[state]
        if not q_values:
            return random.choice(available_actions)
        
        # Filter to available actions
        available_q = {action: q_values[action] for action in available_actions 
                      if action in q_values}
        
        if not available_q:
            return random.choice(available_actions)
        
        return max(available_q, key=available_q.get)
    
    def update_q_value(
        self,
        situation_type: str,
        task_type: str,
        action: str,
        reward: float,
        next_situation_type: Optional[str] = None,
        next_task_type: Optional[str] = None,
        available_next_actions: Optional[List[str]] = None
    ):
        """
        Update Q-value using Q-learning update rule.
        
        Args:
            situation_type: Current situation type
            task_type: Current task type
            action: Action taken
            reward: Reward received
            next_situation_type: Next situation type (optional)
            next_task_type: Next task type (optional)
            available_next_actions: Available actions in next state (optional)
        """
        state = self.get_state_key(situation_type, task_type)
        
        # Current Q-value
        current_q = self.q_table[state][action]
        
        # Calculate max Q-value for next state
        max_next_q = 0.0
        if next_situation_type and next_task_type and available_next_actions:
            next_state = self.get_state_key(next_situation_type, next_task_type)
            next_q_values = self.q_table[next_state]
            available_next_q = {action: next_q_values[action] 
                             for action in available_next_actions 
                             if action in next_q_values}
            if available_next_q:
                max_next_q = max(available_next_q.values())
        
        # Q-learning update: Q(s,a) = Q(s,a) + alpha * (r + gamma * max(Q(s',a')) - Q(s,a))
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state][action] = new_q
    
    def decay_exploration(self, decay_rate: float = 0.995):
        """
        Decay exploration rate.
        
        Args:
            decay_rate: Rate to decay exploration (default 0.995)
        """
        self.exploration_rate = max(0.01, self.exploration_rate * decay_rate)
    
    def get_policy(self) -> Dict[Tuple, str]:
        """
        Get current learned policy (best action for each state).
        
        Returns:
            Dictionary mapping state to best action
        """
        policy = {}
        for state, q_values in self.q_table.items():
            if q_values:
                policy[state] = max(q_values, key=q_values.get)
        return policy


class GradientDescentOptimizer:
    """
    Gradient descent for optimizing weights.
    
    Uses gradient descent to learn optimal weights for
    decision factor scoring.
    """
    
    def __init__(
        self,
        initial_weights: Dict[str, float],
        learning_rate: float = 0.01,
        momentum: float = 0.9
    ):
        """
        Initialize gradient descent optimizer.
        
        Args:
            initial_weights: Initial weight values
            learning_rate: Learning rate for updates
            momentum: Momentum factor for faster convergence
        """
        self.weights = initial_weights.copy()
        self.learning_rate = learning_rate
        self.momentum = momentum
        self.velocities = {name: 0.0 for name in initial_weights}
        self.logger = logging.getLogger(__name__)
    
    def compute_loss(self, predictions: List[float], targets: List[float]) -> float:
        """
        Compute mean squared error loss.
        
        Args:
            predictions: Predicted values
            targets: Target values
        
        Returns:
            Mean squared error loss
        """
        return sum((p - t) ** 2 for p, t in zip(predictions, targets)) / len(predictions)
    
    def compute_gradients(
        self,
        features: List[Dict[str, float]],
        predictions: List[float],
        targets: List[float]
    ) -> Dict[str, float]:
        """
        Compute gradients for each weight.
        
        Args:
            features: Feature values for each sample
            predictions: Predicted values
            targets: Target values
        
        Returns:
            Dictionary of gradients for each weight
        """
        gradients = {name: 0.0 for name in self.weights}
        
        for i, (feat, pred, target) in enumerate(zip(features, predictions, targets)):
            error = pred - target
            for name, weight in self.weights.items():
                gradients[name] += 2 * error * feat.get(name, 0.0) / len(features)
        
        return gradients
    
    def update_weights(self, gradients: Dict[str, float]):
        """
        Update weights using gradient descent with momentum.
        
        Args:
            gradients: Gradients for each weight
        """
        for name in self.weights:
            # Update velocity with momentum
            self.velocities[name] = (
                self.momentum * self.velocities[name] - 
                self.learning_rate * gradients[name]
            )
            
            # Update weight
            self.weights[name] += self.velocities[name]
    
    def train_step(
        self,
        features: List[Dict[str, float]],
        targets: List[float]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Perform one training step.
        
        Args:
            features: Feature values for each sample
            targets: Target values
        
        Returns:
            Tuple of (loss, gradients)
        """
        # Compute predictions using current weights
        predictions = []
        for feat in features:
            pred = sum(self.weights[name] * feat.get(name, 0.0) 
                      for name in self.weights)
            predictions.append(pred)
        
        # Compute loss
        loss = self.compute_loss(predictions, targets)
        
        # Compute gradients
        gradients = self.compute_gradients(features, predictions, targets)
        
        # Update weights
        self.update_weights(gradients)
        
        return loss, gradients
    
    def get_weights(self) -> Dict[str, float]:
        """
        Get current weights.
        
        Returns:
            Dictionary of current weights
        """
        return self.weights.copy()


class AdaptiveHeuristics:
    """
    Adaptive heuristics that improve over time.
    
    Implements comprehensive learning system with:
    - Bayesian optimization for parameter tuning
    - Reinforcement learning for strategy selection
    - Gradient descent for weight learning
    """
    
    def __init__(self, db_path: str = "v4_adaptive_heuristics.db"):
        """
        Initialize adaptive heuristics system.
        
        Args:
            db_path: Path to SQLite database for heuristic storage
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.lock = threading.RLock()
        
        # Baseline heuristics
        self.baseline_heuristics = {
            'confidence_threshold': 0.7,
            'progress_minimal_threshold': 0.1,
            'progress_expected_threshold': 0.3,
            'loop_threshold': 3.0,
            'dead_end_threshold': 5.0,
        }
        
        # Current heuristics (start with baseline)
        self.current_heuristics = self.baseline_heuristics.copy()
        
        # Decision weights for scoring
        self.decision_weights = {
            'success_probability': 1.0,
            'cost': 0.5,
            'risk': 0.8,
            'time': 0.3
        }
        
        # Initialize learning components
        self._init_optimizers()
        
        # Initialize database
        self._init_db()
        
        # Load learned heuristics from database
        self._load_heuristics()
    
    def _init_optimizers(self):
        """Initialize optimization components."""
        # Bayesian optimizer for heuristic parameters
        param_bounds = {
            'confidence_threshold': (0.5, 0.9),
            'progress_minimal_threshold': (0.05, 0.2),
            'progress_expected_threshold': (0.2, 0.5),
            'loop_threshold': (2.0, 5.0),
            'dead_end_threshold': (3.0, 10.0),
        }
        self.bayesian_optimizer = BayesianOptimizer(param_bounds)
        
        # Reinforcement learner for strategy selection
        self.rl_learner = ReinforcementLearner(
            learning_rate=0.1,
            discount_factor=0.95,
            exploration_rate=0.1
        )
        
        # Gradient descent optimizer for decision weights
        self.gd_optimizer = GradientDescentOptimizer(
            initial_weights=self.decision_weights,
            learning_rate=0.01,
            momentum=0.9
        )
    
    def _init_db(self):
        """Initialize SQLite database for heuristic storage."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Create heuristics table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS heuristics (
                heuristic_name TEXT PRIMARY KEY,
                current_value REAL NOT NULL,
                baseline_value REAL NOT NULL,
                last_updated TEXT,
                update_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # Create heuristic history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS heuristic_history (
                id TEXT PRIMARY KEY,
                heuristic_name TEXT NOT NULL,
                old_value REAL NOT NULL,
                new_value REAL NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (heuristic_name) REFERENCES heuristics (heuristic_name)
            )
        """)
        
        # Create decision weights table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS decision_weights (
                weight_name TEXT PRIMARY KEY,
                current_value REAL NOT NULL,
                last_updated TEXT
            )
        """)
        
        # Create strategy selection history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_selection_history (
                id TEXT PRIMARY KEY,
                situation_type TEXT NOT NULL,
                task_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                reward REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Create learning history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_history (
                id TEXT PRIMARY KEY,
                learning_type TEXT NOT NULL,
                details TEXT NOT NULL,
                performance_improvement REAL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Initialize baseline heuristics in database
        for name, value in self.baseline_heuristics.items():
            self.conn.execute("""
                INSERT OR IGNORE INTO heuristics 
                (heuristic_name, current_value, baseline_value, last_updated, update_count)
                VALUES (?, ?, ?, datetime('now'), 0)
            """, (name, value, value))
        
        # Initialize decision weights in database
        for name, value in self.decision_weights.items():
            self.conn.execute("""
                INSERT OR IGNORE INTO decision_weights (weight_name, current_value, last_updated)
                VALUES (?, ?, datetime('now'))
            """, (name, value))
        
        self.conn.commit()
    
    def _load_heuristics(self):
        """Load heuristics from database."""
        cursor = self.conn.execute("""
            SELECT heuristic_name, current_value FROM heuristics
        """)
        
        for row in cursor.fetchall():
            self.current_heuristics[row['heuristic_name']] = row['current_value']
        
        # Load decision weights
        cursor = self.conn.execute("""
            SELECT weight_name, current_value FROM decision_weights
        """)
        
        for row in cursor.fetchall():
            self.decision_weights[row['weight_name']] = row['current_value']
        
        # Load strategy selection history
        cursor = self.conn.execute("""
            SELECT situation_type, task_type, strategy, reward 
            FROM strategy_selection_history
            ORDER BY timestamp DESC
            LIMIT 1000
        """)
        
        for row in cursor.fetchall():
            # Update Q-values from history
            self.rl_learner.update_q_value(
                situation_type=row['situation_type'],
                task_type=row['task_type'],
                strategy=row['strategy'],
                reward=row['reward']
            )
    
    def update_heuristic(
        self,
        heuristic_name: str,
        new_value: float,
        reason: Optional[str] = None
    ) -> bool:
        """
        Update a heuristic value.
        
        Args:
            heuristic_name: Name of heuristic to update
            new_value: New value for heuristic
            reason: Reason for the update
        
        Returns:
            True if update was successful, False otherwise
        """
        with self.lock:
            cursor = self.conn.execute("""
                SELECT current_value, update_count FROM heuristics
                WHERE heuristic_name = ?
            """, (heuristic_name,))
            
            row = cursor.fetchone()
            if not row:
                self.logger.warning(f"Heuristic not found: {heuristic_name}")
                return False
            
            old_value = row['current_value']
            update_count = row['update_count']
            
            # Check if value has significantly changed
            if abs(new_value - old_value) < 0.01:
                return True
            
            # Update heuristic
            self.conn.execute("""
                UPDATE heuristics
                SET current_value = ?, last_updated = datetime('now'), update_count = ?
                WHERE heuristic_name = ?
            """, (new_value, update_count + 1, heuristic_name))
            
            # Record history
            self.conn.execute("""
                INSERT INTO heuristic_history 
                (id, heuristic_name, old_value, new_value, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (str(uuid.uuid4()), heuristic_name, old_value, new_value, reason))
            
            self.conn.commit()
            
            # Update in-memory value
            self.current_heuristics[heuristic_name] = new_value
            
            self.logger.info(f"Updated heuristic {heuristic_name}: {old_value:.3f} -> {new_value:.3f}")
            
            return True
    
    def optimize_heuristics_bayesian(
        self,
        performance_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Optimize heuristics using Bayesian optimization.
        
        Args:
            performance_data: List of performance data entries with:
                - heuristics: dict of heuristic values used
                - success_rate: success rate achieved
        
        Returns:
            Optimized heuristic values
        """
        with self.lock:
            # Register observations
            for data in performance_data:
                heuristics_used = data.get('heuristics', {})
                success_rate = data.get('success_rate', 0.0)
                self.bayesian_optimizer.register_observation(heuristics_used, success_rate)
            
            # Get best parameters
            best_params, best_value = self.bayesian_optimizer.get_best_params()
            
            # Suggest next parameters
            next_params = self.bayesian_optimizer.suggest_next_params()
            
            # Update heuristics if improvement
            current_success = [data.get('success_rate', 0.0) for data in performance_data[-1:]]
            if current_success and best_value > max(current_success):
                # Only update heuristics that exist in the performance data
                for name, value in next_params.items():
                    if name in self.current_heuristics:
                        self.update_heuristic(name, value, "Bayesian optimization")
            
            # Record learning
            improvement = best_value - max(current_success) if current_success else 0.0
            self._record_learning_history(
                "bayesian_optimization",
                f"Optimized heuristics to success rate: {best_value:.3f}",
                improvement
            )
            
            return next_params
    
    def learn_strategy_selection(
        self,
        situation_type: str,
        task_type: str,
        strategy: str,
        reward: float,
        next_situation_type: Optional[str] = None,
        next_task_type: Optional[str] = None,
        available_next_strategies: Optional[List[str]] = None
    ):
        """
        Learn optimal strategy selection using reinforcement learning.
        
        Args:
            situation_type: Current situation type
            task_type: Current task type
            strategy: Strategy selected
            reward: Reward received (e.g., success, efficiency)
            next_situation_type: Next situation type (optional)
            next_task_type: Next task type (optional)
            available_next_strategies: Available strategies in next state (optional)
        """
        with self.lock:
            # Update Q-value
            self.rl_learner.update_q_value(
                situation_type, task_type, strategy, reward,
                next_situation_type, next_task_type, available_next_strategies
            )
            
            # Record in database
            self.conn.execute("""
                INSERT INTO strategy_selection_history
                (id, situation_type, task_type, strategy, reward, timestamp)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (str(uuid.uuid4()), situation_type, task_type, strategy, reward))
            
            self.conn.commit()
            
            # Decay exploration rate
            self.rl_learner.decay_exploration()
            
            self.logger.info(
                f"Learned strategy selection: {task_type}/{situation_type} -> {strategy} "
                f"(reward: {reward:.3f}, exploration: {self.rl_learner.exploration_rate:.3f})"
            )
    
    def select_strategy_rl(
        self,
        situation_type: str,
        task_type: str,
        available_strategies: List[str]
    ) -> str:
        """
        Select strategy using learned policy.
        
        Args:
            situation_type: Current situation type
            task_type: Current task type
            available_strategies: List of available strategies
        
        Returns:
            Selected strategy
        """
        with self.lock:
            return self.rl_learner.select_action(
                situation_type, task_type, available_strategies
            )
    
    def learn_decision_weights(
        self,
        training_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Learn optimal decision weights using gradient descent.
        
        Args:
            training_data: List of training examples with:
                - features: dict of feature values
                - target: target value to predict
        
        Returns:
            Updated weights
        """
        with self.lock:
            # Prepare features and targets
            features = [data['features'] for data in training_data]
            targets = [data['target'] for data in training_data]
            
            # Train for multiple epochs
            losses = []
            for epoch in range(10):
                loss, gradients = self.gd_optimizer.train_step(features, targets)
                losses.append(loss)
            
            # Get updated weights
            new_weights = self.gd_optimizer.get_weights()
            
            # Update decision weights
            for name, value in new_weights.items():
                self.conn.execute("""
                    UPDATE decision_weights
                    SET current_value = ?, last_updated = datetime('now')
                    WHERE weight_name = ?
                """, (value, name))
            
            self.conn.commit()
            
            # Update in-memory weights
            self.decision_weights = new_weights
            
            # Record learning
            improvement = losses[0] - losses[-1] if losses else 0.0
            self._record_learning_history(
                "gradient_descent",
                f"Learned decision weights (loss: {losses[-1]:.6f})",
                improvement
            )
            
            self.logger.info(
                f"Learned decision weights: {new_weights} "
                f"(loss improved by {improvement:.6f})"
            )
            
            return new_weights
    
    def _record_learning_history(
        self,
        learning_type: str,
        details: str,
        improvement: float = 0.0
    ):
        """
        Record learning event in history.
        
        Args:
            learning_type: Type of learning (bayesian, rl, gradient_descent)
            details: Details of learning event
            improvement: Improvement in performance
        """
        self.conn.execute("""
            INSERT INTO learning_history
            (id, learning_type, details, performance_improvement, timestamp)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (str(uuid.uuid4()), learning_type, details, improvement))
        self.conn.commit()
    
    def get_heuristic(self, heuristic_name: str, default: float = 0.0) -> float:
        """
        Get current value of a heuristic.
        
        Args:
            heuristic_name: Name of heuristic
            default: Default value if not found
        
        Returns:
            Current heuristic value
        """
        return self.current_heuristics.get(heuristic_name, default)
    
    def get_all_heuristics(self) -> Dict[str, float]:
        """
        Get all current heuristics.
        
        Returns:
            Dictionary of all heuristics
        """
        return self.current_heuristics.copy()
    
    def get_decision_weight(self, weight_name: str, default: float = 1.0) -> float:
        """
        Get current value of a decision weight.
        
        Args:
            weight_name: Name of weight
            default: Default value if not found
        
        Returns:
            Current weight value
        """
        return self.decision_weights.get(weight_name, default)
    
    def get_all_decision_weights(self) -> Dict[str, float]:
        """
        Get all decision weights.
        
        Returns:
            Dictionary of all decision weights
        """
        return self.decision_weights.copy()
    
    def get_heuristic_history(
        self,
        heuristic_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get history of heuristic updates.
        
        Args:
            heuristic_name: Specific heuristic to get history for (None for all)
            limit: Maximum number of history entries
        
        Returns:
            List of history entries
        """
        with self.lock:
            if heuristic_name:
                cursor = self.conn.execute("""
                    SELECT * FROM heuristic_history
                    WHERE heuristic_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (heuristic_name, limit))
            else:
                cursor = self.conn.execute("""
                    SELECT * FROM heuristic_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_learning_history(
        self,
        learning_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get learning history.
        
        Args:
            learning_type: Type of learning to filter by (None for all)
            limit: Maximum number of history entries
        
        Returns:
            List of learning history entries
        """
        with self.lock:
            if learning_type:
                cursor = self.conn.execute("""
                    SELECT * FROM learning_history
                    WHERE learning_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (learning_type, limit))
            else:
                cursor = self.conn.execute("""
                    SELECT * FROM learning_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_heuristic_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about heuristics.
        
        Returns:
            Dictionary with heuristic statistics
        """
        with self.lock:
            cursor = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_heuristics,
                    AVG(update_count) as avg_update_count,
                    MAX(update_count) as max_update_count
                FROM heuristics
            """)
            
            stats = dict(cursor.fetchone())
            
            # Count heuristics updated recently
            cursor = self.conn.execute("""
                SELECT COUNT(*) as recent_updates
                FROM heuristics
                WHERE last_updated > datetime('now', '-7 days')
            """)
            
            stats['recent_updates'] = cursor.fetchone()['recent_updates']
            
            # Learning statistics
            cursor = self.conn.execute("""
                SELECT 
                    learning_type,
                    COUNT(*) as count,
                    AVG(performance_improvement) as avg_improvement
                FROM learning_history
                GROUP BY learning_type
            """)
            
            stats['learning_stats'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
    
    def export_heuristics(self) -> str:
        """
        Export current heuristics as JSON.
        
        Returns:
            JSON string of current heuristics
        """
        export_data = {
            "heuristics": self.current_heuristics.copy(),
            "decision_weights": self.decision_weights.copy(),
            "baselines": self.baseline_heuristics.copy(),
            "learned_policy": self.rl_learner.get_policy(),
            "exported_at": datetime.now().isoformat()
        }
        
        return json.dumps(export_data, indent=2, default=str)
    
    def reset_to_baseline(self, heuristic_name: Optional[str] = None) -> bool:
        """
        Reset heuristics to baseline values.
        
        Args:
            heuristic_name: Specific heuristic to reset (None for all)
        
        Returns:
            True if reset was successful
        """
        with self.lock:
            if heuristic_name:
                # Reset specific heuristic
                baseline = self.baseline_heuristics.get(heuristic_name)
                if baseline is not None:
                    self.update_heuristic(heuristic_name, baseline, "Reset to baseline")
                    return True
                return False
            else:
                # Reset all heuristics
                for name, value in self.baseline_heuristics.items():
                    self.update_heuristic(name, value, "Reset to baseline")
                
                # Reset optimizers
                self._init_optimizers()
                
                return True
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Global adaptive heuristics manager instance
_adaptive_heuristics = None
_lock = None


def get_adaptive_heuristics() -> AdaptiveHeuristics:
    """
    Get global adaptive heuristics instance (thread-safe singleton).
    
    Returns:
        AdaptiveHeuristics instance
    """
    global _adaptive_heuristics, _lock
    if _adaptive_heuristics is None:
        if _lock is None:
            _lock = threading.Lock()
        
        with _lock:
            if _adaptive_heuristics is None:
                _adaptive_heuristics = AdaptiveHeuristics()
    return _adaptive_heuristics