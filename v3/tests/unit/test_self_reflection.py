"""
Unit tests for SelfReflection module.

Tests the self-reflection mechanism for continuous improvement.
"""

import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from logic.self_reflection import SelfReflection


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    return str(tmp_path / "test_self_reflection.db")


@pytest.fixture
def mock_decision_history():
    """Create mock decision history."""
    mock = Mock()
    return mock


@pytest.fixture
def mock_pattern_recognizer():
    """Create mock pattern recognizer."""
    mock = Mock()
    return mock


@pytest.fixture
def mock_adaptive_heuristics():
    """Create mock adaptive heuristics."""
    mock = Mock()
    mock.update_heuristic = Mock(return_value=True)
    return mock


@pytest.fixture
def self_reflection(
    mock_decision_history,
    mock_pattern_recognizer,
    mock_adaptive_heuristics,
    temp_db_path
):
    """Create SelfReflection instance with mocks."""
    reflection = SelfReflection(
        decision_history=mock_decision_history,
        pattern_recognizer=mock_pattern_recognizer,
        adaptive_heuristics=mock_adaptive_heuristics,
        db_path=temp_db_path
    )
    yield reflection
    reflection.close()


class TestSelfReflectionInitialization:
    """Test SelfReflection initialization."""
    
    def test_initialization(self, temp_db_path):
        """Test that SelfReflection initializes correctly."""
        decision_history = Mock()
        pattern_recognizer = Mock()
        adaptive_heuristics = Mock()
        
        reflection = SelfReflection(
            decision_history=decision_history,
            pattern_recognizer=pattern_recognizer,
            adaptive_heuristics=adaptive_heuristics,
            db_path=temp_db_path
        )
        
        assert reflection.decision_history == decision_history
        assert reflection.pattern_recognizer == pattern_recognizer
        assert reflection.adaptive_heuristics == adaptive_heuristics
        assert reflection.db_path == temp_db_path
        assert reflection.conn is not None
        
        reflection.close()
    
    def test_database_tables_created(self, self_reflection, temp_db_path):
        """Test that database tables are created."""
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Check reflections table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='reflections'
        """)
        assert cursor.fetchone() is not None
        
        # Check reflection_schedule table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='reflection_schedule'
        """)
        assert cursor.fetchone() is not None
        
        conn.close()


class TestPerformReflection:
    """Test perform_reflection method."""
    
    def test_reflection_no_decisions(self, self_reflection, mock_decision_history):
        """Test reflection when no decisions are available."""
        mock_decision_history.list_decisions.return_value = []
        
        result = self_reflection.perform_reflection('periodic')
        
        assert result['status'] == 'no_data'
        assert result['message'] == 'No decisions found for reflection'
        assert 'reflection_id' in result
    
    def test_reflection_with_decisions(
        self,
        self_reflection,
        mock_decision_history,
        mock_pattern_recognizer
    ):
        """Test reflection with decisions."""
        # Setup mock decisions
        decisions = [
            {
                'decision_id': 'd1',
                'timestamp': datetime.now().isoformat(),
                'outcome': 'success',
                'confidence': 0.85,
                'action': 'write_test',
                'reasoning': 'Test needed',
                'time_elapsed': 1.2,
                'resources': {'tokens': 1500}
            },
            {
                'decision_id': 'd2',
                'timestamp': datetime.now().isoformat(),
                'outcome': 'failure',
                'confidence': 0.6,
                'action': 'implement_feature',
                'reasoning': 'Feature required',
                'time_elapsed': 2.5,
                'resources': {'tokens': 3000},
                'error': 'test failed'
            }
        ]
        mock_decision_history.list_decisions.return_value = decisions
        
        # Setup mock patterns
        patterns = [
            {
                'pattern_id': 'p1',
                'success_rate': 0.9,
                'pattern_type': 'decision'
            },
            {
                'pattern_id': 'p2',
                'success_rate': 0.4,
                'pattern_type': 'decision'
            }
        ]
        mock_pattern_recognizer.recognize_patterns.return_value = patterns
        
        # Perform reflection
        result = self_reflection.perform_reflection('periodic')
        
        # Verify result structure
        assert 'reflection_id' in result
        assert result['trigger_type'] == 'periodic'
        assert result['operation_count'] == 2
        assert 'insights' in result
        assert 'recommendations' in result
        assert 'action_items' in result
        assert 'summary' in result
        assert len(result['insights']) > 0
    
    def test_reflection_generates_insights(
        self,
        self_reflection,
        mock_decision_history,
        mock_pattern_recognizer
    ):
        """Test that reflection generates insights."""
        decisions = [
            {
                'decision_id': 'd1',
                'outcome': 'success',
                'confidence': 0.8,
                'action': 'action1',
                'reasoning': 'reasoning1',
                'time_elapsed': 1.0,
                'resources': {'tokens': 1000}
            }
        ]
        mock_decision_history.list_decisions.return_value = decisions
        mock_pattern_recognizer.recognize_patterns.return_value = []
        
        result = self_reflection.perform_reflection('periodic')
        
        insights = result['insights']
        assert len(insights) > 0
        
        # Check insight types
        insight_types = [insight['type'] for insight in insights]
        assert 'performance' in insight_types
    
    def test_reflection_updates_heuristics(
        self,
        self_reflection,
        mock_decision_history,
        mock_pattern_recognizer,
        mock_adaptive_heuristics
    ):
        """Test that reflection updates heuristics."""
        decisions = [
            {
                'decision_id': 'd1',
                'outcome': 'success',
                'confidence': 0.9,
                'action': 'action1',
                'reasoning': 'reasoning1',
                'time_elapsed': 1.0,
                'resources': {'tokens': 1000}
            }
        ]
        mock_decision_history.list_decisions.return_value = decisions
        mock_pattern_recognizer.recognize_patterns.return_value = []
        
        result = self_reflection.perform_reflection('periodic')
        
        # Verify heuristics were updated
        assert 'heuristics_updated' in result


class TestIdentifySuccesses:
    """Test _identify_successes method."""
    
    def test_identify_successful_decisions(self, self_reflection):
        """Test identification of successful decisions."""
        decisions = [
            {
                'decision_id': 'd1',
                'outcome': 'success',
                'confidence': 0.85,
                'action': 'action1',
                'reasoning': 'reasoning1',
                'time_elapsed': 1.0,
                'resources': {'tokens': 1000}
            },
            {
                'decision_id': 'd2',
                'outcome': 'success',
                'confidence': 0.75,
                'action': 'action2',
                'reasoning': 'reasoning2',
                'time_elapsed': 2.0,
                'resources': {'tokens': 2000}
            },
            {
                'decision_id': 'd3',
                'outcome': 'success',
                'confidence': 0.6,  # Too low confidence
                'action': 'action3',
                'reasoning': 'reasoning3',
                'time_elapsed': 1.5,
                'resources': {'tokens': 1500}
            },
            {
                'decision_id': 'd4',
                'outcome': 'failure',
                'confidence': 0.8,
                'action': 'action4',
                'reasoning': 'reasoning4',
                'time_elapsed': 3.0,
                'resources': {'tokens': 3000}
            }
        ]
        
        successes = self_reflection._identify_successes(decisions)
        
        assert len(successes) == 2
        assert all(s['outcome'] == 'success' for s in successes)
        assert all(s['confidence'] > 0.7 for s in successes)
    
    def test_sort_successes_by_time(self, self_reflection):
        """Test that successes are sorted by time elapsed."""
        decisions = [
            {
                'decision_id': 'd1',
                'outcome': 'success',
                'confidence': 0.85,
                'action': 'action1',
                'reasoning': 'reasoning1',
                'time_elapsed': 3.0,
                'resources': {'tokens': 1000}
            },
            {
                'decision_id': 'd2',
                'outcome': 'success',
                'confidence': 0.85,
                'action': 'action2',
                'reasoning': 'reasoning2',
                'time_elapsed': 1.0,
                'resources': {'tokens': 2000}
            }
        ]
        
        successes = self_reflection._identify_successes(decisions)
        
        # Should be sorted by time_elapsed (ascending)
        assert successes[0]['time_elapsed'] < successes[1]['time_elapsed']


class TestIdentifyFailures:
    """Test _identify_failures method."""
    
    def test_identify_failed_decisions(self, self_reflection):
        """Test identification of failed decisions."""
        decisions = [
            {
                'decision_id': 'd1',
                'outcome': 'failure',
                'confidence': 0.8,
                'action': 'action1',
                'reasoning': 'reasoning1',
                'error': 'error1',
                'resources': {'tokens': 1000}
            },
            {
                'decision_id': 'd2',
                'outcome': 'success',
                'confidence': 0.4,  # Low confidence success
                'action': 'action2',
                'reasoning': 'reasoning2',
                'resources': {'tokens': 2000}
            },
            {
                'decision_id': 'd3',
                'outcome': 'success',
                'confidence': 0.85,
                'action': 'action3',
                'reasoning': 'reasoning3',
                'resources': {'tokens': 3000}
            }
        ]
        
        failures = self_reflection._identify_failures(decisions)
        
        assert len(failures) == 2
    
    def test_sort_failures_by_frequency(self, self_reflection):
        """Test that failures are sorted by frequency."""
        decisions = [
            {
                'decision_id': 'd1',
                'outcome': 'failure',
                'confidence': 0.8,
                'action': 'common_action',  # Will appear 3 times
                'reasoning': 'reasoning1',
                'error': 'error1',
                'resources': {'tokens': 1000}
            },
            {
                'decision_id': 'd2',
                'outcome': 'failure',
                'confidence': 0.8,
                'action': 'common_action',
                'reasoning': 'reasoning2',
                'error': 'error2',
                'resources': {'tokens': 2000}
            },
            {
                'decision_id': 'd3',
                'outcome': 'failure',
                'confidence': 0.8,
                'action': 'rare_action',  # Will appear 1 time
                'reasoning': 'reasoning3',
                'error': 'error3',
                'resources': {'tokens': 3000}
            },
            {
                'decision_id': 'd4',
                'outcome': 'failure',
                'confidence': 0.8,
                'action': 'common_action',
                'reasoning': 'reasoning4',
                'error': 'error4',
                'resources': {'tokens': 4000}
            }
        ]
        
        failures = self_reflection._identify_failures(decisions)
        
        # Most common failure should be first
        assert failures[0]['action'] == 'common_action'


class TestGenerateInsights:
    """Test _generate_insights method."""
    
    def test_generate_success_rate_insight(self, self_reflection):
        """Test generation of success rate insight."""
        decisions = [
            {'outcome': 'success', 'confidence': 0.8},
            {'outcome': 'success', 'confidence': 0.85},
            {'outcome': 'failure', 'confidence': 0.6},
            {'outcome': 'success', 'confidence': 0.9},
            {'outcome': 'failure', 'confidence': 0.7}
        ]
        
        insights = self_reflection._generate_insights(
            decisions,
            [],
            [],
            []
        )
        
        # Check for success rate insight
        success_rate_insight = next(
            (i for i in insights if i['category'] == 'success_rate'),
            None
        )
        assert success_rate_insight is not None
        assert success_rate_insight['type'] == 'performance'
        assert success_rate_insight['value'] == 0.6  # 3/5
    
    def test_generate_confidence_insight(self, self_reflection):
        """Test generation of confidence insight."""
        decisions = [
            {'outcome': 'success', 'confidence': 0.8},
            {'outcome': 'success', 'confidence': 0.9},
            {'outcome': 'failure', 'confidence': 0.6}
        ]
        
        insights = self_reflection._generate_insights(
            decisions,
            [],
            [],
            []
        )
        
        # Check for confidence insight
        confidence_insight = next(
            (i for i in insights if i['category'] == 'confidence'),
            None
        )
        assert confidence_insight is not None
        assert confidence_insight['type'] == 'performance'
        assert confidence_insight['value'] == pytest.approx(0.7667, rel=0.01)
    
    def test_generate_efficiency_insight(self, self_reflection):
        """Test generation of efficiency insight."""
        decisions = [
            {
                'outcome': 'success',
                'confidence': 0.8,
                'resources': {'tokens': 1000}
            },
            {
                'outcome': 'success',
                'confidence': 0.9,
                'resources': {'tokens': 2000}
            },
            {
                'outcome': 'failure',
                'confidence': 0.6,
                'resources': {'tokens': 1500}
            }
        ]
        
        insights = self_reflection._generate_insights(
            decisions,
            [],
            [],
            []
        )
        
        # Check for efficiency insight
        efficiency_insight = next(
            (i for i in insights if i['category'] == 'resource_usage'),
            None
        )
        assert efficiency_insight is not None
        assert efficiency_insight['type'] == 'efficiency'
        assert efficiency_insight['value'] == pytest.approx(1500.0, rel=0.01)


class TestGenerateRecommendations:
    """Test _generate_recommendations method."""
    
    def test_generate_recommendations_from_insights(self, self_reflection):
        """Test generation of recommendations from insights."""
        insights = [
            {
                'type': 'performance',
                'category': 'success_rate',
                'value': 0.5,  # Low success rate
                'description': 'Low success rate',
                'severity': 'critical'
            },
            {
                'type': 'performance',
                'category': 'confidence',
                'value': 0.7,  # Medium confidence
                'description': 'Medium confidence',
                'severity': 'warning'
            }
        ]
        
        recommendations = self_reflection._generate_recommendations(
            insights,
            []
        )
        
        assert len(recommendations) > 0
        
        # Should have recommendation for low success rate
        success_rate_rec = next(
            (r for r in recommendations if r['category'] == 'performance'),
            None
        )
        assert success_rate_rec is not None
        assert success_rate_rec['priority'] == 'high'
    
    def test_recommendations_include_priority(self, self_reflection):
        """Test that recommendations have priority levels."""
        insights = [
            {
                'type': 'performance',
                'category': 'success_rate',
                'value': 0.5,
                'description': 'Low success rate',
                'severity': 'critical'
            }
        ]
        
        recommendations = self_reflection._generate_recommendations(
            insights,
            []
        )
        
        # All recommendations should have priority
        assert all('priority' in r for r in recommendations)
        assert all(r['priority'] in ['high', 'medium', 'low'] for r in recommendations)


class TestGenerateActionItems:
    """Test _generate_action_items method."""
    
    def test_generate_action_items_from_recommendations(self, self_reflection):
        """Test generation of action items from recommendations."""
        recommendations = [
            {
                'priority': 'high',
                'category': 'performance',
                'action': 'Improve decision quality',
                'description': 'Improve decision quality'
            },
            {
                'priority': 'medium',
                'category': 'efficiency',
                'action': 'Optimize resources',
                'description': 'Optimize resources'
            }
        ]
        
        action_items = self_reflection._generate_action_items(recommendations)
        
        assert len(action_items) == 2
        
        # All action items should have required fields
        for item in action_items:
            assert 'action_id' in item
            assert 'priority' in item
            assert 'category' in item
            assert 'action' in item
            assert 'description' in item
            assert 'status' in item
            assert item['status'] == 'pending'
    
    def test_sort_action_items_by_priority(self, self_reflection):
        """Test that action items are sorted by priority."""
        recommendations = [
            {
                'priority': 'low',
                'category': 'category1',
                'action': 'action1',
                'description': 'desc1'
            },
            {
                'priority': 'high',
                'category': 'category2',
                'action': 'action2',
                'description': 'desc2'
            },
            {
                'priority': 'medium',
                'category': 'category3',
                'action': 'action3',
                'description': 'desc3'
            }
        ]
        
        action_items = self_reflection._generate_action_items(recommendations)
        
        # Should be sorted: high, medium, low
        assert action_items[0]['priority'] == 'high'
        assert action_items[1]['priority'] == 'medium'
        assert action_items[2]['priority'] == 'low'


class TestUpdateHeuristics:
    """Test _update_heuristics method."""
    
    def test_update_heuristics_on_low_success_rate(
        self,
        self_reflection,
        mock_adaptive_heuristics
    ):
        """Test heuristics update when success rate is low."""
        insights = [
            {
                'type': 'performance',
                'category': 'success_rate',
                'value': 0.5,
                'description': 'Low success rate',
                'severity': 'critical'
            }
        ]
        
        result = self_reflection._update_heuristics(insights, [])
        
        assert result is True
        mock_adaptive_heuristics.update_heuristic.assert_called()
    
    def test_update_heuristics_on_high_success_rate(
        self,
        self_reflection,
        mock_adaptive_heuristics
    ):
        """Test heuristics update when success rate is high."""
        insights = [
            {
                'type': 'performance',
                'category': 'success_rate',
                'value': 0.95,
                'description': 'High success rate',
                'severity': 'good'
            }
        ]
        
        result = self_reflection._update_heuristics(insights, [])
        
        assert result is True
        mock_adaptive_heuristics.update_heuristic.assert_called()
    
    def test_update_heuristics_with_patterns(
        self,
        self_reflection,
        mock_adaptive_heuristics
    ):
        """Test heuristics update with patterns."""
        insights = []
        patterns = [
            {
                'pattern_id': 'p1',
                'success_rate': 0.9
            },
            {
                'pattern_id': 'p2',
                'success_rate': 0.4
            }
        ]
        
        result = self_reflection._update_heuristics(insights, patterns)
        
        assert result is True
        # Should update heuristics for both patterns
        assert mock_adaptive_heuristics.update_heuristic.call_count >= 2


class TestScheduleReflection:
    """Test schedule_reflection method."""
    
    def test_schedule_periodic_reflection(self, self_reflection):
        """Test scheduling periodic reflection."""
        self_reflection.schedule_reflection(
            'periodic',
            interval_operations=100,
            interval_hours=24
        )
        
        # Check schedule was created
        cursor = self_reflection.conn.execute(
            "SELECT * FROM reflection_schedule WHERE trigger_type = 'periodic'"
        )
        row = cursor.fetchone()
        
        assert row is not None
        assert row['interval_operations'] == 100
        assert row['interval_hours'] == 24
        assert row['enabled'] == 1
    
    def test_update_existing_schedule(self, self_reflection):
        """Test updating existing schedule."""
        # Create initial schedule
        self_reflection.schedule_reflection(
            'periodic',
            interval_operations=100,
            interval_hours=24
        )
        
        # Update schedule
        self_reflection.schedule_reflection(
            'periodic',
            interval_operations=200,
            interval_hours=48
        )
        
        # Check schedule was updated
        cursor = self_reflection.conn.execute(
            "SELECT * FROM reflection_schedule WHERE trigger_type = 'periodic'"
        )
        row = cursor.fetchone()
        
        assert row['interval_operations'] == 200
        assert row['interval_hours'] == 48


class TestGetReflections:
    """Test get_reflections method."""
    
    def test_get_all_reflections(
        self,
        self_reflection,
        mock_decision_history,
        mock_pattern_recognizer
    ):
        """Test getting all reflections."""
        # Create some reflections
        mock_decision_history.list_decisions.return_value = [
            {
                'decision_id': 'd1',
                'outcome': 'success',
                'confidence': 0.8,
                'action': 'action1',
                'reasoning': 'reasoning1',
                'time_elapsed': 1.0,
                'resources': {'tokens': 1000}
            }
        ]
        mock_pattern_recognizer.recognize_patterns.return_value = []
        
        self_reflection.perform_reflection('periodic')
        self_reflection.perform_reflection('after_task')
        
        # Get reflections
        reflections = self_reflection.get_reflections(limit=10)
        
        assert len(reflections) == 2
        assert all('reflection_id' in r for r in reflections)
        assert all('insights' in r for r in reflections)
    
    def test_get_reflections_by_trigger_type(
        self,
        self_reflection,
        mock_decision_history,
        mock_pattern_recognizer
    ):
        """Test getting reflections by trigger type."""
        mock_decision_history.list_decisions.return_value = [
            {
                'decision_id': 'd1',
                'outcome': 'success',
                'confidence': 0.8,
                'action': 'action1',
                'reasoning': 'reasoning1',
                'time_elapsed': 1.0,
                'resources': {'tokens': 1000}
            }
        ]
        mock_pattern_recognizer.recognize_patterns.return_value = []
        
        self_reflection.perform_reflection('periodic')
        self_reflection.perform_reflection('after_task')
        self_reflection.perform_reflection('periodic')
        
        # Get periodic reflections only
        periodic_reflections = self_reflection.get_reflections(
            trigger_type='periodic',
            limit=10
        )
        
        assert len(periodic_reflections) == 2
        assert all(r['trigger_type'] == 'periodic' for r in periodic_reflections)


class TestGenerateSummary:
    """Test _generate_summary method."""
    
    def test_generate_summary(self, self_reflection):
        """Test generation of reflection summary."""
        decisions = [
            {'outcome': 'success'},
            {'outcome': 'success'},
            {'outcome': 'failure'}
        ]
        insights = [
            {'type': 'performance', 'category': 'test'},
            {'type': 'pattern', 'category': 'test2'}
        ]
        
        summary = self_reflection._generate_summary(
            decisions,
            insights,
            True
        )
        
        assert isinstance(summary, str)
        assert '3 decisions' in summary
        assert '66.7%' in summary
        assert '2 insights' in summary
        assert 'heuristics updated' in summary


class TestClose:
    """Test close method."""
    
    def test_close_connection(self, self_reflection):
        """Test closing database connection."""
        conn = self_reflection.conn
        self_reflection.close()
        
        # Connection should be closed
        assert self_reflection.conn is None
        # Attempting to use closed connection should fail
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])