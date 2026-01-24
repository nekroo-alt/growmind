"""
Lesson Learner Module

This module implements systematic learning from failures for the L4D V4 system.
It records every failure with full context, analyzes root causes, identifies patterns,
generates lessons learned, and updates decision heuristics to avoid repeated mistakes.

Key Features:
- Record failures with full context
- Root cause analysis
- Pattern identification
- Lesson extraction and storage
- Heuristic updates
- Mistake reduction tracking
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from threading import RLock
import hashlib
from collections import defaultdict, Counter


class FailureRecord:
    """Represents a recorded failure with full context."""
    
    def __init__(
        self,
        failure_id: str,
        timestamp: str,
        failure_type: str,
        context: Dict[str, Any],
        decision: Dict[str, Any],
        root_cause: str,
        severity: str = "medium",
        resources: Optional[Dict[str, Any]] = None
    ):
        self.failure_id = failure_id
        self.timestamp = timestamp
        self.failure_type = failure_type
        self.context = context
        self.decision = decision
        self.root_cause = root_cause
        self.severity = severity  # low, medium, high, critical
        self.resources = resources or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'failure_id': self.failure_id,
            'timestamp': self.timestamp,
            'failure_type': self.failure_type,
            'context': self.context,
            'decision': self.decision,
            'root_cause': self.root_cause,
            'severity': self.severity,
            'resources': self.resources
        }


class LessonLearned:
    """Represents a lesson learned from a failure."""
    
    def __init__(
        self,
        lesson_id: str,
        timestamp: str,
        failure_type: str,
        root_cause: str,
        context_pattern: str,
        prevention: str,
        severity: str = "medium",
        effectiveness_score: float = 0.0,
        application_count: int = 0
    ):
        self.lesson_id = lesson_id
        self.timestamp = timestamp
        self.failure_type = failure_type
        self.root_cause = root_cause
        self.context_pattern = context_pattern
        self.prevention = prevention
        self.severity = severity
        self.effectiveness_score = effectiveness_score
        self.application_count = application_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'lesson_id': self.lesson_id,
            'timestamp': self.timestamp,
            'failure_type': self.failure_type,
            'root_cause': self.root_cause,
            'context_pattern': self.context_pattern,
            'prevention': self.prevention,
            'severity': self.severity,
            'effectiveness_score': self.effectiveness_score,
            'application_count': self.application_count
        }


class LessonLearner:
    """
    Main class for learning from mistakes systematically.
    
    This class:
    - Records every failure with full context
    - Analyzes root causes of failures
    - Identifies patterns in failures
    - Generates lessons learned
    - Updates heuristics based on lessons
    - Tracks mistake reduction over time
    """
    
    def __init__(self, db_path: str = "lessons_learned.db"):
        """
        Initialize the LessonLearner.
        
        Args:
            db_path: Path to the SQLite database for storing lessons
        """
        self.db_path = db_path
        self.lock = RLock()
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Failures table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failures (
                    failure_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    context TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    resources TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Lessons table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    lesson_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    context_pattern TEXT NOT NULL,
                    prevention TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    effectiveness_score REAL DEFAULT 0.0,
                    application_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Failure patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failure_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_hash TEXT NOT NULL UNIQUE,
                    failure_type TEXT NOT NULL,
                    context_signature TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Lesson application tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lesson_applications (
                    application_id TEXT PRIMARY KEY,
                    lesson_id TEXT NOT NULL,
                    decision_id TEXT,
                    timestamp TEXT NOT NULL,
                    prevented BOOLEAN,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
                )
            """)
            
            # Create indexes for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_failures_type 
                ON failures(failure_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_failures_timestamp 
                ON failures(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lessons_type 
                ON lessons(failure_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lessons_effectiveness 
                ON lessons(effectiveness_score DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_hash 
                ON failure_patterns(pattern_hash)
            """)
            
            conn.commit()
    
    def record_failure(
        self,
        failure_type: str,
        context: Dict[str, Any],
        decision: Dict[str, Any],
        root_cause: str,
        severity: str = "medium",
        resources: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a failure with full context.
        
        Args:
            failure_type: Type of failure (e.g., 'api_rate_limit', 'timeout', 'invalid_context')
            context: Context at time of failure
            decision: Decision that led to failure
            root_cause: Root cause analysis
            severity: Severity level (low, medium, high, critical)
            resources: Resources consumed (tokens, time, etc.)
        
        Returns:
            failure_id: Unique identifier for the failure record
        """
        failure_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO failures 
                    (failure_id, timestamp, failure_type, context, decision, root_cause, severity, resources)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    failure_id,
                    timestamp,
                    failure_type,
                    json.dumps(context),
                    json.dumps(decision),
                    root_cause,
                    severity,
                    json.dumps(resources) if resources else None
                ))
                conn.commit()
        
        # Update failure patterns
        self._update_failure_patterns(failure_type, context)
        
        return failure_id
    
    def _update_failure_patterns(self, failure_type: str, context: Dict[str, Any]):
        """
        Update failure pattern tracking.
        
        Args:
            failure_type: Type of failure
            context: Context at time of failure
        """
        # Create a signature from context
        context_signature = self._create_context_signature(context)
        pattern_hash = hashlib.md5(
            f"{failure_type}:{context_signature}".encode()
        ).hexdigest()
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if pattern exists
                cursor.execute("""
                    SELECT pattern_id, frequency 
                    FROM failure_patterns 
                    WHERE pattern_hash = ?
                """, (pattern_hash,))
                
                result = cursor.fetchone()
                timestamp = datetime.utcnow().isoformat()
                
                if result:
                    # Update existing pattern
                    pattern_id, frequency = result
                    cursor.execute("""
                        UPDATE failure_patterns
                        SET frequency = frequency + 1,
                            last_seen = ?
                        WHERE pattern_id = ?
                    """, (timestamp, pattern_id))
                else:
                    # Create new pattern
                    pattern_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO failure_patterns
                        (pattern_id, pattern_hash, failure_type, context_signature, frequency, last_seen, first_seen)
                        VALUES (?, ?, ?, ?, 1, ?, ?)
                    """, (pattern_id, pattern_hash, failure_type, context_signature, timestamp, timestamp))
                
                conn.commit()
    
    def _create_context_signature(self, context: Dict[str, Any]) -> str:
        """
        Create a signature from context for pattern matching.
        
        Args:
            context: Context dictionary
        
        Returns:
            String signature of the context
        """
        # Extract key features for signature
        features = []
        
        # Task type
        if 'task_type' in context:
            features.append(f"task:{context['task_type']}")
        
        # Situation type
        if 'situation_type' in context:
            features.append(f"situation:{context['situation_type']}")
        
        # Error type
        if 'error_type' in context:
            features.append(f"error:{context['error_type']}")
        
        # Strategy used
        if 'strategy' in context:
            features.append(f"strategy:{context['strategy']}")
        
        # Action type
        if 'action_type' in context:
            features.append(f"action:{context['action_type']}")
        
        return "|".join(sorted(features))
    
    def analyze_root_cause(
        self,
        failure_type: str,
        context: Dict[str, Any],
        decision: Dict[str, Any]
    ) -> str:
        """
        Analyze root cause of a failure.
        
        Args:
            failure_type: Type of failure
            context: Context at time of failure
            decision: Decision that led to failure
        
        Returns:
            Root cause description
        """
        # This is a simplified implementation
        # In production, this could use LLM for deeper analysis
        
        root_causes = []
        
        # Check for common root causes
        if 'error_type' in context:
            root_causes.append(f"Encountered error: {context['error_type']}")
        
        if 'strategy' in decision:
            strategy = decision.get('strategy')
            root_causes.append(f"Used strategy: {strategy}")
        
        if 'reasoning' in decision:
            reasoning = decision.get('reasoning', '')[:100]
            root_causes.append(f"Reasoning: {reasoning}")
        
        if 'confidence' in decision:
            confidence = decision['confidence']
            if confidence < 0.5:
                root_causes.append("Low confidence decision (< 0.5)")
        
        if not root_causes:
            root_causes.append("Unknown root cause - insufficient context")
        
        return " | ".join(root_causes)
    
    def extract_lesson(
        self,
        failure_id: str,
        prevention: Optional[str] = None
    ) -> Optional[LessonLearned]:
        """
        Extract a lesson from a failure.
        
        Args:
            failure_id: ID of the failure to extract lesson from
            prevention: Prevention strategy (optional, will be generated if not provided)
        
        Returns:
            LessonLearned object or None if failure not found
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT failure_id, timestamp, failure_type, context, decision, root_cause, severity
                    FROM failures
                    WHERE failure_id = ?
                """, (failure_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                failure_id, timestamp, failure_type, context, decision, root_cause, severity = result
                context = json.loads(context)
                decision = json.loads(decision)
        
        # Generate prevention strategy if not provided
        if prevention is None:
            prevention = self._generate_prevention(failure_type, context, decision, root_cause)
        
        # Create context pattern for matching
        context_pattern = self._create_context_pattern(context, failure_type)
        
        lesson_id = str(uuid.uuid4())
        lesson = LessonLearned(
            lesson_id=lesson_id,
            timestamp=datetime.utcnow().isoformat(),
            failure_type=failure_type,
            root_cause=root_cause,
            context_pattern=context_pattern,
            prevention=prevention,
            severity=severity
        )
        
        # Store lesson
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO lessons
                    (lesson_id, timestamp, failure_type, root_cause, context_pattern, prevention, severity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    lesson_id,
                    lesson.timestamp,
                    lesson.failure_type,
                    lesson.root_cause,
                    lesson.context_pattern,
                    lesson.prevention,
                    lesson.severity
                ))
                conn.commit()
        
        return lesson
    
    def _create_context_pattern(self, context: Dict[str, Any], failure_type: str) -> str:
        """
        Create a pattern string for context matching.
        
        Args:
            context: Context dictionary
            failure_type: Type of failure
        
        Returns:
            Pattern string
        """
        # Don't include failure_type in pattern, rely on error_type in context
        # This allows lessons to match based on observable context rather than internal type
        
        patterns = []
        
        # Add relevant context features (only include existing keys)
        for key in ['task_type', 'situation_type', 'error_type', 'action_type', 'strategy']:
            if key in context:
                patterns.append(f"{key}={context[key]}")
        
        return " AND ".join(patterns)
    
    def _generate_prevention(
        self,
        failure_type: str,
        context: Dict[str, Any],
        decision: Dict[str, Any],
        root_cause: str
    ) -> str:
        """
        Generate prevention strategy for a failure.
        
        Args:
            failure_type: Type of failure
            context: Context at time of failure
            decision: Decision that led to failure
            root_cause: Root cause analysis
        
        Returns:
            Prevention strategy string
        """
        # This is a simplified implementation
        # In production, this could use LLM for better prevention strategies
        
        strategies = {
            'api_rate_limit': 'Implement rate limiting and exponential backoff',
            'timeout': 'Increase timeout limits or break operation into smaller chunks',
            'invalid_context': 'Validate context completeness before decision making',
            'insufficient_tokens': 'Monitor token usage and implement budget management',
            'low_confidence': 'Require minimum confidence threshold or request more context',
            'loop_detected': 'Implement loop detection and recovery mechanisms',
            'dead_end': 'Implement early progress validation and backtracking',
            'circular_reasoning': 'Track decision dependencies and document decisions',
            'scope_creep': 'Freeze task scope and break into smaller subtasks'
        }
        
        if failure_type in strategies:
            return strategies[failure_type]
        
        # Generic prevention based on root cause
        if 'low confidence' in root_cause:
            return 'Increase confidence threshold or request more context before decision'
        elif 'error' in root_cause.lower():
            return 'Implement error handling and recovery mechanisms'
        else:
            return 'Analyze similar past failures and apply learned prevention strategies'
    
    def check_lessons(
        self,
        current_context: Dict[str, Any],
        current_decision: Dict[str, Any]
    ) -> List[LessonLearned]:
        """
        Check if any lessons apply to current situation.
        
        Args:
            current_context: Current context
            current_decision: Current decision being considered
        
        Returns:
            List of applicable lessons
        """
        applicable_lessons = []
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Query all lessons
                cursor.execute("""
                    SELECT lesson_id, timestamp, failure_type, root_cause, 
                           context_pattern, prevention, severity, effectiveness_score, application_count
                    FROM lessons
                    ORDER BY effectiveness_score DESC
                """)
                
                results = cursor.fetchall()
        
        for result in results:
            (lesson_id, timestamp, failure_type, root_cause, context_pattern,
             prevention, severity, effectiveness_score, application_count) = result
            
            lesson = LessonLearned(
                lesson_id=lesson_id,
                timestamp=timestamp,
                failure_type=failure_type,
                root_cause=root_cause,
                context_pattern=context_pattern,
                prevention=prevention,
                severity=severity,
                effectiveness_score=effectiveness_score,
                application_count=application_count
            )
            
            # Check if lesson applies
            if self._lesson_applies(lesson, current_context, current_decision):
                applicable_lessons.append(lesson)
        
        return applicable_lessons
    
    def _lesson_applies(
        self,
        lesson: LessonLearned,
        current_context: Dict[str, Any],
        current_decision: Dict[str, Any]
    ) -> bool:
        """
        Check if a lesson applies to current situation.
        
        Args:
            lesson: Lesson to check
            current_context: Current context
            current_decision: Current decision
        
        Returns:
            True if lesson applies
        """
        # Parse lesson context pattern
        pattern_parts = lesson.context_pattern.split(" AND ")
        
        matched_conditions = 0
        
        for part in pattern_parts:
            if "=" not in part:
                continue
            
            key, value = part.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Check if current context matches pattern
            if key in current_context:
                if str(current_context[key]) != value:
                    return False
                matched_conditions += 1
            elif key in current_decision:
                if str(current_decision[key]) != value:
                    return False
                matched_conditions += 1
            else:
                # Key not found - pattern doesn't match
                return False
        
        # Must match at least one condition
        return matched_conditions > 0
    
    def apply_lesson(
        self,
        lesson_id: str,
        decision_id: Optional[str] = None,
        prevented: bool = True
    ) -> bool:
        """
        Record application of a lesson.
        
        Args:
            lesson_id: ID of the lesson applied
            decision_id: ID of the decision (optional)
            prevented: Whether the lesson prevented a failure
        
        Returns:
            True if successful
        """
        application_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Record application
                cursor.execute("""
                    INSERT INTO lesson_applications
                    (application_id, lesson_id, decision_id, timestamp, prevented)
                    VALUES (?, ?, ?, ?, ?)
                """, (application_id, lesson_id, decision_id, timestamp, prevented))
                
                # Update lesson application count
                cursor.execute("""
                    UPDATE lessons
                    SET application_count = application_count + 1
                    WHERE lesson_id = ?
                """, (lesson_id,))
                
                # Update effectiveness score
                if prevented:
                    cursor.execute("""
                        UPDATE lessons
                        SET effectiveness_score = effectiveness_score + 0.1
                        WHERE lesson_id = ? AND effectiveness_score < 1.0
                    """, (lesson_id,))
                
                conn.commit()
        
        return True
    
    def get_failure_patterns(
        self,
        failure_type: Optional[str] = None,
        min_frequency: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get frequent failure patterns.
        
        Args:
            failure_type: Filter by failure type (optional)
            min_frequency: Minimum frequency threshold
        
        Returns:
            List of failure patterns
        """
        patterns = []
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if failure_type:
                    cursor.execute("""
                        SELECT pattern_id, pattern_hash, failure_type, context_signature, 
                               frequency, last_seen, first_seen
                        FROM failure_patterns
                        WHERE failure_type = ? AND frequency >= ?
                        ORDER BY frequency DESC
                    """, (failure_type, min_frequency))
                else:
                    cursor.execute("""
                        SELECT pattern_id, pattern_hash, failure_type, context_signature, 
                               frequency, last_seen, first_seen
                        FROM failure_patterns
                        WHERE frequency >= ?
                        ORDER BY frequency DESC
                    """, (min_frequency,))
                
                results = cursor.fetchall()
        
        for result in results:
            pattern_id, pattern_hash, failure_type, context_signature, frequency, last_seen, first_seen = result
            patterns.append({
                'pattern_id': pattern_id,
                'pattern_hash': pattern_hash,
                'failure_type': failure_type,
                'context_signature': context_signature,
                'frequency': frequency,
                'last_seen': last_seen,
                'first_seen': first_seen
            })
        
        return patterns
    
    def get_lessons(
        self,
        failure_type: Optional[str] = None,
        min_effectiveness: float = 0.0,
        limit: int = 100
    ) -> List[LessonLearned]:
        """
        Get lessons learned.
        
        Args:
            failure_type: Filter by failure type (optional)
            min_effectiveness: Minimum effectiveness score
            limit: Maximum number of lessons to return
        
        Returns:
            List of lessons
        """
        lessons = []
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if failure_type:
                    cursor.execute("""
                        SELECT lesson_id, timestamp, failure_type, root_cause,
                               context_pattern, prevention, severity, effectiveness_score, application_count
                        FROM lessons
                        WHERE failure_type = ? AND effectiveness_score >= ?
                        ORDER BY effectiveness_score DESC
                        LIMIT ?
                    """, (failure_type, min_effectiveness, limit))
                else:
                    cursor.execute("""
                        SELECT lesson_id, timestamp, failure_type, root_cause,
                               context_pattern, prevention, severity, effectiveness_score, application_count
                        FROM lessons
                        WHERE effectiveness_score >= ?
                        ORDER BY effectiveness_score DESC
                        LIMIT ?
                    """, (min_effectiveness, limit))
                
                results = cursor.fetchall()
        
        for result in results:
            (lesson_id, timestamp, failure_type, root_cause, context_pattern,
             prevention, severity, effectiveness_score, application_count) = result
            
            lessons.append(LessonLearned(
                lesson_id=lesson_id,
                timestamp=timestamp,
                failure_type=failure_type,
                root_cause=root_cause,
                context_pattern=context_pattern,
                prevention=prevention,
                severity=severity,
                effectiveness_score=effectiveness_score,
                application_count=application_count
            ))
        
        return lessons
    
    def get_mistake_reduction_metrics(self) -> Dict[str, Any]:
        """
        Get metrics on mistake reduction over time.
        
        Returns:
            Dictionary with reduction metrics
        """
        metrics = {
            'total_failures': 0,
            'total_lessons': 0,
            'total_applications': 0,
            'prevented_failures': 0,
            'failure_by_type': defaultdict(int),
            'lesson_effectiveness': [],
            'patterns_found': 0
        }
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count failures
                cursor.execute("SELECT COUNT(*) FROM failures")
                metrics['total_failures'] = cursor.fetchone()[0]
                
                # Count failures by type
                cursor.execute("""
                    SELECT failure_type, COUNT(*) 
                    FROM failures 
                    GROUP BY failure_type
                """)
                for failure_type, count in cursor.fetchall():
                    metrics['failure_by_type'][failure_type] = count
                
                # Count lessons
                cursor.execute("SELECT COUNT(*) FROM lessons")
                metrics['total_lessons'] = cursor.fetchone()[0]
                
                # Count lesson applications
                cursor.execute("SELECT COUNT(*) FROM lesson_applications")
                metrics['total_applications'] = cursor.fetchone()[0]
                
                # Count prevented failures
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM lesson_applications 
                    WHERE prevented = 1
                """)
                metrics['prevented_failures'] = cursor.fetchone()[0]
                
                # Get effectiveness scores
                cursor.execute("SELECT effectiveness_score FROM lessons")
                metrics['lesson_effectiveness'] = [score[0] for score in cursor.fetchall()]
                
                # Count patterns
                cursor.execute("SELECT COUNT(*) FROM failure_patterns")
                metrics['patterns_found'] = cursor.fetchone()[0]
        
        # Calculate derived metrics
        if metrics['total_lessons'] > 0:
            metrics['avg_effectiveness'] = sum(metrics['lesson_effectiveness']) / len(metrics['lesson_effectiveness'])
        else:
            metrics['avg_effectiveness'] = 0.0
        
        if metrics['total_applications'] > 0:
            metrics['prevention_rate'] = metrics['prevented_failures'] / metrics['total_applications']
        else:
            metrics['prevention_rate'] = 0.0
        
        # Convert defaultdict to dict
        metrics['failure_by_type'] = dict(metrics['failure_by_type'])
        
        return metrics
    
    def delete_old_failures(self, days_old: int = 90) -> int:
        """
        Delete old failure records.
        
        Args:
            days_old: Delete failures older than this many days
        
        Returns:
            Number of failures deleted
        """
        from datetime import datetime, timedelta
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM failures
                    WHERE timestamp < ?
                """, (cutoff_date,))
                deleted_count = cursor.rowcount
                conn.commit()
        
        return deleted_count
    
    def export_lessons(self, output_format: str = "json") -> str:
        """
        Export all lessons to a string.
        
        Args:
            output_format: Format to export ('json' or 'dict')
        
        Returns:
            Exported lessons as string or dict
        """
        lessons = self.get_lessons()
        
        if output_format == "dict":
            return [lesson.to_dict() for lesson in lessons]
        elif output_format == "json":
            return json.dumps([lesson.to_dict() for lesson in lessons], indent=2)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")