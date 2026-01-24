"""
Self-Reflection Mechanism for Continuous Improvement

This module implements the self-reflection mechanism that enables the system to:
- Review recent decisions and identify patterns
- Identify areas for improvement
- Generate self-reflection reports
- Update heuristics based on learnings
- Reflect on strategy performance
- Schedule regular reflection intervals
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

# Import V4 modules
from data.decision_history import DecisionHistoryManager
from logic.pattern_recognizer import PatternRecognizer
from logic.adaptive_heuristics import AdaptiveHeuristics


class SelfReflection:
    """
    Self-reflection mechanism for continuous improvement.
    
    Performs regular self-reflection to:
    - Review recent decisions
    - Analyze patterns
    - Identify successes and failures
    - Generate insights
    - Update heuristics/strategies
    """
    
    def __init__(
        self,
        decision_history: DecisionHistoryManager,
        pattern_recognizer: PatternRecognizer,
        adaptive_heuristics: AdaptiveHeuristics,
        db_path: str = "v4_self_reflection.db"
    ):
        """
        Initialize self-reflection mechanism.
        
        Args:
            decision_history: Decision history tracking system
            pattern_recognizer: Pattern recognition engine
            adaptive_heuristics: Adaptive heuristics system
            db_path: Path to SQLite database for reflection storage
        """
        self.decision_history = decision_history
        self.pattern_recognizer = pattern_recognizer
        self.adaptive_heuristics = adaptive_heuristics
        self.db_path = db_path
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for reflection storage."""
        import sqlite3
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                reflection_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                operation_count INTEGER,
                time_range_hours REAL,
                reflection_data TEXT NOT NULL,
                insights TEXT,
                recommendations TEXT,
                action_items TEXT,
                heuristics_updated INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS reflection_schedule (
                schedule_id TEXT PRIMARY KEY,
                trigger_type TEXT NOT NULL,
                interval_operations INTEGER,
                interval_hours REAL,
                last_reflection_time TEXT,
                next_reflection_time TEXT,
                enabled INTEGER DEFAULT 1
            )
        """)
        
        self.conn.commit()
    
    def perform_reflection(
        self,
        trigger_type: str,
        lookback_hours: Optional[float] = None,
        operation_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform self-reflection based on trigger type.
        
        Args:
            trigger_type: Type of reflection trigger ('after_task', 'after_error', 
                         'periodic', 'on_request')
            lookback_hours: Hours to look back for decisions (optional)
            operation_count: Number of operations to review (optional)
        
        Returns:
            Reflection report with insights and recommendations
        """
        self.logger.info(f"Performing self-reflection (trigger: {trigger_type})")
        
        # Determine time range
        if lookback_hours is None:
            lookback_hours = 24  # Default: look back 24 hours
        
        start_time = datetime.now() - timedelta(hours=lookback_hours)
        
        # Collect recent decisions
        decisions = self.decision_history.list_decisions(
            start_time=start_time,
            limit=operation_count or 100
        )
        
        if not decisions:
            self.logger.warning("No decisions found for reflection")
            return {
                "reflection_id": self._generate_id(),
                "timestamp": datetime.now().isoformat(),
                "trigger_type": trigger_type,
                "status": "no_data",
                "message": "No decisions found for reflection"
            }
        
        # Analyze patterns
        patterns = self.pattern_recognizer.recognize_patterns()
        
        # Identify successes and failures
        successes = self._identify_successes(decisions)
        failures = self._identify_failures(decisions)
        
        # Generate insights
        insights = self._generate_insights(decisions, patterns, successes, failures)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(insights, patterns)
        
        # Generate action items
        action_items = self._generate_action_items(recommendations)
        
        # Update heuristics based on learnings
        heuristics_updated = self._update_heuristics(insights, patterns)
        
        # Create reflection report
        reflection_report = {
            "reflection_id": self._generate_id(),
            "timestamp": datetime.now().isoformat(),
            "trigger_type": trigger_type,
            "operation_count": len(decisions),
            "time_range_hours": lookback_hours,
            "summary": self._generate_summary(decisions, insights, heuristics_updated),
            "insights": insights,
            "recommendations": recommendations,
            "action_items": action_items,
            "heuristics_updated": heuristics_updated
        }
        
        # Store reflection
        self._store_reflection(reflection_report)
        
        # Update schedule
        self._update_schedule(trigger_type)
        
        self.logger.info(f"Self-reflection complete: {len(insights)} insights, "
                       f"{len(recommendations)} recommendations")
        
        return reflection_report
    
    def _identify_successes(
        self,
        decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identify successful decisions.
        
        Args:
            decisions: List of decisions to analyze
        
        Returns:
            List of successful decisions with details
        """
        successes = []
        
        for decision in decisions:
            # Success criteria: outcome is 'success' and confidence > 0.7
            if (decision.get('outcome') == 'success' and
                decision.get('confidence', 0) > 0.7):
                
                successes.append({
                    "decision_id": decision.get('id'),
                    "action": decision.get('action'),
                    "reasoning": decision.get('reasoning'),
                    "confidence": decision.get('confidence'),
                    "outcome": decision.get('outcome'),
                    "time_elapsed": decision.get('time_elapsed'),
                    "resources": decision.get('resources')
                })
        
        # Sort by time elapsed (fastest first)
        successes.sort(key=lambda x: x.get('time_elapsed', float('inf')))
        
        return successes
    
    def _identify_failures(
        self,
        decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identify failed decisions.
        
        Args:
            decisions: List of decisions to analyze
        
        Returns:
            List of failed decisions with details
        """
        failures = []
        
        for decision in decisions:
            # Failure criteria: outcome is 'failure' or low confidence success
            if (decision.get('outcome') == 'failure' or
                (decision.get('outcome') == 'success' and
                 decision.get('confidence', 0) < 0.5)):
                
                failures.append({
                    "decision_id": decision.get('id'),
                    "action": decision.get('action'),
                    "reasoning": decision.get('reasoning'),
                    "confidence": decision.get('confidence'),
                    "outcome": decision.get('outcome'),
                    "error": decision.get('error'),
                    "resources": decision.get('resources')
                })
        
        # Sort by frequency of similar failures
        from collections import Counter
        failure_actions = [f['action'] for f in failures]
        failure_counts = Counter(failure_actions)
        
        failures.sort(
            key=lambda x: failure_counts.get(x['action'], 0),
            reverse=True
        )
        
        return failures
    
    def _generate_insights(
        self,
        decisions: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]],
        successes: List[Dict[str, Any]],
        failures: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate insights from decisions and patterns.
        
        Args:
            decisions: List of decisions
            patterns: List of recognized patterns
            successes: List of successful decisions
            failures: List of failed decisions
        
        Returns:
            List of insights
        """
        insights = []
        
        # Insight 1: Overall success rate
        total = len(decisions)
        success_count = sum(1 for d in decisions if d.get('outcome') == 'success')
        success_rate = success_count / total if total > 0 else 0
        
        insights.append({
            "type": "performance",
            "category": "success_rate",
            "value": success_rate,
            "description": f"Overall success rate: {success_rate:.1%}",
            "severity": "good" if success_rate > 0.8 else "warning" if success_rate > 0.6 else "critical"
        })
        
        # Insight 2: Average confidence
        avg_confidence = sum(d.get('confidence', 0) for d in decisions) / total if total > 0 else 0
        
        insights.append({
            "type": "performance",
            "category": "confidence",
            "value": avg_confidence,
            "description": f"Average confidence: {avg_confidence:.2f}",
            "severity": "good" if avg_confidence > 0.8 else "warning" if avg_confidence > 0.6 else "critical"
        })
        
        # Insight 3: Top success patterns
        success_patterns = [p for p in patterns if p.get('success_rate', 0) > 0.8]
        if success_patterns:
            insights.append({
                "type": "pattern",
                "category": "successful",
                "value": len(success_patterns),
                "description": f"Identified {len(success_patterns)} successful patterns",
                "patterns": success_patterns[:3],  # Top 3
                "severity": "good"
            })
        
        # Insight 4: Top failure patterns
        failure_patterns = [p for p in patterns if p.get('success_rate', 1) < 0.5]
        if failure_patterns:
            insights.append({
                "type": "pattern",
                "category": "failure",
                "value": len(failure_patterns),
                "description": f"Identified {len(failure_patterns)} failure patterns",
                "patterns": failure_patterns[:3],  # Top 3
                "severity": "critical"
            })
        
        # Insight 5: Most common failure
        if failures:
            from collections import Counter
            failure_actions = [f['action'] for f in failures]
            most_common = Counter(failure_actions).most_common(1)[0]
            
            insights.append({
                "type": "failure",
                "category": "common_failure",
                "value": most_common[1],
                "description": f"Most common failure: '{most_common[0]}' ({most_common[1]} occurrences)",
                "severity": "critical" if most_common[1] > 3 else "warning"
            })
        
        # Insight 6: Resource efficiency
        total_tokens = sum(d.get('resources', {}).get('tokens', 0) for d in decisions)
        avg_tokens = total_tokens / total if total > 0 else 0
        
        insights.append({
            "type": "efficiency",
            "category": "resource_usage",
            "value": avg_tokens,
            "description": f"Average tokens per decision: {avg_tokens:.0f}",
            "severity": "good" if avg_tokens < 2000 else "warning" if avg_tokens < 5000 else "critical"
        })
        
        return insights
    
    def _generate_recommendations(
        self,
        insights: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on insights and patterns.
        
        Args:
            insights: List of insights
            patterns: List of patterns
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Analyze insights for actionable recommendations
        for insight in insights:
            if insight['type'] == 'performance':
                if insight['category'] == 'success_rate':
                    if insight['value'] < 0.6:
                        recommendations.append({
                            "priority": "high",
                            "category": "performance",
                            "action": "Improve decision quality",
                            "description": "Success rate is below 60%. Review decision-making process and consider more conservative approach.",
                            "insight_ref": insight
                        })
                
                elif insight['category'] == 'confidence':
                    if insight['value'] < 0.6:
                        recommendations.append({
                            "priority": "medium",
                            "category": "confidence",
                            "action": "Improve confidence estimation",
                            "description": "Average confidence is low. Consider gathering more context or improving confidence calibration.",
                            "insight_ref": insight
                        })
            
            elif insight['type'] == 'pattern':
                if insight['category'] == 'failure':
                    recommendations.append({
                        "priority": "high",
                        "category": "pattern",
                        "action": "Address failure patterns",
                        "description": f"Address identified failure patterns to reduce recurrence.",
                        "patterns": insight['patterns'],
                        "insight_ref": insight
                    })
            
            elif insight['type'] == 'failure':
                if insight['category'] == 'common_failure':
                    recommendations.append({
                        "priority": "high",
                        "category": "failure",
                        "action": "Investigate common failure",
                        "description": f"Investigate and address the most common failure: '{insight['description'].split(':')[1].strip().split('(')[0].strip()}'",
                        "insight_ref": insight
                    })
            
            elif insight['type'] == 'efficiency':
                if insight['category'] == 'resource_usage':
                    if insight['value'] > 5000:
                        recommendations.append({
                            "priority": "medium",
                            "category": "efficiency",
                            "action": "Optimize resource usage",
                            "description": "Average token usage is high. Consider improving context pruning or using more efficient reasoning.",
                            "insight_ref": insight
                        })
        
        return recommendations
    
    def _generate_action_items(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate action items from recommendations.
        
        Args:
            recommendations: List of recommendations
        
        Returns:
            List of action items
        """
        action_items = []
        
        for i, rec in enumerate(recommendations):
            action_items.append({
                "action_id": self._generate_id(),
                "priority": rec['priority'],
                "category": rec['category'],
                "action": rec['action'],
                "description": rec['description'],
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "recommendation_ref": i
            })
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        action_items.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return action_items
    
    def _update_heuristics(
        self,
        insights: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]]
    ) -> bool:
        """
        Update heuristics based on insights and patterns.
        
        Args:
            insights: List of insights
            patterns: List of patterns
        
        Returns:
            True if heuristics were updated, False otherwise
        """
        try:
            # Update heuristics based on insights
            for insight in insights:
                if insight['type'] == 'performance':
                    if insight['category'] == 'success_rate':
                        # Adjust confidence threshold based on success rate
                        if insight['value'] < 0.6:
                            self.adaptive_heuristics.update_heuristic(
                                'confidence_threshold',
                                0.85,  # Increase to be more conservative
                                reason="Low success rate detected"
                            )
                        elif insight['value'] > 0.9:
                            self.adaptive_heuristics.update_heuristic(
                                'confidence_threshold',
                                0.65,  # Decrease to be more aggressive
                                reason="High success rate detected"
                            )
            
            # Update heuristics based on patterns
            for pattern in patterns:
                if pattern.get('success_rate', 1) > 0.85:
                    # Reinforce successful patterns
                    self.adaptive_heuristics.update_heuristic(
                        f'pattern_weight_{pattern.get("pattern_id", "unknown")}',
                        1.2,  # Increase weight
                        reason="High success rate pattern"
                    )
                elif pattern.get('success_rate', 0) < 0.5:
                    # Penalize failure patterns
                    self.adaptive_heuristics.update_heuristic(
                        f'pattern_weight_{pattern.get("pattern_id", "unknown")}',
                        0.8,  # Decrease weight
                        reason="Low success rate pattern"
                    )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to update heuristics: {e}")
            return False
    
    def _generate_summary(
        self,
        decisions: List[Dict[str, Any]],
        insights: List[Dict[str, Any]],
        heuristics_updated: bool
    ) -> str:
        """
        Generate summary of reflection.
        
        Args:
            decisions: List of decisions reviewed
            insights: List of insights generated
            heuristics_updated: Whether heuristics were updated
        
        Returns:
            Summary text
        """
        total = len(decisions)
        success_count = sum(1 for d in decisions if d.get('outcome') == 'success')
        success_rate = success_count / total if total > 0 else 0
        
        summary = (
            f"Reviewed {total} decisions with {success_rate:.1%} success rate. "
            f"Generated {len(insights)} insights. "
            f"Heuristics {'updated' if heuristics_updated else 'not updated'}."
        ).lower()
        
        return summary
    
    def _store_reflection(self, reflection: Dict[str, Any]) -> None:
        """
        Store reflection in database.
        
        Args:
            reflection: Reflection report to store
        """
        import sqlite3
        try:
            self.conn.execute("""
                INSERT INTO reflections (
                    reflection_id, timestamp, trigger_type, operation_count,
                    time_range_hours, reflection_data, insights, recommendations,
                    action_items, heuristics_updated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reflection['reflection_id'],
                reflection['timestamp'],
                reflection['trigger_type'],
                reflection.get('operation_count'),
                reflection.get('time_range_hours'),
                json.dumps(reflection),
                json.dumps(reflection.get('insights', [])),
                json.dumps(reflection.get('recommendations', [])),
                json.dumps(reflection.get('action_items', [])),
                reflection.get('heuristics_updated', 0),
                datetime.now().isoformat()
            ))
            self.conn.commit()
        
        except sqlite3.Error as e:
            self.logger.error(f"Failed to store reflection: {e}")
    
    def _update_schedule(self, trigger_type: str) -> None:
        """
        Update reflection schedule.
        
        Args:
            trigger_type: Type of trigger that just occurred
        """
        now = datetime.now()
        
        # Get or create schedule for this trigger type
        cursor = self.conn.execute(
            "SELECT * FROM reflection_schedule WHERE trigger_type = ?",
            (trigger_type,)
        )
        row = cursor.fetchone()
        
        if row:
            # Update last reflection time
            self.conn.execute("""
                UPDATE reflection_schedule
                SET last_reflection_time = ?
                WHERE trigger_type = ?
            """, (now.isoformat(), trigger_type))
        else:
            # Create new schedule
            interval_operations = 100 if trigger_type == 'periodic' else None
            interval_hours = 24 if trigger_type == 'periodic' else None
            
            self.conn.execute("""
                INSERT INTO reflection_schedule (
                    schedule_id, trigger_type, interval_operations, interval_hours,
                    last_reflection_time, next_reflection_time, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self._generate_id(),
                trigger_type,
                interval_operations,
                interval_hours,
                now.isoformat(),
                (now + timedelta(hours=interval_hours or 0)).isoformat() if interval_hours else None,
                1
            ))
        
        self.conn.commit()
    
    def schedule_reflection(
        self,
        trigger_type: str,
        interval_operations: Optional[int] = None,
        interval_hours: Optional[float] = None
    ) -> None:
        """
        Schedule regular reflection.
        
        Args:
            trigger_type: Type of trigger ('after_task', 'after_error', 'periodic')
            interval_operations: Interval in number of operations
            interval_hours: Interval in hours
        """
        cursor = self.conn.execute(
            "SELECT schedule_id FROM reflection_schedule WHERE trigger_type = ?",
            (trigger_type,)
        )
        row = cursor.fetchone()
        
        now = datetime.now()
        next_time = None
        if interval_hours:
            next_time = now + timedelta(hours=interval_hours)
        
        if row:
            # Update existing schedule
            self.conn.execute("""
                UPDATE reflection_schedule
                SET interval_operations = ?, interval_hours = ?, next_reflection_time = ?
                WHERE trigger_type = ?
            """, (interval_operations, interval_hours, next_time.isoformat() if next_time else None, trigger_type))
        else:
            # Create new schedule
            self.conn.execute("""
                INSERT INTO reflection_schedule (
                    schedule_id, trigger_type, interval_operations, interval_hours,
                    last_reflection_time, next_reflection_time, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self._generate_id(),
                trigger_type,
                interval_operations,
                interval_hours,
                now.isoformat(),
                next_time.isoformat() if next_time else None,
                1
            ))
        
        self.conn.commit()
        self.logger.info(f"Scheduled reflection: {trigger_type} "
                       f"(every {interval_operations} ops or {interval_hours} hours)")
    
    def get_reflections(
        self,
        trigger_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get stored reflections.
        
        Args:
            trigger_type: Filter by trigger type (optional)
            limit: Maximum number of reflections to return
        
        Returns:
            List of reflection reports
        """
        if trigger_type:
            cursor = self.conn.execute("""
                SELECT reflection_data FROM reflections
                WHERE trigger_type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (trigger_type, limit))
        else:
            cursor = self.conn.execute("""
                SELECT reflection_data FROM reflections
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        return [json.loads(row['reflection_data']) for row in rows]
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        import uuid
        return str(uuid.uuid4())
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
