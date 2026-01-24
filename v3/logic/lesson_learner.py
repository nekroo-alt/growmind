"""
Lesson Learner - Systematic Learning from Failures

This module implements systematic learning from failures to:
- Record every failure with full context
- Analyze root cause of each failure
- Identify patterns in failures
- Generate lessons learned
- Update decision heuristics to avoid repeated mistakes
- Track mistake reduction over time
"""

import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import uuid
import threading

# Import decision history for failure analysis
try:
    from v3.data.decision_history import DecisionHistory
except ImportError:
    DecisionHistory = None


@dataclass
class LessonLearned:
    """Represents a lesson learned from a failure"""
    lesson_id: str
    failure_type: str
    root_cause: str
    context: Dict[str, Any]
    prevention: str
    frequency: int
    effectiveness: float  # How effective this lesson has been
    created_at: str
    updated_at: str
    sample_failures: List[str] = field(default_factory=list)


@dataclass
class FailureAnalysis:
    """Represents analysis of a failure"""
    failure_id: str
    decision_id: str
    failure_type: str
    root_cause: str
    context: Dict[str, Any]
    contributing_factors: List[str]
    suggested_prevention: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    analyzed_at: str


class LessonLearner:
    """
    Lesson Learner for Systematic Learning from Failures
    
    Records failures, analyzes root causes, identifies patterns,
    generates lessons learned, and updates heuristics to avoid
    repeated mistakes.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize lesson learner
        
        Args:
            db_path: Path to SQLite database for lesson persistence
        """
        self.db_path = db_path or 'data/lessons_learned.db'
        self.decision_history = None
        self.lock = threading.RLock()
        
        # Configuration
        self.min_pattern_frequency = 2  # Minimum frequency to identify a pattern
        self.effectiveness_threshold = 0.7  # Effectiveness threshold for effective lessons
        self.severity_weights = {
            'low': 0.25,
            'medium': 0.5,
            'high': 0.75,
            'critical': 1.0
        }
        
        # Initialize database
        self._init_db()
        
        # Try to initialize decision history
        if DecisionHistory:
            try:
                self.decision_history = DecisionHistory()
            except Exception as e:
                print(f"Warning: Could not initialize decision history: {e}")
    
    def _init_db(self):
        """Initialize SQLite database for lesson storage"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Lessons learned table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lessons_learned (
                    lesson_id TEXT PRIMARY KEY,
                    failure_type TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    context TEXT NOT NULL,
                    prevention TEXT NOT NULL,
                    frequency INTEGER NOT NULL,
                    effectiveness REAL NOT NULL,
                    sample_failures TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # Failures table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS failures (
                    failure_id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    context TEXT NOT NULL,
                    contributing_factors TEXT,
                    suggested_prevention TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    lesson_id TEXT
                )
            ''')
            
            # Mistake tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mistake_tracking (
                    timestamp TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    lesson_applied INTEGER NOT NULL,
                    mistake_avoided INTEGER NOT NULL
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_failure_type ON lessons_learned(failure_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_effectiveness ON lessons_learned(effectiveness)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_frequency ON lessons_learned(frequency)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_decision_id ON failures(decision_id)')
            
            conn.commit()
    
    def record_failure(self, decision_id: str, context: Dict[str, Any], 
                      error_message: str = None) -> FailureAnalysis:
        """
        Record a failure with full context
        
        Args:
            decision_id: ID of the decision that failed
            context: Context dictionary at time of failure
            error_message: Error message from the failure
            
        Returns:
            FailureAnalysis object with analysis results
        """
        with self.lock:
            # Analyze the failure
            analysis = self._analyze_failure(decision_id, context, error_message)
            
            # Save failure to database
            self._save_failure(analysis)
            
            # Check if this matches existing lessons
            self._check_and_update_lessons(analysis)
            
            # Identify if this is part of a failure pattern
            self._identify_failure_patterns()
            
            return analysis
    
    def _analyze_failure(self, decision_id: str, context: Dict[str, Any],
                        error_message: str = None) -> FailureAnalysis:
        """
        Analyze a failure to determine root cause and contributing factors
        
        Args:
            decision_id: ID of the decision that failed
            context: Context dictionary at time of failure
            error_message: Error message from the failure
            
        Returns:
            FailureAnalysis with analysis results
        """
        # Determine failure type
        failure_type = self._classify_failure_type(context, error_message)
        
        # Analyze root cause
        root_cause = self._analyze_root_cause(context, failure_type)
        
        # Identify contributing factors
        contributing_factors = self._identify_contributing_factors(context, failure_type)
        
        # Generate prevention strategy
        prevention = self._generate_prevention(failure_type, root_cause, contributing_factors)
        
        # Determine severity
        severity = self._determine_severity(context, failure_type)
        
        analysis = FailureAnalysis(
            failure_id=str(uuid.uuid4()),
            decision_id=decision_id,
            failure_type=failure_type,
            root_cause=root_cause,
            context=context,
            contributing_factors=contributing_factors,
            suggested_prevention=prevention,
            severity=severity,
            analyzed_at=datetime.utcnow().isoformat()
        )
        
        return analysis
    
    def _classify_failure_type(self, context: Dict[str, Any], 
                               error_message: str = None) -> str:
        """
        Classify the type of failure
        
        Args:
            context: Context dictionary
            error_message: Error message from failure
            
        Returns:
            Failure type string
        """
        # Check error message first
        if error_message:
            if 'timeout' in error_message.lower():
                return 'timeout_failure'
            elif 'connection' in error_message.lower():
                return 'connection_failure'
            elif 'permission' in error_message.lower() or 'access' in error_message.lower():
                return 'permission_failure'
            elif 'memory' in error_message.lower():
                return 'memory_failure'
            elif 'invalid' in error_message.lower() or 'validation' in error_message.lower():
                return 'validation_failure'
        
        # Check context
        situation = context.get('situation_type', '')
        if 'error' in situation.lower():
            if 'loop' in context.get('detected_traps', []):
                return 'loop_failure'
            elif 'dead_end' in context.get('detected_traps', []):
                return 'dead_end_failure'
        
        task_type = context.get('task_type', '')
        if 'planning' in task_type:
            return 'planning_failure'
        elif 'implementation' in task_type:
            return 'implementation_failure'
        elif 'validation' in task_type:
            return 'validation_failure'
        
        # Default
        return 'unknown_failure'
    
    def _analyze_root_cause(self, context: Dict[str, Any], 
                            failure_type: str) -> str:
        """
        Analyze the root cause of a failure
        
        Args:
            context: Context dictionary
            failure_type: Type of failure
            
        Returns:
            Root cause description
        """
        root_causes = {
            'timeout_failure': 'Insufficient timeout configuration or slow operation',
            'connection_failure': 'Network connectivity issues or service unavailability',
            'permission_failure': 'Insufficient permissions or incorrect access configuration',
            'memory_failure': 'Memory exhaustion or memory leak',
            'validation_failure': 'Invalid input or failed validation checks',
            'loop_failure': 'Infinite loop detected in execution logic',
            'dead_end_failure': 'Execution reached a dead end with no viable path forward',
            'planning_failure': 'Task planning failed due to incomplete or incorrect requirements',
            'implementation_failure': 'Implementation failed due to logic errors or incorrect approach',
            'validation_failure': 'Validation failed due to incorrect acceptance criteria or test issues',
            'unknown_failure': 'Unknown cause - requires further investigation'
        }
        
        return root_causes.get(failure_type, 'Unknown cause')
    
    def _identify_contributing_factors(self, context: Dict[str, Any],
                                     failure_type: str) -> List[str]:
        """
        Identify contributing factors to a failure
        
        Args:
            context: Context dictionary
            failure_type: Type of failure
            
        Returns:
            List of contributing factors
        """
        factors = []
        
        # Check for insufficient context
        if context.get('context_level') == 'L0':
            factors.append('Insufficient context used for decision')
        
        # Check for strategy issues
        strategy = context.get('strategy', '')
        if strategy == 'aggressive':
            factors.append('Aggressive strategy may have taken excessive risks')
        
        # Check for resource constraints
        resources = context.get('resources', {})
        if resources.get('tokens_used', 0) > resources.get('token_budget', 0) * 0.9:
            factors.append('Resource constraints may have impacted decision quality')
        
        # Check for error history
        error_count = context.get('recent_error_count', 0)
        if error_count > 3:
            factors.append(f'High error rate ({error_count} recent errors) indicates systemic issues')
        
        # Check for trap detection
        detected_traps = context.get('detected_traps', [])
        if detected_traps:
            factors.append(f'Detected traps: {", ".join(detected_traps)}')
        
        # Check for task complexity
        task_type = context.get('task_type', '')
        if 'complex' in task_type.lower():
            factors.append('High task complexity may have contributed to failure')
        
        return factors if factors else ['No specific contributing factors identified']
    
    def _generate_prevention(self, failure_type: str, root_cause: str,
                           contributing_factors: List[str]) -> str:
        """
        Generate prevention strategy for the failure
        
        Args:
            failure_type: Type of failure
            root_cause: Root cause description
            contributing_factors: List of contributing factors
            
        Returns:
            Prevention strategy description
        """
        preventions = {
            'timeout_failure': 'Increase timeout values and implement retry logic with exponential backoff',
            'connection_failure': 'Implement circuit breaker pattern, connection pooling, and retry logic',
            'permission_failure': 'Verify and configure appropriate permissions before operation',
            'memory_failure': 'Optimize memory usage, implement pagination for large datasets, add memory monitoring',
            'validation_failure': 'Implement comprehensive input validation and pre-flight checks',
            'loop_failure': 'Add loop detection and automatic loop breaking mechanisms',
            'dead_end_failure': 'Implement progress tracking and early detection of non-productive paths',
            'planning_failure': 'Gather complete requirements, validate task complexity, use hierarchical planning',
            'implementation_failure': 'Use TDD, add comprehensive tests, implement code review process',
            'validation_failure': 'Review and strengthen acceptance criteria, improve test coverage',
            'unknown_failure': 'Implement comprehensive logging and monitoring to identify patterns'
        }
        
        base_prevention = preventions.get(failure_type, 'Implement monitoring and logging')
        
        # Add factor-specific prevention
        if 'Insufficient context' in ' '.join(contributing_factors):
            base_prevention += '; Use higher context level (L1/L2) for complex decisions'
        
        if 'Aggressive strategy' in ' '.join(contributing_factors):
            base_prevention += '; Use more conservative strategies for complex or uncertain situations'
        
        return base_prevention
    
    def _determine_severity(self, context: Dict[str, Any], 
                           failure_type: str) -> str:
        """
        Determine the severity of a failure
        
        Args:
            context: Context dictionary
            failure_type: Type of failure
            
        Returns:
            Severity string ('low', 'medium', 'high', 'critical')
        """
        # Critical failures
        if failure_type in ['permission_failure', 'memory_failure']:
            return 'critical'
        
        # High severity failures
        if failure_type in ['timeout_failure', 'connection_failure']:
            return 'high'
        
        # Medium severity failures
        if failure_type in ['loop_failure', 'dead_end_failure', 'implementation_failure']:
            return 'medium'
        
        # Check error count for severity adjustment
        error_count = context.get('recent_error_count', 0)
        if error_count > 5:
            return 'critical'
        elif error_count > 3:
            return 'high'
        
        # Default
        return 'low'
    
    def _save_failure(self, analysis: FailureAnalysis):
        """
        Save failure analysis to database
        
        Args:
            analysis: FailureAnalysis object
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO failures (
                    failure_id, decision_id, failure_type, root_cause,
                    context, contributing_factors, suggested_prevention,
                    severity, analyzed_at, lesson_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.failure_id,
                analysis.decision_id,
                analysis.failure_type,
                analysis.root_cause,
                json.dumps(analysis.context),
                json.dumps(analysis.contributing_factors),
                analysis.suggested_prevention,
                analysis.severity,
                analysis.analyzed_at,
                None  # lesson_id will be set later
            ))
            
            conn.commit()
    
    def _check_and_update_lessons(self, analysis: FailureAnalysis):
        """
        Check if failure matches existing lessons and update them
        
        Args:
            analysis: FailureAnalysis object
        """
        # Find similar lessons
        similar_lessons = self._find_similar_lessons(analysis)
        
        if similar_lessons:
            # Update existing lesson
            lesson_id = similar_lessons[0]['lesson_id']
            self._update_lesson(lesson_id, analysis)
        else:
            # Create new lesson
            self._create_lesson_from_failure(analysis)
    
    def _find_similar_lessons(self, analysis: FailureAnalysis) -> List[Dict[str, Any]]:
        """
        Find lessons similar to this failure
        
        Args:
            analysis: FailureAnalysis object
            
        Returns:
            List of similar lesson dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Find lessons with same failure type and similar root cause
            cursor.execute('''
                SELECT lesson_id, failure_type, root_cause, prevention, frequency
                FROM lessons_learned
                WHERE failure_type = ?
                ORDER BY effectiveness DESC, frequency DESC
                LIMIT 5
            ''', (analysis.failure_type,))
            
            lessons = []
            for row in cursor.fetchall():
                lesson = {
                    'lesson_id': row[0],
                    'failure_type': row[1],
                    'root_cause': row[2],
                    'prevention': row[3],
                    'frequency': row[4]
                }
                lessons.append(lesson)
            
            return lessons
    
    def _update_lesson(self, lesson_id: str, analysis: FailureAnalysis):
        """
        Update an existing lesson with new failure
        
        Args:
            lesson_id: ID of lesson to update
            analysis: FailureAnalysis object
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Increment frequency
            cursor.execute('''
                UPDATE lessons_learned
                SET frequency = frequency + 1,
                    updated_at = ?
                WHERE lesson_id = ?
            ''', (datetime.utcnow().isoformat(), lesson_id))
            
            # Update failure with lesson_id
            cursor.execute('''
                UPDATE failures
                SET lesson_id = ?
                WHERE failure_id = ?
            ''', (lesson_id, analysis.failure_id))
            
            conn.commit()
    
    def _create_lesson_from_failure(self, analysis: FailureAnalysis):
        """
        Create a new lesson from a failure
        
        Args:
            analysis: FailureAnalysis object
        """
        lesson = LessonLearned(
            lesson_id=str(uuid.uuid4()),
            failure_type=analysis.failure_type,
            root_cause=analysis.root_cause,
            context=analysis.context,
            prevention=analysis.suggested_prevention,
            frequency=1,
            effectiveness=0.5,  # Start with moderate effectiveness
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            sample_failures=[analysis.failure_id]
        )
        
        self._save_lesson(lesson)
        
        # Update failure with lesson_id
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE failures
                SET lesson_id = ?
                WHERE failure_id = ?
            ''', (lesson.lesson_id, analysis.failure_id))
            conn.commit()
    
    def _save_lesson(self, lesson: LessonLearned):
        """
        Save lesson to database
        
        Args:
            lesson: LessonLearned object
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO lessons_learned (
                    lesson_id, failure_type, root_cause, context, prevention,
                    frequency, effectiveness, sample_failures, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                lesson.lesson_id,
                lesson.failure_type,
                lesson.root_cause,
                json.dumps(lesson.context),
                lesson.prevention,
                lesson.frequency,
                lesson.effectiveness,
                json.dumps(lesson.sample_failures),
                lesson.created_at,
                lesson.updated_at
            ))
            
            conn.commit()
    
    def _identify_failure_patterns(self):
        """
        Identify patterns in failures
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get recent failures
            cursor.execute('''
                SELECT failure_type, root_cause, COUNT(*) as count
                FROM failures
                WHERE analyzed_at > datetime('now', '-7 days')
                GROUP BY failure_type, root_cause
                HAVING count >= ?
                ORDER BY count DESC
            ''', (self.min_pattern_frequency,))
            
            patterns = cursor.fetchall()
            
            for failure_type, root_cause, count in patterns:
                print(f"Failure pattern identified: {failure_type} - {root_cause} ({count} occurrences)")
    
    def get_lessons_for_context(self, context: Dict[str, Any]) -> List[LessonLearned]:
        """
        Get relevant lessons for a given context
        
        Args:
            context: Current context dictionary
            
        Returns:
            List of relevant LessonLearned objects
        """
        with self.lock:
            # Determine failure type from context
            failure_type = self._classify_failure_type(context)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get lessons for this failure type
                cursor.execute('''
                    SELECT lesson_id, failure_type, root_cause, context, prevention,
                           frequency, effectiveness, sample_failures, created_at, updated_at
                    FROM lessons_learned
                    WHERE failure_type = ? AND effectiveness >= ?
                    ORDER BY effectiveness DESC, frequency DESC
                    LIMIT 10
                ''', (failure_type, self.effectiveness_threshold))
                
                lessons = []
                for row in cursor.fetchall():
                    lesson = LessonLearned(
                        lesson_id=row[0],
                        failure_type=row[1],
                        root_cause=row[2],
                        context=json.loads(row[3]),
                        prevention=row[4],
                        frequency=row[5],
                        effectiveness=row[6],
                        sample_failures=json.loads(row[7]) if row[7] else [],
                        created_at=row[8],
                        updated_at=row[9]
                    )
                    lessons.append(lesson)
                
                return lessons
    
    def apply_lesson(self, lesson_id: str, success: bool):
        """
        Record whether a lesson was applied and if it was successful
        
        Args:
            lesson_id: ID of the lesson
            success: Whether the lesson application was successful
        """
        with self.lock:
            # Get lesson to determine failure type
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT failure_type FROM lessons_learned WHERE lesson_id = ?', (lesson_id,))
                result = cursor.fetchone()
                if not result:
                    return
                failure_type = result[0]
            
            # Update lesson effectiveness
            new_effectiveness = self._calculate_effectiveness(lesson_id, success)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE lessons_learned
                    SET effectiveness = ?, updated_at = ?
                    WHERE lesson_id = ?
                ''', (new_effectiveness, datetime.utcnow().isoformat(), lesson_id))
                conn.commit()
            
            # Record in mistake tracking
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO mistake_tracking (timestamp, failure_type, lesson_applied, mistake_avoided)
                    VALUES (?, ?, ?, ?)
                ''', (datetime.utcnow().isoformat(), failure_type, 1, 1 if success else 0))
                conn.commit()
    
    def _calculate_effectiveness(self, lesson_id: str, success: bool) -> float:
        """
        Calculate new effectiveness score for a lesson
        
        Args:
            lesson_id: ID of the lesson
            success: Whether the lesson application was successful
            
        Returns:
            New effectiveness score (0.0 to 1.0)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current effectiveness and frequency
            cursor.execute('''
                SELECT effectiveness, frequency FROM lessons_learned WHERE lesson_id = ?
            ''', (lesson_id,))
            result = cursor.fetchone()
            if not result:
                return 0.5
            
            current_effectiveness, frequency = result
            
            # Weighted update: recent applications have more weight
            weight = min(1.0, 5 / frequency)  # More weight for early applications
            new_effectiveness = (current_effectiveness * (1 - weight) + 
                              (1.0 if success else 0.0) * weight)
            
            return new_effectiveness
    
    def get_mistake_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about mistakes and lessons
        
        Returns:
            Dictionary with mistake statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total failures
            cursor.execute('SELECT COUNT(*) FROM failures')
            total_failures = cursor.fetchone()[0]
            
            # Failures by type
            cursor.execute('''
                SELECT failure_type, COUNT(*) as count
                FROM failures
                GROUP BY failure_type
                ORDER BY count DESC
            ''')
            failures_by_type = dict(cursor.fetchall())
            
            # Total lessons
            cursor.execute('SELECT COUNT(*) FROM lessons_learned')
            total_lessons = cursor.fetchone()[0]
            
            # Average effectiveness
            cursor.execute('SELECT AVG(effectiveness) FROM lessons_learned')
            avg_effectiveness = cursor.fetchone()[0] or 0.0
            
            # Mistake tracking
            cursor.execute('''
                SELECT 
                    SUM(lesson_applied) as total_applied,
                    SUM(mistake_avoided) as total_avoided,
                    COUNT(*) as total_attempts
                FROM mistake_tracking
            ''')
            result = cursor.fetchone()
            if result:
                total_applied, total_avoided, total_attempts = result
                avoidance_rate = total_avoided / total_applied if total_applied > 0 else 0.0
            else:
                total_applied = 0
                total_avoided = 0
                total_attempts = 0
                avoidance_rate = 0.0
            
            return {
                'total_failures': total_failures,
                'failures_by_type': failures_by_type,
                'total_lessons': total_lessons,
                'average_effectiveness': avg_effectiveness,
                'total_lesson_applications': total_applied,
                'mistakes_avoided': total_avoided,
                'mistake_avoidance_rate': avoidance_rate,
                'total_attempts': total_attempts
            }
    
    def get_lessons_by_effectiveness(self, min_effectiveness: float = 0.7, 
                                    limit: int = 20) -> List[LessonLearned]:
        """
        Get lessons sorted by effectiveness
        
        Args:
            min_effectiveness: Minimum effectiveness threshold
            limit: Maximum number of lessons to return
            
        Returns:
            List of LessonLearned objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT lesson_id, failure_type, root_cause, context, prevention,
                       frequency, effectiveness, sample_failures, created_at, updated_at
                FROM lessons_learned
                WHERE effectiveness >= ?
                ORDER BY effectiveness DESC, frequency DESC
                LIMIT ?
            ''', (min_effectiveness, limit))
            
            lessons = []
            for row in cursor.fetchall():
                lesson = LessonLearned(
                    lesson_id=row[0],
                    failure_type=row[1],
                    root_cause=row[2],
                    context=json.loads(row[3]),
                    prevention=row[4],
                    frequency=row[5],
                    effectiveness=row[6],
                    sample_failures=json.loads(row[7]) if row[7] else [],
                    created_at=row[8],
                    updated_at=row[9]
                )
                lessons.append(lesson)
            
            return lessons
    
    def get_recent_failures(self, limit: int = 20) -> List[FailureAnalysis]:
        """
        Get recent failures
        
        Args:
            limit: Maximum number of failures to return
            
        Returns:
            List of FailureAnalysis objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT failure_id, decision_id, failure_type, root_cause,
                       context, contributing_factors, suggested_prevention,
                       severity, analyzed_at, lesson_id
                FROM failures
                ORDER BY analyzed_at DESC
                LIMIT ?
            ''', (limit,))
            
            failures = []
            for row in cursor.fetchall():
                failure = FailureAnalysis(
                    failure_id=row[0],
                    decision_id=row[1],
                    failure_type=row[2],
                    root_cause=row[3],
                    context=json.loads(row[4]),
                    contributing_factors=json.loads(row[5]),
                    suggested_prevention=row[6],
                    severity=row[7],
                    analyzed_at=row[8]
                )
                failures.append(failure)
            
            return failures
    
    def cleanup_old_data(self, days: int = 90):
        """
        Clean up old failures and lessons
        
        Args:
            days: Number of days to keep data
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete old failures
            cursor.execute('DELETE FROM failures WHERE analyzed_at < ?', (cutoff_date,))
            
            # Delete old lessons with low effectiveness
            cursor.execute('''
                DELETE FROM lessons_learned 
                WHERE updated_at < ? AND effectiveness < 0.5 AND frequency < 3
            ''', (cutoff_date,))
            
            conn.commit()