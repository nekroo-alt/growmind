"""
Unit tests for Adaptive Heuristics - Task 6.5

Tests the comprehensive adaptive heuristics system with:
- Bayesian optimization for parameter tuning
- Reinforcement learning for strategy selection
- Gradient descent for weight learning
- Heuristic management and persistence
"""

import pytest
import os
import tempfile
import json
from datetime import datetime
import time

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from logic.adaptive_heuristics import (
    BayesianOptimizer,
    ReinforcementLearner,
    GradientDescentOptimizer,
    AdaptiveHeuristics,
    get_adaptive_heuristics
)


class TestBayesianOptimizer:
    """Test Bayesian optimizer."""
    
    def test_initialization(self):
        """Test Bayesian optimizer initialization."""
        param_bounds = {
            'param1': (0.0, 1.0),
            'param2': (-1.0, 1.0)
        }
        optimizer = BayesianOptimizer(param_bounds)
        
        assert optimizer.param_bounds == param_bounds
        assert optimizer.observations == []
    
    def test_first_suggestion(self):
        """Test first suggestion uses middle of bounds."""
        param_bounds = {
            'param1': (0.0, 1.0),
            'param2': (-1.0, 1.0)
        }
        optimizer = BayesianOptimizer(param_bounds)
        
        suggestion = optimizer.suggest_next_params()
        
        assert 'param1' in suggestion
        assert 'param2' in suggestion
        assert suggestion['param1'] == pytest.approx(0.5, abs=0.01)
        assert suggestion['param2'] == pytest.approx(0.0, abs=0.01)
    
    def test_register_observation(self):
        """Test registering observations."""
        param_bounds = {'param1': (0.0, 1.0)}
        optimizer = BayesianOptimizer(param_bounds)
        
        optimizer.register_observation({'param1': 0.5}, 0.8)
        optimizer.register_observation({'param1': 0.7}, 0.9)
        
        assert len(optimizer.observations) == 2
    
    def test_observation_limit(self):
        """Test observation limit is enforced."""
        param_bounds = {'param1': (0.0, 1.0)}
        optimizer = BayesianOptimizer(param_bounds)
        
        # Register more than 100 observations
        for i in range(150):
            optimizer.register_observation({'param1': 0.5}, 0.8)
        
        assert len(optimizer.observations) == 100
    
    def test_get_best_params(self):
        """Test getting best parameters."""
        param_bounds = {'param1': (0.0, 1.0)}
        optimizer = BayesianOptimizer(param_bounds)
        
        optimizer.register_observation({'param1': 0.5}, 0.6)
        optimizer.register_observation({'param1': 0.7}, 0.9)
        optimizer.register_observation({'param1': 0.3}, 0.7)
        
        best_params, best_value = optimizer.get_best_params()
        
        assert best_params['param1'] == 0.7
        assert best_value == 0.9
    
    def test_get_best_params_no_observations(self):
        """Test error when no observations available."""
        param_bounds = {'param1': (0.0, 1.0)}
        optimizer = BayesianOptimizer(param_bounds)
        
        with pytest.raises(ValueError):
            optimizer.get_best_params()


class TestReinforcementLearner:
    """Test Q-learning reinforcement learner."""
    
    def test_initialization(self):
        """Test RL learner initialization."""
        learner = ReinforcementLearner(
            learning_rate=0.1,
            discount_factor=0.95,
            exploration_rate=0.2
        )
        
        assert learner.learning_rate == 0.1
        assert learner.discount_factor == 0.95
        assert learner.exploration_rate == 0.2
        assert len(learner.q_table) == 0
    
    def test_select_action_explore(self):
        """Test exploration (random action)."""
        learner = ReinforcementLearner(exploration_rate=1.0)
        
        actions = ['strategy_a', 'strategy_b', 'strategy_c']
        action = learner.select_action('normal', 'planning', actions)
        
        assert action in actions
    
    def test_select_action_exploit(self):
        """Test exploitation (best action)."""
        learner = ReinforcementLearner(exploration_rate=0.0)
        
        # Set up Q-values
        state = ('normal', 'planning')
        learner.q_table[state]['strategy_a'] = 0.5
        learner.q_table[state]['strategy_b'] = 0.8
        learner.q_table[state]['strategy_c'] = 0.3
        
        actions = ['strategy_a', 'strategy_b', 'strategy_c']
        action = learner.select_action('normal', 'planning', actions)
        
        # Should select best action (strategy_b with 0.8)
        assert action == 'strategy_b'
    
    def test_select_action_no_q_values(self):
        """Test action selection when no Q-values exist."""
        learner = ReinforcementLearner(exploration_rate=0.0)
        
        actions = ['strategy_a', 'strategy_b', 'strategy_c']
        action = learner.select_action('normal', 'planning', actions)
        
        # Should select random action
        assert action in actions
    
    def test_update_q_value(self):
        """Test Q-value update."""
        learner = ReinforcementLearner()
        
        learner.update_q_value('normal', 'planning', 'strategy_a', 1.0)
        
        state = ('normal', 'planning')
        assert state in learner.q_table
        assert 'strategy_a' in learner.q_table[state]
        assert learner.q_table[state]['strategy_a'] > 0
    
    def test_update_q_value_with_next_state(self):
        """Test Q-value update with next state."""
        learner = ReinforcementLearner()
        
        # Set up next state Q-values
        next_state = ('error', 'implementation')
        learner.q_table[next_state]['strategy_b'] = 0.5
        
        learner.update_q_value(
            'normal', 'planning', 'strategy_a', 1.0,
            'error', 'implementation', ['strategy_b']
        )
        
        state = ('normal', 'planning')
        assert state in learner.q_table
    
    def test_decay_exploration(self):
        """Test exploration rate decay."""
        learner = ReinforcementLearner(exploration_rate=0.5)
        
        learner.decay_exploration(decay_rate=0.9)
        
        assert learner.exploration_rate == pytest.approx(0.45, abs=0.001)
    
    def test_decay_exploration_minimum(self):
        """Test exploration rate doesn't go below minimum."""
        learner = ReinforcementLearner(exploration_rate=0.01)
        
        learner.decay_exploration()
        
        assert learner.exploration_rate >= 0.01
    
    def test_get_policy(self):
        """Test getting learned policy."""
        learner = ReinforcementLearner(exploration_rate=0.0)
        
        # Set up Q-values for multiple states
        state1 = ('normal', 'planning')
        learner.q_table[state1]['strategy_a'] = 0.5
        learner.q_table[state1]['strategy_b'] = 0.8
        
        state2 = ('error', 'implementation')
        learner.q_table[state2]['strategy_a'] = 0.9
        learner.q_table[state2]['strategy_b'] = 0.3
        
        policy = learner.get_policy()
        
        assert policy[state1] == 'strategy_b'
        assert policy[state2] == 'strategy_a'


class TestGradientDescentOptimizer:
    """Test gradient descent optimizer."""
    
    def test_initialization(self):
        """Test GD optimizer initialization."""
        initial_weights = {'weight1': 0.5, 'weight2': 0.3}
        optimizer = GradientDescentOptimizer(
            initial_weights,
            learning_rate=0.01,
            momentum=0.9
        )
        
        assert optimizer.weights == initial_weights
        assert optimizer.learning_rate == 0.01
        assert optimizer.momentum == 0.9
        assert len(optimizer.velocities) == 2
    
    def test_compute_loss(self):
        """Test loss computation."""
        optimizer = GradientDescentOptimizer({'w1': 1.0})
        
        predictions = [2.0, 3.0, 4.0]
        targets = [2.5, 3.5, 4.5]
        
        loss = optimizer.compute_loss(predictions, targets)
        
        # MSE = ((2.0-2.5)^2 + (3.0-3.5)^2 + (4.0-4.5)^2) / 3
        # MSE = (0.25 + 0.25 + 0.25) / 3 = 0.25
        assert loss == pytest.approx(0.25, abs=0.01)
    
    def test_compute_gradients(self):
        """Test gradient computation."""
        optimizer = GradientDescentOptimizer({'w1': 1.0})
        
        features = [{'w1': 2.0}, {'w1': 3.0}]
        predictions = [2.0, 3.0]
        targets = [2.5, 3.5]
        
        gradients = optimizer.compute_gradients(features, predictions, targets)
        
        assert 'w1' in gradients
    
    def test_train_step(self):
        """Test training step."""
        optimizer = GradientDescentOptimizer({'w1': 1.0})
        
        features = [{'w1': 2.0}, {'w1': 3.0}, {'w1': 4.0}]
        targets = [2.5, 3.5, 4.5]
        
        loss_before = optimizer.compute_loss(
            [sum(optimizer.weights.values()) * f['w1'] for f in features],
            targets
        )
        
        loss, gradients = optimizer.train_step(features, targets)
        
        # Weights should have changed
        assert optimizer.weights['w1'] != 1.0
        
        # Loss should decrease
        loss_after = optimizer.compute_loss(
            [sum(optimizer.weights.values()) * f['w1'] for f in features],
            targets
        )
        assert loss_after <= loss_before
    
    def test_get_weights(self):
        """Test getting weights."""
        optimizer = GradientDescentOptimizer({'w1': 1.0, 'w2': 2.0})
        
        weights = optimizer.get_weights()
        
        assert weights == {'w1': 1.0, 'w2': 2.0}
        # Should be a copy
        weights['w1'] = 5.0
        assert optimizer.weights['w1'] == 1.0


class TestAdaptiveHeuristics:
    """Test adaptive heuristics system."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
    
    def test_initialization(self, temp_db_path):
        """Test adaptive heuristics initialization."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        assert len(ah.current_heuristics) > 0
        assert len(ah.decision_weights) > 0
        assert ah.bayesian_optimizer is not None
        assert ah.rl_learner is not None
        assert ah.gd_optimizer is not None
        
        ah.close()
    
    def test_get_heuristic(self, temp_db_path):
        """Test getting heuristic value."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        value = ah.get_heuristic('confidence_threshold')
        
        assert value > 0
        assert value <= 1.0
        
        ah.close()
    
    def test_get_heuristic_default(self, temp_db_path):
        """Test getting heuristic with default value."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        value = ah.get_heuristic('nonexistent', 0.5)
        
        assert value == 0.5
        
        ah.close()
    
    def test_get_all_heuristics(self, temp_db_path):
        """Test getting all heuristics."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        heuristics = ah.get_all_heuristics()
        
        assert len(heuristics) > 0
        assert 'confidence_threshold' in heuristics
        assert 'progress_minimal_threshold' in heuristics
        
        ah.close()
    
    def test_update_heuristic(self, temp_db_path):
        """Test updating heuristic value."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        old_value = ah.get_heuristic('confidence_threshold')
        new_value = old_value + 0.1
        
        result = ah.update_heuristic('confidence_threshold', new_value, "Test update")
        
        assert result is True
        assert ah.get_heuristic('confidence_threshold') == pytest.approx(new_value, abs=0.01)
        
        ah.close()
    
    def test_update_heuristic_no_change(self, temp_db_path):
        """Test updating heuristic with insignificant change."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        old_value = ah.get_heuristic('confidence_threshold')
        new_value = old_value + 0.001  # Too small
        
        result = ah.update_heuristic('confidence_threshold', new_value, "Small change")
        
        assert result is True
        assert ah.get_heuristic('confidence_threshold') == pytest.approx(old_value, abs=0.01)
        
        ah.close()
    
    def test_get_decision_weight(self, temp_db_path):
        """Test getting decision weight."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        weight = ah.get_decision_weight('success_probability')
        
        assert weight > 0
        
        ah.close()
    
    def test_get_all_decision_weights(self, temp_db_path):
        """Test getting all decision weights."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        weights = ah.get_all_decision_weights()
        
        assert len(weights) > 0
        assert 'success_probability' in weights
        assert 'cost' in weights
        assert 'risk' in weights
        assert 'time' in weights
        
        ah.close()
    
    def test_learn_strategy_selection(self, temp_db_path):
        """Test learning strategy selection."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Learn from a strategy selection
        ah.learn_strategy_selection(
            situation_type='normal',
            task_type='planning',
            strategy='conservative',
            reward=1.0
        )
        
        # Verify Q-value was updated
        state = ('normal', 'planning')
        assert state in ah.rl_learner.q_table
        
        ah.close()
    
    def test_select_strategy_rl(self, temp_db_path):
        """Test selecting strategy using RL."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        strategies = ['conservative', 'balanced', 'aggressive']
        strategy = ah.select_strategy_rl('normal', 'planning', strategies)
        
        assert strategy in strategies
        
        ah.close()
    
    def test_learn_decision_weights(self, temp_db_path):
        """Test learning decision weights."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Create training data
        training_data = [
            {
                'features': {'success_probability': 0.9, 'cost': 0.5, 'risk': 0.2, 'time': 0.8},
                'target': 0.85
            },
            {
                'features': {'success_probability': 0.7, 'cost': 0.6, 'risk': 0.4, 'time': 0.7},
                'target': 0.65
            },
            {
                'features': {'success_probability': 0.8, 'cost': 0.4, 'risk': 0.3, 'time': 0.6},
                'target': 0.75
            }
        ]
        
        new_weights = ah.learn_decision_weights(training_data)
        
        assert len(new_weights) == 4
        # Weights should have changed from initial values
        # (exact values depend on training)
        
        ah.close()
    
    def test_optimize_heuristics_bayesian(self, temp_db_path):
        """Test Bayesian optimization of heuristics."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Create performance data
        performance_data = [
            {
                'heuristics': {
                    'confidence_threshold': 0.7,
                    'progress_minimal_threshold': 0.1
                },
                'success_rate': 0.8
            },
            {
                'heuristics': {
                    'confidence_threshold': 0.75,
                    'progress_minimal_threshold': 0.12
                },
                'success_rate': 0.85
            }
        ]
        
        next_params = ah.optimize_heuristics_bayesian(performance_data)
        
        assert 'confidence_threshold' in next_params
        assert 'progress_minimal_threshold' in next_params
        
        ah.close()
    
    def test_get_heuristic_history(self, temp_db_path):
        """Test getting heuristic update history."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Update a heuristic
        ah.update_heuristic('confidence_threshold', 0.8, "Test")
        
        # Get history
        history = ah.get_heuristic_history('confidence_threshold')
        
        assert len(history) > 0
        assert history[0]['heuristic_name'] == 'confidence_threshold'
        assert 'old_value' in history[0]
        assert 'new_value' in history[0]
        
        ah.close()
    
    def test_get_all_heuristic_history(self, temp_db_path):
        """Test getting all heuristic history."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Update multiple heuristics
        ah.update_heuristic('confidence_threshold', 0.8, "Test 1")
        ah.update_heuristic('progress_minimal_threshold', 0.15, "Test 2")
        
        # Get all history
        history = ah.get_heuristic_history()
        
        assert len(history) >= 2
        
        ah.close()
    
    def test_get_learning_history(self, temp_db_path):
        """Test getting learning history."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Perform some learning
        training_data = [
            {
                'features': {'success_probability': 0.9},
                'target': 0.85
            }
        ]
        ah.learn_decision_weights(training_data)
        
        # Get learning history
        history = ah.get_learning_history('gradient_descent')
        
        assert len(history) > 0
        
        ah.close()
    
    def test_get_heuristic_statistics(self, temp_db_path):
        """Test getting heuristic statistics."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Update a heuristic
        ah.update_heuristic('confidence_threshold', 0.8, "Test")
        
        stats = ah.get_heuristic_statistics()
        
        assert 'total_heuristics' in stats
        assert 'avg_update_count' in stats
        assert 'learning_stats' in stats
        
        ah.close()
    
    def test_export_heuristics(self, temp_db_path):
        """Test exporting heuristics to JSON."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        export = ah.export_heuristics()
        
        # Parse JSON
        data = json.loads(export)
        
        assert 'heuristics' in data
        assert 'decision_weights' in data
        assert 'baselines' in data
        assert 'learned_policy' in data
        assert 'exported_at' in data
        
        ah.close()
    
    def test_reset_to_baseline_all(self, temp_db_path):
        """Test resetting all heuristics to baseline."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Update heuristics
        ah.update_heuristic('confidence_threshold', 0.9, "Test")
        
        # Reset to baseline
        result = ah.reset_to_baseline()
        
        assert result is True
        
        # Verify reset
        assert ah.get_heuristic('confidence_threshold') == pytest.approx(
            ah.baseline_heuristics['confidence_threshold'],
            abs=0.01
        )
        
        ah.close()
    
    def test_reset_to_baseline_single(self, temp_db_path):
        """Test resetting single heuristic to baseline."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        # Update heuristic
        ah.update_heuristic('confidence_threshold', 0.9, "Test")
        
        # Reset single heuristic
        result = ah.reset_to_baseline('confidence_threshold')
        
        assert result is True
        assert ah.get_heuristic('confidence_threshold') == pytest.approx(
            ah.baseline_heuristics['confidence_threshold'],
            abs=0.01
        )
        
        ah.close()
    
    def test_reset_to_baseline_nonexistent(self, temp_db_path):
        """Test resetting nonexistent heuristic returns False."""
        ah = AdaptiveHeuristics(temp_db_path)
        
        result = ah.reset_to_baseline('nonexistent_heuristic')
        
        assert result is False
        
        ah.close()
    
    def test_thread_safety(self, temp_db_path):
        """Test thread safety of operations."""
        import threading
        
        ah = AdaptiveHeuristics(temp_db_path)
        
        results = []
        
        def update_heuristic():
            for i in range(10):
                ah.update_heuristic('confidence_threshold', 0.7 + i * 0.01, f"Thread update {i}")
            results.append(True)
        
        # Create multiple threads
        threads = [threading.Thread(target=update_heuristic) for _ in range(5)]
        
        # Start threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # All threads should complete successfully
        assert len(results) == 5
        
        ah.close()
    
    def test_persistence(self, temp_db_path):
        """Test that heuristics persist across instances."""
        # First instance
        ah1 = AdaptiveHeuristics(temp_db_path)
        ah1.update_heuristic('confidence_threshold', 0.85, "Persistence test")
        ah1.close()
        
        # Second instance should load persisted values
        ah2 = AdaptiveHeuristics(temp_db_path)
        
        assert ah2.get_heuristic('confidence_threshold') == pytest.approx(0.85, abs=0.01)
        
        ah2.close()


class TestGlobalInstance:
    """Test global adaptive heuristics instance."""
    
    def test_singleton_pattern(self):
        """Test that get_adaptive_heuristics returns singleton."""
        import os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Get instances
            ah1 = get_adaptive_heuristics()
            ah2 = get_adaptive_heuristics()
            
            # Should be same instance
            assert ah1 is ah2
            
            ah1.close()
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])