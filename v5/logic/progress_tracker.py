"""
Progress Metrics Definition and Tracking

This module defines comprehensive progress metrics for code, task, session, and project
progress, along with thresholds and goals for validating development progress.

Part of V4 Enhancement: Progress Validation and Tracking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import json


class ProgressMetricType(Enum):
    """Types of progress metrics"""
    CODE = "code"
    TASK = "task"
    SESSION = "session"
    PROJECT = "project"
    CUSTOM = "custom"


@dataclass
class CodeProgressMetrics:
    """
    Metrics for tracking code progress
    
    Tracks changes to the codebase including additions, modifications, deletions,
    and quality metrics like tests and code coverage.
    """
    # Line changes
    lines_added: int = 0
    lines_modified: int = 0
    lines_deleted: int = 0
    
    # Test metrics
    tests_passing: int = 0
    tests_failing: int = 0
    tests_total: int = 0
    test_coverage_percent: float = 0.0
    
    # Quality metrics
    code_coverage_percent: float = 0.0
    cyclomatic_complexity: float = 0.0
    maintainability_index: float = 0.0
    
    # File metrics
    files_added: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    
    def total_lines_changed(self) -> int:
        """Total lines changed (added + modified + deleted)"""
        return self.lines_added + self.lines_modified + self.lines_deleted
    
    def test_pass_rate(self) -> float:
        """Calculate test pass rate as percentage"""
        if self.tests_total == 0:
            return 100.0  # No tests means 100% by default
        return (self.tests_passing / self.tests_total) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'lines_added': self.lines_added,
            'lines_modified': self.lines_modified,
            'lines_deleted': self.lines_deleted,
            'tests_passing': self.tests_passing,
            'tests_failing': self.tests_failing,
            'tests_total': self.tests_total,
            'test_coverage_percent': self.test_coverage_percent,
            'code_coverage_percent': self.code_coverage_percent,
            'cyclomatic_complexity': self.cyclomatic_complexity,
            'maintainability_index': self.maintainability_index,
            'files_added': self.files_added,
            'files_modified': self.files_modified,
            'files_deleted': self.files_deleted
        }


@dataclass
class TaskProgressMetrics:
    """
    Metrics for tracking task progress
    
    Tracks completion status of tasks, subtasks, and acceptance criteria,
    along with time spent and resource usage.
    """
    # Completion metrics
    subtasks_total: int = 0
    subtasks_completed: int = 0
    
    # Acceptance criteria
    acceptance_criteria_total: int = 0
    acceptance_criteria_met: int = 0
    
    # Time metrics
    time_spent_seconds: float = 0.0
    time_estimated_seconds: float = 0.0
    
    # Resource metrics
    tokens_used: int = 0
    api_calls: int = 0
    
    # Status
    task_status: str = "pending"  # pending, in_progress, completed, failed, blocked
    
    def completion_percentage(self) -> float:
        """Calculate overall task completion percentage"""
        if self.subtasks_total == 0 and self.acceptance_criteria_total == 0:
            return 100.0 if self.task_status == "completed" else 0.0
        
        subtask_weight = 0.5 if self.subtasks_total > 0 else 0
        criteria_weight = 0.5 if self.acceptance_criteria_total > 0 else 0
        
        subtask_pct = (self.subtasks_completed / self.subtasks_total) * 100 if self.subtasks_total > 0 else 0
        criteria_pct = (self.acceptance_criteria_met / self.acceptance_criteria_total) * 100 if self.acceptance_criteria_total > 0 else 0
        
        return subtask_weight * subtask_pct + criteria_weight * criteria_pct
    
    def time_efficiency(self) -> float:
        """Calculate time efficiency (estimated / actual)"""
        if self.time_spent_seconds == 0:
            return 1.0
        return self.time_estimated_seconds / self.time_spent_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'subtasks_total': self.subtasks_total,
            'subtasks_completed': self.subtasks_completed,
            'acceptance_criteria_total': self.acceptance_criteria_total,
            'acceptance_criteria_met': self.acceptance_criteria_met,
            'time_spent_seconds': self.time_spent_seconds,
            'time_estimated_seconds': self.time_estimated_seconds,
            'tokens_used': self.tokens_used,
            'api_calls': self.api_calls,
            'task_status': self.task_status
        }


@dataclass
class SessionProgressMetrics:
    """
    Metrics for tracking session progress
    
    Tracks overall productivity during a development session including
    tasks completed, errors encountered, and efficiency metrics.
    """
    # Task metrics
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_blocked: int = 0
    
    # Error metrics
    errors_encountered: int = 0
    errors_resolved: int = 0
    errors_remaining: int = 0
    
    # Time metrics
    session_duration_seconds: float = 0.0
    active_time_seconds: float = 0.0
    
    # Efficiency metrics
    operations_per_hour: float = 0.0
    success_rate: float = 0.0
    recovery_rate: float = 0.0
    
    # Code metrics
    total_lines_written: int = 0
    total_tests_added: int = 0
    
    def total_tasks(self) -> int:
        """Total tasks attempted"""
        return self.tasks_completed + self.tasks_failed + self.tasks_blocked
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate as percentage"""
        total = self.total_tasks()
        if total == 0:
            return 100.0
        return (self.tasks_completed / total) * 100.0
    
    def calculate_recovery_rate(self) -> float:
        """Calculate error recovery rate as percentage"""
        if self.errors_encountered == 0:
            return 100.0
        return (self.errors_resolved / self.errors_encountered) * 100.0
    
    def calculate_efficiency(self) -> float:
        """Calculate active time efficiency"""
        if self.session_duration_seconds == 0:
            return 100.0
        return (self.active_time_seconds / self.session_duration_seconds) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'tasks_blocked': self.tasks_blocked,
            'errors_encountered': self.errors_encountered,
            'errors_resolved': self.errors_resolved,
            'errors_remaining': self.errors_remaining,
            'session_duration_seconds': self.session_duration_seconds,
            'active_time_seconds': self.active_time_seconds,
            'operations_per_hour': self.operations_per_hour,
            'success_rate': self.success_rate,
            'recovery_rate': self.recovery_rate,
            'total_lines_written': self.total_lines_written,
            'total_tests_added': self.total_tests_added
        }


@dataclass
class ProjectProgressMetrics:
    """
    Metrics for tracking project progress
    
    Tracks high-level project progress including features implemented,
    issues resolved, milestones achieved, and overall project health.
    """
    # Feature metrics
    features_total: int = 0
    features_completed: int = 0
    features_in_progress: int = 0
    
    # Issue metrics
    issues_total: int = 0
    issues_resolved: int = 0
    issues_remaining: int = 0
    
    # Milestone metrics
    milestones_total: int = 0
    milestones_completed: int = 0
    milestone_progress: float = 0.0  # Progress toward next milestone
    
    # Quality metrics
    overall_code_coverage: float = 0.0
    bug_rate: float = 0.0
    technical_debt_score: float = 0.0
    
    # Release metrics
    release_percent: float = 0.0
    days_until_release: int = 0
    
    def feature_completion_percentage(self) -> float:
        """Calculate feature completion percentage"""
        if self.features_total == 0:
            return 100.0
        return (self.features_completed / self.features_total) * 100.0
    
    def issue_resolution_percentage(self) -> float:
        """Calculate issue resolution percentage"""
        if self.issues_total == 0:
            return 100.0
        return (self.issues_resolved / self.issues_total) * 100.0
    
    def milestone_completion_percentage(self) -> float:
        """Calculate milestone completion percentage"""
        if self.milestones_total == 0:
            return 100.0
        return (self.milestones_completed / self.milestones_total) * 100.0
    
    def overall_health_score(self) -> float:
        """Calculate overall project health score (0-100)"""
        feature_score = self.feature_completion_percentage() * 0.4
        issue_score = self.issue_resolution_percentage() * 0.2
        coverage_score = self.overall_code_coverage * 0.2
        quality_score = (100 - self.bug_rate) * 0.2
        
        return feature_score + issue_score + coverage_score + quality_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'features_total': self.features_total,
            'features_completed': self.features_completed,
            'features_in_progress': self.features_in_progress,
            'issues_total': self.issues_total,
            'issues_resolved': self.issues_resolved,
            'issues_remaining': self.issues_remaining,
            'milestones_total': self.milestones_total,
            'milestones_completed': self.milestones_completed,
            'milestone_progress': self.milestone_progress,
            'overall_code_coverage': self.overall_code_coverage,
            'bug_rate': self.bug_rate,
            'technical_debt_score': self.technical_debt_score,
            'release_percent': self.release_percent,
            'days_until_release': self.days_until_release
        }


@dataclass
class ProgressThresholds:
    """
    Progress thresholds and goals for validation
    
    Defines acceptable progress rates and minimum/expected/optimal
    performance levels for different metric types.
    """
    # Code progress thresholds (percentage of total code change)
    code_minimal: float = 0.10  # 10% progress per operation
    code_expected: float = 0.30  # 30% progress per operation
    code_optimal: float = 0.50  # 50%+ progress per operation
    
    # Task progress thresholds (percentage of task completion)
    task_minimal: float = 0.10  # 10% progress per operation
    task_expected: float = 0.30  # 30% progress per operation
    task_optimal: float = 0.50  # 50%+ progress per operation
    
    # Session progress thresholds (tasks per hour)
    session_minimal: float = 1.0  # 1 task per hour
    session_expected: float = 2.0  # 2 tasks per hour
    session_optimal: float = 3.0  # 3+ tasks per hour
    
    # Project progress thresholds (percentage of project completion)
    project_minimal: float = 0.05  # 5% progress per day
    project_expected: float = 0.10  # 10% progress per day
    project_optimal: float = 0.20  # 20%+ progress per day
    
    # Stagnation thresholds (number of operations without progress)
    stagnation_warning: int = 3  # Warning after 3 ops
    stagnation_critical: int = 5  # Critical after 5 ops
    
    # Regression thresholds (negative progress)
    regression_tolerance: float = 0.0  # 0% tolerance for regression
    
    def is_progress_minimal(self, progress: float, metric_type: ProgressMetricType) -> bool:
        """Check if progress meets minimal threshold"""
        threshold_map = {
            ProgressMetricType.CODE: self.code_minimal,
            ProgressMetricType.TASK: self.task_minimal,
            ProgressMetricType.SESSION: self.session_minimal,
            ProgressMetricType.PROJECT: self.project_minimal
        }
        threshold = threshold_map.get(metric_type, 0.0)
        return progress >= threshold
    
    def is_progress_expected(self, progress: float, metric_type: ProgressMetricType) -> bool:
        """Check if progress meets expected threshold"""
        threshold_map = {
            ProgressMetricType.CODE: self.code_expected,
            ProgressMetricType.TASK: self.task_expected,
            ProgressMetricType.SESSION: self.session_expected,
            ProgressMetricType.PROJECT: self.project_expected
        }
        threshold = threshold_map.get(metric_type, 0.0)
        return progress >= threshold
    
    def is_progress_optimal(self, progress: float, metric_type: ProgressMetricType) -> bool:
        """Check if progress meets optimal threshold"""
        threshold_map = {
            ProgressMetricType.CODE: self.code_optimal,
            ProgressMetricType.TASK: self.task_optimal,
            ProgressMetricType.SESSION: self.session_optimal,
            ProgressMetricType.PROJECT: self.project_optimal
        }
        threshold = threshold_map.get(metric_type, 0.0)
        return progress >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'code_minimal': self.code_minimal,
            'code_expected': self.code_expected,
            'code_optimal': self.code_optimal,
            'task_minimal': self.task_minimal,
            'task_expected': self.task_expected,
            'task_optimal': self.task_optimal,
            'session_minimal': self.session_minimal,
            'session_expected': self.session_expected,
            'session_optimal': self.session_optimal,
            'project_minimal': self.project_minimal,
            'project_expected': self.project_expected,
            'project_optimal': self.project_optimal,
            'stagnation_warning': self.stagnation_warning,
            'stagnation_critical': self.stagnation_critical,
            'regression_tolerance': self.regression_tolerance
        }


@dataclass
class CustomMetric:
    """
    Custom project-specific metric
    
    Allows projects to define their own metrics beyond the standard
    code, task, session, and project metrics.
    """
    name: str
    description: str
    metric_type: ProgressMetricType
    value: float
    unit: str = ""
    minimal_threshold: Optional[float] = None
    expected_threshold: Optional[float] = None
    optimal_threshold: Optional[float] = None
    
    def is_progress_minimal(self) -> bool:
        """Check if custom metric meets minimal threshold"""
        if self.minimal_threshold is None:
            return True
        return self.value >= self.minimal_threshold
    
    def is_progress_expected(self) -> bool:
        """Check if custom metric meets expected threshold"""
        if self.expected_threshold is None:
            return self.is_progress_minimal()
        return self.value >= self.expected_threshold
    
    def is_progress_optimal(self) -> bool:
        """Check if custom metric meets optimal threshold"""
        if self.optimal_threshold is None:
            return self.is_progress_expected()
        return self.value >= self.optimal_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'name': self.name,
            'description': self.description,
            'metric_type': self.metric_type.value,
            'value': self.value,
            'unit': self.unit,
            'minimal_threshold': self.minimal_threshold,
            'expected_threshold': self.expected_threshold,
            'optimal_threshold': self.optimal_threshold
        }


class ProgressMetrics:
    """
    Main progress metrics container
    
    Aggregates all progress metrics (code, task, session, project)
    and provides methods for validation, comparison, and reporting.
    """
    
    def __init__(self):
        self.code_metrics = CodeProgressMetrics()
        self.task_metrics = TaskProgressMetrics()
        self.session_metrics = SessionProgressMetrics()
        self.project_metrics = ProjectProgressMetrics()
        self.thresholds = ProgressThresholds()
        self.custom_metrics: List[CustomMetric] = []
        self.timestamp = datetime.now()
    
    def get_metric(self, metric_type: ProgressMetricType):
        """Get metrics for specific type"""
        metric_map = {
            ProgressMetricType.CODE: self.code_metrics,
            ProgressMetricType.TASK: self.task_metrics,
            ProgressMetricType.SESSION: self.session_metrics,
            ProgressMetricType.PROJECT: self.project_metrics
        }
        return metric_map.get(metric_type)
    
    def add_custom_metric(self, metric: CustomMetric):
        """Add a custom metric"""
        self.custom_metrics.append(metric)
    
    def validate_progress(self, metric_type: ProgressMetricType, progress: float) -> Dict[str, bool]:
        """
        Validate progress against thresholds
        
        Returns dict with keys: minimal, expected, optimal
        """
        return {
            'minimal': self.thresholds.is_progress_minimal(progress, metric_type),
            'expected': self.thresholds.is_progress_expected(progress, metric_type),
            'optimal': self.thresholds.is_progress_optimal(progress, metric_type)
        }
    
    def check_stagnation(self, ops_without_progress: int) -> str:
        """
        Check if stagnation is occurring
        
        Returns: 'none', 'warning', or 'critical'
        """
        if ops_without_progress >= self.thresholds.stagnation_critical:
            return 'critical'
        elif ops_without_progress >= self.thresholds.stagnation_warning:
            return 'warning'
        else:
            return 'none'
    
    def check_regression(self, current_progress: float, previous_progress: float) -> bool:
        """
        Check if regression has occurred
        
        Returns True if progress has regressed beyond tolerance
        """
        regression = previous_progress - current_progress
        return regression > self.thresholds.regression_tolerance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entire metrics object to dictionary"""
        return {
            'code_metrics': self.code_metrics.to_dict(),
            'task_metrics': self.task_metrics.to_dict(),
            'session_metrics': self.session_metrics.to_dict(),
            'project_metrics': self.project_metrics.to_dict(),
            'thresholds': self.thresholds.to_dict(),
            'custom_metrics': [m.to_dict() for m in self.custom_metrics],
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressMetrics':
        """Create metrics object from dictionary"""
        metrics = cls()
        
        if 'code_metrics' in data:
            cm = data['code_metrics']
            metrics.code_metrics = CodeProgressMetrics(**cm)
        
        if 'task_metrics' in data:
            tm = data['task_metrics']
            metrics.task_metrics = TaskProgressMetrics(**tm)
        
        if 'session_metrics' in data:
            sm = data['session_metrics']
            metrics.session_metrics = SessionProgressMetrics(**sm)
        
        if 'project_metrics' in data:
            pm = data['project_metrics']
            metrics.project_metrics = ProjectProgressMetrics(**pm)
        
        if 'thresholds' in data:
            th = data['thresholds']
            metrics.thresholds = ProgressThresholds(**th)
        
        if 'custom_metrics' in data:
            metrics.custom_metrics = [
                CustomMetric(
                    name=m['name'],
                    description=m['description'],
                    metric_type=ProgressMetricType(m['metric_type']),
                    value=m['value'],
                    unit=m.get('unit', ''),
                    minimal_threshold=m.get('minimal_threshold'),
                    expected_threshold=m.get('expected_threshold'),
                    optimal_threshold=m.get('optimal_threshold')
                )
                for m in data['custom_metrics']
            ]
        
        if 'timestamp' in data:
            metrics.timestamp = datetime.fromisoformat(data['timestamp'])
        
        return metrics


# Utility functions for metric calculations

def calculate_code_progress_percentage(current: CodeProgressMetrics, 
                                       baseline: CodeProgressMetrics) -> float:
    """
    Calculate code progress percentage relative to baseline
    
    Args:
        current: Current code metrics
        baseline: Baseline code metrics to compare against
    
    Returns:
        Progress percentage (0-100)
    """
    # Calculate change in lines
    lines_change = (current.lines_added + current.lines_modified + current.lines_deleted)
    baseline_change = (baseline.lines_added + baseline.lines_modified + baseline.lines_deleted)
    
    if baseline_change == 0:
        return 100.0 if lines_change > 0 else 0.0
    
    progress = (lines_change / baseline_change) * 100
    return min(progress, 100.0)


def calculate_task_progress_percentage(current: TaskProgressMetrics,
                                        baseline: TaskProgressMetrics) -> float:
    """
    Calculate task progress percentage relative to baseline
    
    Args:
        current: Current task metrics
        baseline: Baseline task metrics to compare against
    
    Returns:
        Progress percentage (0-100)
    """
    current_pct = current.completion_percentage()
    baseline_pct = baseline.completion_percentage()
    
    if baseline_pct == 0:
        return current_pct
    
    progress = current_pct - baseline_pct
    return min(progress, 100.0)


def compare_with_historical(metrics: ProgressMetrics, 
                          historical: List[ProgressMetrics]) -> Dict[str, float]:
    """
    Compare current metrics with historical averages
    
    Args:
        metrics: Current metrics
        historical: List of historical metrics
    
    Returns:
        Dictionary comparing current to historical averages
    """
    if not historical:
        return {}
    
    comparison = {}
    
    # Calculate historical averages
    avg_code_lines = sum(m.code_metrics.total_lines_changed() for m in historical) / len(historical)
    avg_task_completion = sum(m.task_metrics.completion_percentage() for m in historical) / len(historical)
    avg_session_tasks = sum(m.session_metrics.tasks_completed for m in historical) / len(historical)
    avg_project_completion = sum(m.project_metrics.feature_completion_percentage() for m in historical) / len(historical)
    
    # Calculate current values
    current_code_lines = metrics.code_metrics.total_lines_changed()
    current_task_completion = metrics.task_metrics.completion_percentage()
    current_session_tasks = metrics.session_metrics.tasks_completed
    current_project_completion = metrics.project_metrics.feature_completion_percentage()
    
    # Calculate ratios (current / average)
    comparison['code_ratio'] = current_code_lines / avg_code_lines if avg_code_lines > 0 else 1.0
    comparison['task_ratio'] = current_task_completion / avg_task_completion if avg_task_completion > 0 else 1.0
    comparison['session_ratio'] = current_session_tasks / avg_session_tasks if avg_session_tasks > 0 else 1.0
    comparison['project_ratio'] = current_project_completion / avg_project_completion if avg_project_completion > 0 else 1.0
    
    return comparison


class ProgressTracker:
    """
    Progress tracker for continuous monitoring
    
    Tracks progress metrics in real-time, compares against expected rates,
    detects stagnation and regression, generates alerts, and produces reports.
    """
    
    def __init__(self, task_id: Optional[str] = None):
        """
        Initialize progress tracker
        
        Args:
            task_id: Optional task identifier for tracking
        """
        self.task_id = task_id
        self.metrics = ProgressMetrics()
        self.baseline_metrics = None
        self.historical_metrics: List[ProgressMetrics] = []
        self.ops_without_progress = 0
        self.last_progress = 0.0
        self.is_tracking = False
        self.start_time = None
        self.alerts: List[Dict[str, Any]] = []
        
    def start_tracking(self, task_id: Optional[str] = None):
        """
        Start tracking progress for a task
        
        Args:
            task_id: Optional task identifier (overrides constructor)
        """
        if task_id:
            self.task_id = task_id
        
        self.is_tracking = True
        self.start_time = datetime.now()
        self.metrics = ProgressMetrics()
        self.baseline_metrics = None
        self.ops_without_progress = 0
        self.last_progress = 0.0
        self.alerts = []
        
    def stop_tracking(self):
        """Stop tracking progress"""
        self.is_tracking = False
        
    def update_progress(self, task_id: Optional[str] = None,
                       code_metrics: Optional[CodeProgressMetrics] = None,
                       task_metrics: Optional[TaskProgressMetrics] = None,
                       session_metrics: Optional[SessionProgressMetrics] = None,
                       project_metrics: Optional[ProjectProgressMetrics] = None,
                       custom_metrics: Optional[List[CustomMetric]] = None):
        """
        Update progress metrics
        
        Args:
            task_id: Optional task identifier
            code_metrics: Updated code metrics
            task_metrics: Updated task metrics
            session_metrics: Updated session metrics
            project_metrics: Updated project metrics
            custom_metrics: Updated custom metrics
        """
        if not self.is_tracking:
            return
            
        if task_id:
            self.task_id = task_id
            
        # Update baseline on first call
        if self.baseline_metrics is None:
            self.baseline_metrics = self.metrics
            
        # Save historical snapshot before update
        self.historical_metrics.append(self.metrics)
        
        # Update metrics
        if code_metrics:
            self.metrics.code_metrics = code_metrics
        if task_metrics:
            self.metrics.task_metrics = task_metrics
        if session_metrics:
            self.metrics.session_metrics = session_metrics
        if project_metrics:
            self.metrics.project_metrics = project_metrics
        if custom_metrics:
            self.metrics.custom_metrics = custom_metrics
            
        self.metrics.timestamp = datetime.now()
        
    def check_progress(self, task_id: Optional[str] = None,
                      metric_type: Optional[ProgressMetricType] = None) -> Dict[str, Any]:
        """
        Check if progress is adequate
        
        Args:
            task_id: Optional task identifier
            metric_type: Optional specific metric type to check (checks all if None)
        
        Returns:
            Dictionary with validation results and status
        """
        if not self.is_tracking:
            return {
                'status': 'not_tracking',
                'is_adequate': False,
                'details': {}
            }
            
        # If no baseline yet, use current metrics as baseline
        if self.baseline_metrics is None:
            self.baseline_metrics = self.metrics
            
        result = {
            'task_id': task_id or self.task_id,
            'timestamp': datetime.now().isoformat(),
            'is_adequate': True,
            'status': 'adequate',
            'details': {}
        }
        
        # Check stagnation
        stagnation_status = self.metrics.check_stagnation(self.ops_without_progress)
        if stagnation_status != 'none':
            result['stagnation'] = stagnation_status
            result['status'] = stagnation_status
            if stagnation_status == 'critical':
                result['is_adequate'] = False
                
        # Check regression
        current_progress = self._calculate_overall_progress()
        if self.metrics.check_regression(current_progress, self.last_progress):
            result['regression'] = True
            result['status'] = 'regression'
            result['is_adequate'] = False
            self._generate_alert('regression', 
                               f"Regression detected: {current_progress:.2f}% -> {self.last_progress:.2f}%")
            
        self.last_progress = current_progress
        
        # Check each metric type
        metric_types = [metric_type] if metric_type else [
            ProgressMetricType.CODE,
            ProgressMetricType.TASK,
            ProgressMetricType.SESSION,
            ProgressMetricType.PROJECT
        ]
        
        for mtype in metric_types:
            progress = self._calculate_progress_for_type(mtype)
            validation = self.metrics.validate_progress(mtype, progress)
            
            result['details'][mtype.value] = {
                'progress': progress,
                'validation': validation
            }
            
            # Check if meets minimal threshold
            if not validation['minimal']:
                result['is_adequate'] = False
                if result['status'] == 'adequate':
                    result['status'] = 'below_minimal'
                self._generate_alert(mtype.value,
                                   f"Progress {progress:.2f}% below minimal threshold for {mtype.value}")
                
        return result
        
    def _calculate_overall_progress(self) -> float:
        """Calculate overall progress across all metric types"""
        if self.baseline_metrics is None:
            return 0.0
            
        total = 0.0
        count = 0
        
        for mtype in [ProgressMetricType.CODE, ProgressMetricType.TASK, 
                     ProgressMetricType.SESSION, ProgressMetricType.PROJECT]:
            progress = self._calculate_progress_for_type(mtype)
            total += progress
            count += 1
            
        return total / count if count > 0 else 0.0
        
    def _calculate_progress_for_type(self, metric_type: ProgressMetricType) -> float:
        """Calculate progress for specific metric type"""
        if self.baseline_metrics is None:
            return 0.0
            
        current = self.metrics.get_metric(metric_type)
        baseline = self.baseline_metrics.get_metric(metric_type)
        
        if metric_type == ProgressMetricType.CODE:
            return calculate_code_progress_percentage(
                self.metrics.code_metrics, self.baseline_metrics.code_metrics
            )
        elif metric_type == ProgressMetricType.TASK:
            return calculate_task_progress_percentage(
                self.metrics.task_metrics, self.baseline_metrics.task_metrics
            )
        elif metric_type == ProgressMetricType.SESSION:
            # Session progress: tasks completed / tasks attempted
            total = current.total_tasks()
            if total == 0:
                return 0.0
            return (current.tasks_completed / total) * 100.0
        elif metric_type == ProgressMetricType.PROJECT:
            return current.feature_completion_percentage()
        else:
            return 0.0
            
    def detect_stagnation(self, threshold: Optional[int] = None) -> Dict[str, Any]:
        """
        Detect if progress has stagnated
        
        Args:
            threshold: Optional custom stagnation threshold (uses default if None)
        
        Returns:
            Dictionary with stagnation status and details
        """
        stagnation_threshold = threshold or self.metrics.thresholds.stagnation_warning
        
        result = {
            'ops_without_progress': self.ops_without_progress,
            'status': 'none',
            'severity': 'none'
        }
        
        if self.ops_without_progress >= self.metrics.thresholds.stagnation_critical:
            result['status'] = 'critical'
            result['severity'] = 'critical'
            result['message'] = f"Critical stagnation: {self.ops_without_progress} operations without progress"
            self._generate_alert('stagnation_critical', result['message'])
            
        elif self.ops_without_progress >= stagnation_threshold:
            result['status'] = 'warning'
            result['severity'] = 'warning'
            result['message'] = f"Stagnation warning: {self.ops_without_progress} operations without progress"
            self._generate_alert('stagnation_warning', result['message'])
            
        return result
        
    def detect_regression(self, metric_type: Optional[ProgressMetricType] = None) -> Dict[str, Any]:
        """
        Detect if progress has regressed
        
        Args:
            metric_type: Optional specific metric type to check (checks all if None)
        
        Returns:
            Dictionary with regression status and details
        """
        result = {
            'has_regression': False,
            'regressions': []
        }
        
        # Need at least 2 historical metrics to detect regression
        if len(self.historical_metrics) < 2 or self.baseline_metrics is None:
            return result
        
        metric_types = [metric_type] if metric_type else [
            ProgressMetricType.CODE,
            ProgressMetricType.TASK,
            ProgressMetricType.SESSION,
            ProgressMetricType.PROJECT
        ]
        
        # Get previous metrics (second to last in history)
        previous_metrics = self.historical_metrics[-2]
        
        for mtype in metric_types:
            # Calculate progress for current state
            current_progress = self._calculate_progress_for_type(mtype)
            
            # Calculate progress for previous state using temporary tracker
            temp_tracker = ProgressTracker()
            temp_tracker.baseline_metrics = self.baseline_metrics
            temp_tracker.metrics = previous_metrics
            previous_progress = temp_tracker._calculate_progress_for_type(mtype)
            
            # Check if regression occurred
            if current_progress < previous_progress - self.metrics.thresholds.regression_tolerance:
                regression_details = {
                    'metric_type': mtype.value,
                    'previous': previous_progress,
                    'current': current_progress,
                    'change': current_progress - previous_progress
                }
                result['regressions'].append(regression_details)
                result['has_regression'] = True
                
                self._generate_alert(
                    f'regression_{mtype.value}',
                    f"Regression in {mtype.value}: {previous_progress:.2f}% -> {current_progress:.2f}%"
                )
                        
        return result
        
    def _generate_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """
        Generate and store an alert
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
        """
        alert = {
            'timestamp': datetime.now().isoformat(),
            'task_id': self.task_id,
            'type': alert_type,
            'severity': severity,
            'message': message
        }
        self.alerts.append(alert)
        
    def get_alerts(self, severity: Optional[str] = None, 
                   alert_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get alerts with optional filtering
        
        Args:
            severity: Optional severity filter
            alert_type: Optional alert type filter
        
        Returns:
            List of alerts matching filters
        """
        filtered = self.alerts
        
        if severity:
            filtered = [a for a in filtered if a['severity'] == severity]
            
        if alert_type:
            filtered = [a for a in filtered if a['type'] == alert_type]
            
        return filtered
        
    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts = []
        
    def get_report(self, task_id: Optional[str] = None,
                   include_historical: bool = True,
                   include_alerts: bool = True) -> Dict[str, Any]:
        """
        Generate progress report
        
        Args:
            task_id: Optional task identifier
            include_historical: Include historical metrics
            include_alerts: Include alerts
        
        Returns:
            Comprehensive progress report
        """
        report = {
            'task_id': task_id or self.task_id,
            'is_tracking': self.is_tracking,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'current_time': datetime.now().isoformat(),
            'duration_seconds': (
                (datetime.now() - self.start_time).total_seconds() 
                if self.start_time else 0
            ),
            'metrics': self.metrics.to_dict(),
            'progress_summary': {}
        }
        
        # Calculate progress for each metric type
        for mtype in [ProgressMetricType.CODE, ProgressMetricType.TASK,
                     ProgressMetricType.SESSION, ProgressMetricType.PROJECT]:
            progress = self._calculate_progress_for_type(mtype)
            validation = self.metrics.validate_progress(mtype, progress)
            
            report['progress_summary'][mtype.value] = {
                'progress': progress,
                'validation': validation
            }
            
        # Add stagnation detection
        stagnation = self.detect_stagnation()
        report['stagnation'] = stagnation
        
        # Add regression detection
        regression = self.detect_regression()
        report['regression'] = regression
        
        # Add historical metrics if requested
        if include_historical:
            report['historical_metrics'] = [
                m.to_dict() for m in self.historical_metrics[-10:]  # Last 10 entries
            ]
            
        # Add alerts if requested
        if include_alerts:
            report['alerts'] = self.alerts
            
        # Add historical comparison
        if self.historical_metrics:
            report['historical_comparison'] = compare_with_historical(
                self.metrics, self.historical_metrics
            )
            
        return report
        
    def get_summary(self) -> Dict[str, Any]:
        """
        Get brief summary of current progress
        
        Returns:
            Brief summary dictionary
        """
        overall_progress = self._calculate_overall_progress()
        
        summary = {
            'task_id': self.task_id,
            'is_tracking': self.is_tracking,
            'overall_progress': overall_progress,
            'ops_without_progress': self.ops_without_progress,
            'total_alerts': len(self.alerts),
            'critical_alerts': len([a for a in self.alerts if a['severity'] == 'critical']),
            'status': 'adequate'
        }
        
        # Determine overall status
        stagnation = self.detect_stagnation()
        if stagnation['status'] != 'none':
            summary['status'] = stagnation['status']
            
        regression = self.detect_regression()
        if regression['has_regression']:
            summary['status'] = 'regression'
            
        if overall_progress < 10:
            summary['status'] = 'below_minimal'
            
        return summary
        
    def increment_ops_without_progress(self):
        """Increment counter for operations without progress"""
        self.ops_without_progress += 1
        
    def reset_ops_without_progress(self):
        """Reset counter for operations without progress"""
        self.ops_without_progress = 0
        
    def export_to_json(self, filepath: str):
        """
        Export progress data to JSON file
        
        Args:
            filepath: Path to JSON file
        """
        report = self.get_report()
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
    def load_from_json(self, filepath: str):
        """
        Load progress data from JSON file
        
        Args:
            filepath: Path to JSON file
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        self.task_id = data.get('task_id')
        self.is_tracking = data.get('is_tracking', False)
        
        if data.get('start_time'):
            self.start_time = datetime.fromisoformat(data['start_time'])
            
        self.metrics = ProgressMetrics.from_dict(data['metrics'])
        
        # Load historical metrics
        if 'historical_metrics' in data:
            self.historical_metrics = [
                ProgressMetrics.from_dict(m) for m in data['historical_metrics']
            ]
            
        # Load alerts
        if 'alerts' in data:
            self.alerts = data['alerts']
            
        # Set baseline if historical metrics exist
        if self.historical_metrics:
            self.baseline_metrics = self.historical_metrics[0]
            
        # Recalculate progress counters
        if 'stagnation' in data:
            self.ops_without_progress = data['stagnation'].get('ops_without_progress', 0)
            
        self.last_progress = self._calculate_overall_progress()


# Global instance for singleton pattern
_progress_tracker_instance = None


def get_progress_tracker(
    telemetry_manager=None,
    context_hierarchy_manager=None,
    minimal_threshold: float = 0.1,
    expected_threshold: float = 0.3
) -> ProgressTracker:
    """
    Get or create singleton ProgressTracker instance
    
    Args:
        telemetry_manager: Manager for tracking operations
        context_hierarchy_manager: Manager for accessing context
        minimal_threshold: Minimum progress threshold (0.0-1.0)
        expected_threshold: Expected progress threshold (0.0-1.0)
        
    Returns:
        ProgressTracker instance
    """
    global _progress_tracker_instance
    
    if _progress_tracker_instance is None:
        _progress_tracker_instance = ProgressTracker(
            telemetry_manager=telemetry_manager,
            context_hierarchy_manager=context_hierarchy_manager,
            minimal_threshold=minimal_threshold,
            expected_threshold=expected_threshold
        )
        logger.info("Created singleton ProgressTracker instance")
    
    return _progress_tracker_instance


def reset_progress_tracker():
    """
    Reset singleton ProgressTracker instance
    Useful for testing or reinitialization
    """
    global _progress_tracker_instance
    _progress_tracker_instance = None
    logger.info("Reset singleton ProgressTracker instance")
