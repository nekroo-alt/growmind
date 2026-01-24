"""
Progress Prediction Module

Implements progress prediction for time and resource estimation using multiple
prediction methods including historical averaging, linear regression, and ML models.

Part of V4 Enhancement: Progress Validation and Tracking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime, timedelta
import json
import math
from statistics import mean, median, stdev

# Import progress tracker components
from logic.progress_tracker import (
    ProgressMetrics,
    ProgressTracker,
    CodeProgressMetrics,
    TaskProgressMetrics,
    SessionProgressMetrics,
    ProjectProgressMetrics,
    ProgressMetricType
)


class PredictionMethod(Enum):
    """Methods for progress prediction"""
    HISTORICAL_AVERAGE = "historical_average"
    LINEAR_REGRESSION = "linear_regression"
    ML_MODEL = "ml_model"
    HYBRID = "hybrid"


@dataclass
class TaskPrediction:
    """
    Prediction for task completion
    
    Contains time estimates, resource estimates, and success probability
    for a task based on current progress and historical data.
    """
    task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Time predictions (seconds)
    time_to_completion: float = 0.0
    time_confidence_interval: Tuple[float, float] = (0.0, 0.0)  # (min, max)
    
    # Resource predictions
    tokens_needed: int = 0
    api_calls_needed: int = 0
    compute_hours_needed: float = 0.0
    
    # Success predictions
    success_probability: float = 0.0  # 0.0 to 1.0
    confidence_score: float = 0.0  # 0.0 to 1.0
    
    # Method used
    prediction_method: PredictionMethod = PredictionMethod.HISTORICAL_AVERAGE
    
    # Additional factors
    complexity_score: float = 0.0  # 0.0 to 1.0
    similarity_score: float = 0.0  # 0.0 to 1.0 (to historical tasks)
    
    # Progress information
    current_progress: float = 0.0  # 0.0 to 100.0
    current_progress_rate: float = 0.0  # progress per hour
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'task_id': self.task_id,
            'timestamp': self.timestamp.isoformat(),
            'time_to_completion': self.time_to_completion,
            'time_confidence_interval': list(self.time_confidence_interval),
            'tokens_needed': self.tokens_needed,
            'api_calls_needed': self.api_calls_needed,
            'compute_hours_needed': self.compute_hours_needed,
            'success_probability': self.success_probability,
            'confidence_score': self.confidence_score,
            'prediction_method': self.prediction_method.value,
            'complexity_score': self.complexity_score,
            'similarity_score': self.similarity_score,
            'current_progress': self.current_progress,
            'current_progress_rate': self.current_progress_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskPrediction':
        """Create from dictionary"""
        return cls(
            task_id=data.get('task_id'),
            timestamp=datetime.fromisoformat(data['timestamp']),
            time_to_completion=data['time_to_completion'],
            time_confidence_interval=tuple(data['time_confidence_interval']),
            tokens_needed=data['tokens_needed'],
            api_calls_needed=data['api_calls_needed'],
            compute_hours_needed=data['compute_hours_needed'],
            success_probability=data['success_probability'],
            confidence_score=data['confidence_score'],
            prediction_method=PredictionMethod(data['prediction_method']),
            complexity_score=data['complexity_score'],
            similarity_score=data['similarity_score'],
            current_progress=data['current_progress'],
            current_progress_rate=data['current_progress_rate']
        )


@dataclass
class PredictionAccuracy:
    """
    Metrics for tracking prediction accuracy
    
    Tracks how accurate predictions have been compared to actual results.
    """
    # Time accuracy metrics
    time_mae: float = 0.0  # Mean Absolute Error
    time_rmse: float = 0.0  # Root Mean Square Error
    time_mape: float = 0.0  # Mean Absolute Percentage Error
    
    # Resource accuracy metrics
    token_mae: float = 0.0
    token_mape: float = 0.0
    
    # Success accuracy metrics
    success_accuracy: float = 0.0  # Percentage of correct success/failure predictions
    
    # Counters
    total_predictions: int = 0
    successful_predictions: int = 0
    
    # Historical accuracy by method
    method_accuracy: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'time_mae': self.time_mae,
            'time_rmse': self.time_rmse,
            'time_mape': self.time_mape,
            'token_mae': self.token_mae,
            'token_mape': self.token_mape,
            'success_accuracy': self.success_accuracy,
            'total_predictions': self.total_predictions,
            'successful_predictions': self.successful_predictions,
            'method_accuracy': self.method_accuracy
        }


class ProgressPredictor:
    """
    Progress predictor for time and resource estimation
    
    Uses multiple prediction methods (historical average, linear regression, ML)
    to predict task completion time, resource needs, and success probability.
    Continuously learns from prediction errors to improve accuracy.
    """
    
    def __init__(self, use_ml_model: bool = False):
        """
        Initialize progress predictor
        
        Args:
            use_ml_model: Whether to use ML model (requires training data)
        """
        self.use_ml_model = use_ml_model
        self.ml_model = None
        self.ml_model_trained = False
        
        # Historical data for predictions
        self.historical_tasks: List[Dict[str, Any]] = []
        
        # Prediction accuracy tracking
        self.accuracy = PredictionAccuracy()
        
        # Weights for hybrid prediction
        self.hybrid_weights = {
            'historical_average': 0.3,
            'linear_regression': 0.5,
            'ml_model': 0.2
        }
        
    def predict_completion_time(self,
                                 tracker: ProgressTracker,
                                 method: PredictionMethod = PredictionMethod.HYBRID) -> TaskPrediction:
        """
        Predict time to complete current task
        
        Args:
            tracker: Progress tracker with current metrics
            method: Prediction method to use
        
        Returns:
            TaskPrediction with time and resource estimates
        """
        # Get current progress information
        current_progress = tracker._calculate_overall_progress()
        progress_rate = tracker._calculate_progress_for_type(ProgressMetricType.CODE)  # Use code progress
        
        # Calculate elapsed time
        elapsed_time = 0.0
        if tracker.start_time:
            elapsed_time = (datetime.now() - tracker.start_time).total_seconds()
        
        # Calculate progress rate (percent per hour)
        if elapsed_time > 0 and current_progress > 0:
            progress_rate_per_hour = (current_progress / 100) / (elapsed_time / 3600)
        else:
            progress_rate_per_hour = 0.0
        
        # Initialize prediction
        prediction = TaskPrediction(
            task_id=tracker.task_id,
            current_progress=current_progress,
            current_progress_rate=progress_rate_per_hour
        )
        
        # Get predictions from different methods
        historical_pred = self._predict_historical_average(tracker, progress_rate_per_hour)
        regression_pred = self._predict_linear_regression(tracker, progress_rate_per_hour)
        ml_pred = None
        
        if self.use_ml_model and self.ml_model_trained:
            ml_pred = self._predict_ml_model(tracker)
        
        # Combine predictions based on method
        if method == PredictionMethod.HISTORICAL_AVERAGE:
            prediction = historical_pred
        elif method == PredictionMethod.LINEAR_REGRESSION:
            prediction = regression_pred
        elif method == PredictionMethod.ML_MODEL:
            if ml_pred:
                prediction = ml_pred
            else:
                # Fall back to regression if ML not available
                prediction = regression_pred
                prediction.prediction_method = PredictionMethod.LINEAR_REGRESSION
        elif method == PredictionMethod.HYBRID:
            prediction = self._combine_predictions(historical_pred, regression_pred, ml_pred)
        
        # Update task_id and timestamp
        prediction.task_id = tracker.task_id
        prediction.timestamp = datetime.now()
        prediction.current_progress = current_progress
        prediction.current_progress_rate = progress_rate_per_hour
        
        return prediction
        
    def _predict_historical_average(self,
                                   tracker: ProgressTracker,
                                   progress_rate: float) -> TaskPrediction:
        """
        Predict using historical average method
        
        Args:
            tracker: Progress tracker
            progress_rate: Current progress rate (percent per hour)
        
        Returns:
            TaskPrediction
        """
        prediction = TaskPrediction(prediction_method=PredictionMethod.HISTORICAL_AVERAGE)
        
        if not self.historical_tasks:
            # No historical data - use current progress rate if available
            if progress_rate > 0:
                remaining_progress = 100.0 - tracker._calculate_overall_progress()
                prediction.time_to_completion = (remaining_progress / 100.0) / progress_rate * 3600
                prediction.time_confidence_interval = (
                    prediction.time_to_completion * 0.5,
                    prediction.time_to_completion * 2.0
                )
            else:
                # Default estimate: 1 hour per 10% progress
                remaining_progress = 100.0 - tracker._calculate_overall_progress()
                prediction.time_to_completion = (remaining_progress / 10.0) * 3600
                prediction.time_confidence_interval = (
                    prediction.time_to_completion * 0.7,
                    prediction.time_to_completion * 1.5
                )
            
            prediction.success_probability = 0.7
            prediction.confidence_score = 0.3
            prediction.complexity_score = 0.5
            prediction.similarity_score = 0.0
            
            # Default resource estimates
            prediction.tokens_needed = 5000
            prediction.api_calls_needed = 10
            prediction.compute_hours_needed = prediction.time_to_completion / 3600.0
            
            return prediction
        
        # Find similar historical tasks
        similar_tasks = self._find_similar_tasks(tracker, top_k=5)
        
        if similar_tasks:
            # Use average of similar tasks
            avg_time = mean([t.get('time_to_completion', 3600) for t in similar_tasks])
            avg_tokens = mean([t.get('tokens_used', 5000) for t in similar_tasks])
            avg_api_calls = mean([t.get('api_calls', 10) for t in similar_tasks])
            success_rate = mean([t.get('success', True) for t in similar_tasks])
            
            prediction.time_to_completion = avg_time
            prediction.tokens_needed = int(avg_tokens)
            prediction.api_calls_needed = int(avg_api_calls)
            prediction.success_probability = success_rate
            prediction.confidence_score = min(0.7, 0.4 + len(similar_tasks) * 0.1)
            prediction.complexity_score = mean([t.get('complexity', 0.5) for t in similar_tasks])
            prediction.similarity_score = mean([t.get('similarity', 0.5) for t in similar_tasks])
            
            # Calculate confidence interval
            time_values = [t.get('time_to_completion', 3600) for t in similar_tasks]
            if len(time_values) > 1:
                std_dev = stdev(time_values)
                prediction.time_confidence_interval = (
                    max(0, avg_time - std_dev),
                    avg_time + std_dev
                )
            else:
                prediction.time_confidence_interval = (avg_time * 0.5, avg_time * 2.0)
        else:
            # No similar tasks - use overall average
            avg_time = mean([t.get('time_to_completion', 3600) for t in self.historical_tasks])
            avg_tokens = mean([t.get('tokens_used', 5000) for t in self.historical_tasks])
            avg_api_calls = mean([t.get('api_calls', 10) for t in self.historical_tasks])
            success_rate = mean([t.get('success', True) for t in self.historical_tasks])
            
            prediction.time_to_completion = avg_time
            prediction.tokens_needed = int(avg_tokens)
            prediction.api_calls_needed = int(avg_api_calls)
            prediction.success_probability = success_rate
            prediction.confidence_score = 0.5
            prediction.complexity_score = 0.5
            prediction.similarity_score = 0.0
            prediction.time_confidence_interval = (avg_time * 0.5, avg_time * 2.0)
        
        prediction.compute_hours_needed = prediction.time_to_completion / 3600.0
        
        return prediction
        
    def _predict_linear_regression(self,
                                  tracker: ProgressTracker,
                                  progress_rate: float) -> TaskPrediction:
        """
        Predict using linear regression based on current progress rate
        
        Args:
            tracker: Progress tracker
            progress_rate: Current progress rate (percent per hour)
        
        Returns:
            TaskPrediction
        """
        prediction = TaskPrediction(prediction_method=PredictionMethod.LINEAR_REGRESSION)
        
        current_progress = tracker._calculate_overall_progress()
        remaining_progress = 100.0 - current_progress
        
        if progress_rate > 0:
            # Use current progress rate
            prediction.time_to_completion = (remaining_progress / 100.0) / progress_rate * 3600
            prediction.confidence_score = min(0.8, 0.5 + progress_rate * 0.3)
        else:
            # No progress rate - use historical regression
            if self.historical_tasks:
                # Linear regression on historical data
                times = [t.get('time_to_completion', 3600) for t in self.historical_tasks]
                complexities = [t.get('complexity', 0.5) for t in self.historical_tasks]
                
                if len(times) >= 2:
                    # Simple linear regression: time = a * complexity + b
                    avg_time = mean(times)
                    avg_complexity = mean(complexities)
                    
                    numerator = sum([(c - avg_complexity) * (t - avg_time) 
                                     for c, t in zip(complexities, times)])
                    denominator = sum([(c - avg_complexity) ** 2 for c in complexities])
                    
                    if denominator > 0:
                        slope = numerator / denominator
                        intercept = avg_time - slope * avg_complexity
                        
                        # Estimate complexity from current task
                        current_complexity = self._estimate_complexity(tracker)
                        prediction.time_to_completion = slope * current_complexity + intercept
                    else:
                        prediction.time_to_completion = avg_time
                    
                    # Calculate confidence interval
                    time_std = stdev(times) if len(times) > 1 else avg_time * 0.5
                    prediction.time_confidence_interval = (
                        max(0, prediction.time_to_completion - time_std),
                        prediction.time_to_completion + time_std
                    )
                else:
                    prediction.time_to_completion = mean(times)
                    prediction.time_confidence_interval = (mean(times) * 0.5, mean(times) * 2.0)
            else:
                # No historical data - default estimate
                prediction.time_to_completion = (remaining_progress / 10.0) * 3600
                prediction.time_confidence_interval = (
                    prediction.time_to_completion * 0.7,
                    prediction.time_to_completion * 1.5
                )
            
            prediction.confidence_score = 0.4
        
        # Calculate resource estimates based on time
        time_hours = prediction.time_to_completion / 3600.0
        prediction.tokens_needed = int(time_hours * 2000)  # 2000 tokens per hour
        prediction.api_calls_needed = int(time_hours * 4)  # 4 API calls per hour
        prediction.compute_hours_needed = time_hours
        
        # Estimate success probability based on progress
        if current_progress > 50:
            prediction.success_probability = 0.9
        elif current_progress > 25:
            prediction.success_probability = 0.8
        elif current_progress > 10:
            prediction.success_probability = 0.7
        else:
            prediction.success_probability = 0.6
        
        prediction.complexity_score = self._estimate_complexity(tracker)
        prediction.similarity_score = 0.0
        
        return prediction
        
    def _predict_ml_model(self, tracker: ProgressTracker) -> Optional[TaskPrediction]:
        """
        Predict using ML model (placeholder for actual ML implementation)
        
        Args:
            tracker: Progress tracker
        
        Returns:
            TaskPrediction or None if model not available
        """
        if not self.use_ml_model or not self.ml_model_trained:
            return None
        
        # TODO: Implement actual ML model prediction
        # This would use a trained model (e.g., scikit-learn, TensorFlow, PyTorch)
        # to predict time, resources, and success probability
        
        prediction = TaskPrediction(prediction_method=PredictionMethod.ML_MODEL)
        
        # Placeholder implementation
        # In real implementation, this would:
        # 1. Extract features from tracker
        # 2. Feed features to trained model
        # 3. Return model predictions
        
        return prediction
        
    def _combine_predictions(self,
                               historical: TaskPrediction,
                               regression: TaskPrediction,
                               ml: Optional[TaskPrediction] = None) -> TaskPrediction:
        """
        Combine predictions from multiple methods
        
        Args:
            historical: Prediction from historical average method
            regression: Prediction from linear regression method
            ml: Optional prediction from ML model
        
        Returns:
            Combined TaskPrediction
        """
        prediction = TaskPrediction(prediction_method=PredictionMethod.HYBRID)
        
        # Time prediction
        if ml and ml.prediction_method == PredictionMethod.ML_MODEL:
            prediction.time_to_completion = (
                self.hybrid_weights['historical_average'] * historical.time_to_completion +
                self.hybrid_weights['linear_regression'] * regression.time_to_completion +
                self.hybrid_weights['ml_model'] * ml.time_to_completion
            )
        else:
            prediction.time_to_completion = (
                self.hybrid_weights['historical_average'] * historical.time_to_completion +
                self.hybrid_weights['linear_regression'] * regression.time_to_completion
            )
        
        # Resource predictions (weighted average)
        prediction.tokens_needed = int(
            historical.tokens_needed * 0.5 + regression.tokens_needed * 0.5
        )
        prediction.api_calls_needed = int(
            historical.api_calls_needed * 0.5 + regression.api_calls_needed * 0.5
        )
        prediction.compute_hours_needed = prediction.time_to_completion / 3600.0
        
        # Success probability
        prediction.success_probability = (
            historical.success_probability * 0.4 +
            regression.success_probability * 0.6
        )
        
        # Confidence score (higher for hybrid)
        prediction.confidence_score = min(0.9, historical.confidence_score * 0.5 + regression.confidence_score * 0.5 + 0.1)
        
        # Complexity and similarity
        prediction.complexity_score = (historical.complexity_score + regression.complexity_score) / 2
        prediction.similarity_score = historical.similarity_score
        
        # Confidence interval (average of methods)
        min_time = (historical.time_confidence_interval[0] + regression.time_confidence_interval[0]) / 2
        max_time = (historical.time_confidence_interval[1] + regression.time_confidence_interval[1]) / 2
        prediction.time_confidence_interval = (min_time, max_time)
        
        return prediction
        
    def _find_similar_tasks(self,
                            tracker: ProgressTracker,
                            top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar historical tasks
        
        Args:
            tracker: Progress tracker with current task metrics
            top_k: Number of similar tasks to return
        
        Returns:
            List of similar task records
        """
        if not self.historical_tasks:
            return []
        
        # Calculate similarity score for each historical task
        for task in self.historical_tasks:
            similarity = self._calculate_similarity(tracker, task)
            task['similarity'] = similarity
        
        # Sort by similarity and return top_k
        similar_tasks = sorted(
            [t for t in self.historical_tasks if t.get('similarity', 0) > 0],
            key=lambda x: x['similarity'],
            reverse=True
        )
        
        return similar_tasks[:top_k]
        
    def _calculate_similarity(self,
                               tracker: ProgressTracker,
                               historical_task: Dict[str, Any]) -> float:
        """
        Calculate similarity between current task and historical task
        
        Args:
            tracker: Progress tracker with current task
            historical_task: Historical task record
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        similarity = 0.0
        total_weight = 0.0
        
        # Compare complexity
        current_complexity = self._estimate_complexity(tracker)
        historical_complexity = historical_task.get('complexity', 0.5)
        complexity_diff = abs(current_complexity - historical_complexity)
        complexity_sim = max(0, 1.0 - complexity_diff * 2)
        similarity += complexity_sim * 0.4
        total_weight += 0.4
        
        # Compare task type (if available)
        current_type = self._classify_task_type(tracker)
        historical_type = historical_task.get('task_type', 'unknown')
        type_sim = 1.0 if current_type == historical_type else 0.3
        similarity += type_sim * 0.3
        total_weight += 0.3
        
        # Compare progress (if historical has progress data)
        if 'progress' in historical_task:
            historical_progress = historical_task['progress']
            current_progress = tracker._calculate_overall_progress()
            progress_diff = abs(current_progress - historical_progress) / 100.0
            progress_sim = max(0, 1.0 - progress_diff)
            similarity += progress_sim * 0.3
            total_weight += 0.3
        else:
            total_weight += 0.3
        
        return similarity / total_weight if total_weight > 0 else 0.0
        
    def _estimate_complexity(self, tracker: ProgressTracker) -> float:
        """
        Estimate task complexity from tracker metrics
        
        Args:
            tracker: Progress tracker
        
        Returns:
            Complexity score (0.0 to 1.0)
        """
        complexity = 0.5  # Default
        
        # Consider number of subtasks
        task_metrics = tracker.metrics.task_metrics
        if task_metrics.subtasks_total > 0:
            # More subtasks = higher complexity
            complexity = min(1.0, 0.3 + (task_metrics.subtasks_total / 20.0))
        
        # Consider error rate
        if tracker.historical_metrics:
            recent_errors = sum(1 for m in tracker.historical_metrics[-5:] 
                             if m.session_metrics.errors_encountered > 0)
            error_rate = recent_errors / 5.0
            complexity += error_rate * 0.2
        
        # Consider cyclomatic complexity from code metrics
        code_metrics = tracker.metrics.code_metrics
        if code_metrics.cyclomatic_complexity > 0:
            complexity = min(1.0, complexity + code_metrics.cyclomatic_complexity * 0.01)
        
        return min(1.0, complexity)
        
    def _classify_task_type(self, tracker: ProgressTracker) -> str:
        """
        Classify task type from tracker metrics
        
        Args:
            tracker: Progress tracker
        
        Returns:
            Task type string
        """
        # Simple classification based on metrics
        # Check in order of specificity (most specific first)
        if tracker.metrics.code_metrics.lines_modified > 100:
            return 'refactoring'
        elif tracker.metrics.code_metrics.files_added > 5:
            return 'new_feature'
        elif tracker.metrics.code_metrics.test_coverage_percent > 0:
            return 'testing'
        else:
            return 'bug_fix'
        
    def record_actual_result(self,
                              prediction: TaskPrediction,
                              actual_time: float,
                              actual_tokens: int,
                              actual_api_calls: int,
                              success: bool):
        """
        Record actual results to improve future predictions
        
        Args:
            prediction: Original prediction
            actual_time: Actual time to complete (seconds)
            actual_tokens: Actual tokens used
            actual_api_calls: Actual API calls made
            success: Whether task succeeded
        """
        # Calculate errors
        time_error = abs(prediction.time_to_completion - actual_time)
        time_error_pct = (time_error / actual_time * 100) if actual_time > 0 else 0
        
        token_error = abs(prediction.tokens_needed - actual_tokens)
        token_error_pct = (token_error / actual_tokens * 100) if actual_tokens > 0 else 0
        
        # Update accuracy metrics
        n = self.accuracy.total_predictions
        
        # Running average for MAE
        if n == 0:
            self.accuracy.time_mae = time_error
            self.accuracy.token_mae = token_error
        else:
            self.accuracy.time_mae = (self.accuracy.time_mae * n + time_error) / (n + 1)
            self.accuracy.token_mae = (self.accuracy.token_mae * n + token_error) / (n + 1)
        
        # Running average for MAPE
        if n == 0:
            self.accuracy.time_mape = time_error_pct
            self.accuracy.token_mape = token_error_pct
        else:
            self.accuracy.time_mape = (self.accuracy.time_mape * n + time_error_pct) / (n + 1)
            self.accuracy.token_mape = (self.accuracy.token_mae * n + token_error_pct) / (n + 1)
        
        # Update RMSE
        if n == 0:
            self.accuracy.time_rmse = time_error ** 2
        else:
            self.accuracy.time_rmse = (self.accuracy.time_rmse * n + time_error ** 2) / (n + 1)
        self.accuracy.time_rmse = math.sqrt(self.accuracy.time_rmse)
        
        # Update success accuracy
        success_prediction = prediction.success_probability >= 0.5
        if success_prediction == success:
            self.accuracy.successful_predictions += 1
        self.accuracy.total_predictions += 1
        self.accuracy.success_accuracy = (
            self.accuracy.successful_predictions / self.accuracy.total_predictions * 100
        )
        
        # Update method accuracy
        method = prediction.prediction_method.value
        if method not in self.accuracy.method_accuracy:
            self.accuracy.method_accuracy[method] = 0.0
        
        method_success = (time_error_pct < 20) and (token_error_pct < 20) and (success_prediction == success)
        method_n = sum(1 for t in self.historical_tasks if t.get('method') == method) + 1
        
        current_accuracy = self.accuracy.method_accuracy.get(method, 0.0)
        new_accuracy = (current_accuracy * (method_n - 1) + (1.0 if method_success else 0.0)) / method_n
        self.accuracy.method_accuracy[method] = new_accuracy
        
        # Add to historical tasks
        historical_task = {
            'task_id': prediction.task_id,
            'timestamp': prediction.timestamp.isoformat(),
            'time_to_completion': actual_time,
            'tokens_used': actual_tokens,
            'api_calls': actual_api_calls,
            'success': success,
            'method': method,
            'complexity': prediction.complexity_score,
            'progress': prediction.current_progress
        }
        self.historical_tasks.append(historical_task)
        
        # Limit historical tasks size
        if len(self.historical_tasks) > 1000:
            self.historical_tasks = self.historical_tasks[-1000:]
        
        # Retrain ML model if enabled
        if self.use_ml_model:
            self._retrain_ml_model()
        
    def _retrain_ml_model(self):
        """
        Retrain ML model with historical data
        
        Note: This is a placeholder for actual ML training.
        Real implementation would use scikit-learn, TensorFlow, or PyTorch.
        """
        if not self.use_ml_model or len(self.historical_tasks) < 10:
            return
        
        # TODO: Implement actual ML model training
        # This would:
        # 1. Prepare features from historical tasks
        # 2. Prepare labels (time, tokens, success)
        # 3. Train model (e.g., Random Forest, Gradient Boosting, Neural Network)
        # 4. Set ml_model_trained = True
        
        self.ml_model_trained = True
        
    def update_prediction(self,
                         tracker: ProgressTracker,
                         old_prediction: TaskPrediction) -> TaskPrediction:
        """
        Update prediction as work progresses
        
        Args:
            tracker: Updated progress tracker
            old_prediction: Previous prediction
        
        Returns:
            Updated TaskPrediction
        """
        # Get new prediction
        new_prediction = self.predict_completion_time(tracker, old_prediction.prediction_method)
        
        # Blend old and new predictions based on progress
        progress = tracker._calculate_overall_progress()
        
        # As progress increases, trust new prediction more
        new_weight = progress / 100.0
        old_weight = 1.0 - new_weight
        
        # Time prediction (weighted average)
        new_prediction.time_to_completion = (
            old_weight * old_prediction.time_to_completion +
            new_weight * new_prediction.time_to_completion
        )
        
        # Resource predictions (weighted average)
        new_prediction.tokens_needed = int(
            old_weight * old_prediction.tokens_needed +
            new_weight * new_prediction.tokens_needed
        )
        new_prediction.api_calls_needed = int(
            old_weight * old_prediction.api_calls_needed +
            new_weight * new_prediction.api_calls_needed
        )
        
        # Success probability (weighted average)
        new_prediction.success_probability = (
            old_weight * old_prediction.success_probability +
            new_weight * new_prediction.success_probability
        )
        
        # Confidence increases with progress
        new_prediction.confidence_score = min(0.95, old_prediction.confidence_score * 0.5 + new_prediction.confidence_score * 0.5 + 0.1)
        
        return new_prediction
        
    def get_accuracy_report(self) -> Dict[str, Any]:
        """
        Get accuracy report for predictions
        
        Returns:
            Dictionary with accuracy metrics
        """
        return self.accuracy.to_dict()
        
    def export_predictions(self, filepath: str):
        """
        Export predictions and accuracy data to JSON
        
        Args:
            filepath: Path to JSON file
        """
        data = {
            'accuracy': self.accuracy.to_dict(),
            'hybrid_weights': self.hybrid_weights,
            'historical_tasks': self.historical_tasks,
            'ml_model_trained': self.ml_model_trained
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load_predictions(self, filepath: str):
        """
        Load predictions and accuracy data from JSON
        
        Args:
            filepath: Path to JSON file
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.accuracy = PredictionAccuracy(**data.get('accuracy', {}))
        self.hybrid_weights = data.get('hybrid_weights', self.hybrid_weights)
        self.historical_tasks = data.get('historical_tasks', [])
        self.ml_model_trained = data.get('ml_model_trained', False)
        
    def clear_historical_data(self):
        """Clear all historical prediction data"""
        self.historical_tasks = []
        self.accuracy = PredictionAccuracy()
        self.ml_model_trained = False