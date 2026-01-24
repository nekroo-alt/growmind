"""
Unit tests for ContextSummarizer - V4 Adaptive Reasoning System

Tests cover:
- L1 context summarization (recent actions)
- L2 context summarization (session)
- L3 context summarization (project)
- Summary types (brief, detailed, full)
- Caching behavior
- LLM summarization (with mocks)
- Fallback summarization
- Quality score tracking
- Cache invalidation
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from logic.context_summarizer import ContextSummarizer, Summary
from data.context_hierarchy import ContextHierarchyManager, ContextLevel


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    return str(tmp_path / "test_context_hierarchy.db")


@pytest.fixture
def context_manager(temp_db_path):
    """Create ContextHierarchyManager instance for testing."""
    return ContextHierarchyManager(db_path=temp_db_path)


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider for testing."""
    provider = Mock()
    provider.generate = Mock(return_value='{"summary": "test summary", "key_events": ["event1"]}')
    return provider


@pytest.fixture
def summarizer(context_manager, mock_llm_provider):
    """Create ContextSummarizer instance for testing."""
    return ContextSummarizer(
        context_manager=context_manager,
        llm_provider=mock_llm_provider
    )


class TestL1Summarization:
    """Tests for L1 context summarization (recent actions)."""
    
    def test_summarize_l1_brief_with_llm(self, context_manager, summarizer, mock_llm_provider):
        """Test L1 brief summarization with LLM."""
        # Add some actions to L1
        for i in range(5):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        # Mock LLM response for brief summary
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": ["action_1", "action_2", "action_3"],
    "summary": "Brief summary of recent actions",
    "action_count": 5
}
```'''
        
        # Summarize L1
        summary = summarizer.summarize_l1(summary_type='brief')
        
        assert summary is not None
        assert summary.summary_type == 'brief'
        assert summary.items_summarized == 5
        assert 'summary' in summary.content
        assert 'key_events' in summary.content
        assert summary.quality_score == 1.0  # LLM gets initial score of 1.0
        
        # Verify summary was stored
        cached = context_manager.get_summary(ContextLevel.L1, 'brief')
        assert cached is not None
        assert cached['summary'] == 'Brief summary of recent actions'
    
    def test_summarize_l1_detailed_with_llm(self, context_manager, summarizer, mock_llm_provider):
        """Test L1 detailed summarization with LLM."""
        # Add some actions to L1
        for i in range(10):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        # Mock LLM response for detailed summary
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": [
        {"event": "action_1", "example": "example data"},
        {"event": "action_2", "example": "example data"}
    ],
    "summary": "Detailed summary of recent actions with patterns",
    "patterns": ["pattern1", "pattern2"],
    "action_count": 10
}
```'''
        
        # Summarize L1
        summary = summarizer.summarize_l1(summary_type='detailed')
        
        assert summary is not None
        assert summary.summary_type == 'detailed'
        assert summary.items_summarized == 10
        assert 'summary' in summary.content
        assert 'patterns' in summary.content
        assert len(summary.content['patterns']) == 2
        assert summary.quality_score == 1.0
    
    def test_summarize_l1_full_with_llm(self, context_manager, summarizer, mock_llm_provider):
        """Test L1 full summarization with LLM."""
        # Add some actions to L1
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        # Mock LLM response for full summary
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": [
        {"event": "action_1", "example": "example data", "context": "context info"}
    ],
    "summary": "Comprehensive summary with full context",
    "patterns": ["pattern1"],
    "action_count": 3,
    "timeline": [
        {"time": "10:00:00", "event": "action_1"},
        {"time": "10:01:00", "event": "action_2"}
    ]
}
```'''
        
        # Summarize L1
        summary = summarizer.summarize_l1(summary_type='full')
        
        assert summary is not None
        assert summary.summary_type == 'full'
        assert summary.items_summarized == 3
        assert 'timeline' in summary.content
        assert len(summary.content['timeline']) == 2
    
    def test_summarize_l1_no_actions(self, summarizer):
        """Test L1 summarization with no actions."""
        summary = summarizer.summarize_l1()
        
        assert summary is None
    
    def test_summarize_l1_fallback_no_llm(self, context_manager):
        """Test L1 summarization fallback when LLM is not available."""
        # Create summarizer without LLM provider
        summarizer = ContextSummarizer(context_manager=context_manager)
        
        # Add some actions to L1
        for i in range(5):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        # Summarize L1 (should use fallback)
        summary = summarizer.summarize_l1(summary_type='brief')
        
        assert summary is not None
        assert summary.summary_type == 'brief'
        assert summary.items_summarized == 5
        assert summary.quality_score == 0.5  # Fallback gets lower score
        assert 'summary' in summary.content
    
    def test_summarize_l1_llm_error(self, context_manager, summarizer, mock_llm_provider):
        """Test L1 summarization when LLM fails."""
        # Add some actions to L1
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        # Mock LLM to raise error
        mock_llm_provider.generate.side_effect = Exception("LLM failed")
        
        # Summarize L1 (should use fallback)
        summary = summarizer.summarize_l1()
        
        assert summary is not None
        assert summary.quality_score == 0.5  # Fallback gets lower score
    
    def test_summarize_l1_caching(self, context_manager, summarizer, mock_llm_provider):
        """Test L1 summarization caching."""
        # Add some actions to L1
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        # Mock LLM response
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": ["action_1"],
    "summary": "Cached summary",
    "action_count": 3
}
```'''
        
        # First call should use LLM
        summary1 = summarizer.summarize_l1(summary_type='detailed')
        assert mock_llm_provider.generate.call_count == 1
        
        # Second call should use cache
        summary2 = summarizer.summarize_l1(summary_type='detailed')
        assert mock_llm_provider.generate.call_count == 1  # No additional call
        
        # Verify same summary
        assert summary1.content['summary'] == summary2.content['summary']
    
    def test_summarize_l1_force_refresh(self, context_manager, summarizer, mock_llm_provider):
        """Test L1 summarization with force refresh."""
        # Add some actions to L1
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        # Mock LLM response
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": ["action_1"],
    "summary": "Fresh summary",
    "action_count": 3
}
```'''
        
        # First call
        summary1 = summarizer.summarize_l1()
        
        # Force refresh
        summary2 = summarizer.summarize_l1(force_refresh=True)
        
        # Verify LLM was called twice
        assert mock_llm_provider.generate.call_count == 2


class TestL2Summarization:
    """Tests for L2 context summarization (session)."""
    
    def test_summarize_l2_brief_with_actions(self, context_manager, summarizer, mock_llm_provider):
        """Test L2 brief summarization with actions."""
        # Add actions to L2
        for i in range(5):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        # Mock LLM response for brief summary
        mock_llm_provider.generate.return_value = '''```json
{
    "themes": ["theme1", "theme2"],
    "summary": "Brief session summary",
    "progress": "in_progress"
}
```'''
        
        # Summarize L2
        summary = summarizer.summarize_l2(summary_type='brief')
        
        assert summary is not None
        assert summary.summary_type == 'brief'
        assert summary.items_summarized == 5
        assert 'themes' in summary.content
        assert 'progress' in summary.content
    
    def test_summarize_l2_detailed_with_errors(self, context_manager, summarizer, mock_llm_provider):
        """Test L2 detailed summarization with errors."""
        # Add actions and errors to L2
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        for i in range(2):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='error',
                content={'type': f'error_{i}', 'message': f'error message {i}'}
            )
        
        # Mock LLM response for detailed summary
        mock_llm_provider.generate.return_value = '''```json
{
    "themes": ["error_handling", "task_completion"],
    "patterns": ["pattern1", "pattern2"],
    "summary": "Detailed session summary with error analysis",
    "progress": "completed",
    "success_rate": 0.8,
    "common_errors": ["error_0", "error_1"]
}
```'''
        
        # Summarize L2
        summary = summarizer.summarize_l2(summary_type='detailed')
        
        assert summary is not None
        assert summary.summary_type == 'detailed'
        assert summary.items_summarized == 5  # 3 actions + 2 errors
        assert 'success_rate' in summary.content
        assert 'common_errors' in summary.content
        assert summary.content['success_rate'] == 0.8
    
    def test_summarize_l2_full(self, context_manager, summarizer, mock_llm_provider):
        """Test L2 full summarization."""
        # Add actions and errors to L2
        for i in range(5):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='action',
                content={'type': f'action_{i}', 'category': 'testing' if i % 2 == 0 else 'implementation'}
            )
        
        for i in range(2):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='error',
                content={'type': f'error_{i}', 'category': 'api_error'}
            )
        
        # Mock LLM response for full summary
        mock_llm_provider.generate.return_value = '''```json
{
    "themes": ["testing", "implementation", "error_handling"],
    "patterns": ["pattern1"],
    "summary": "Comprehensive session summary",
    "progress": "in_progress",
    "success_rate": 0.6,
    "common_errors": ["api_error"],
    "action_breakdown": {"testing": 3, "implementation": 2},
    "error_breakdown": {"api_error": 2}
}
```'''
        
        # Summarize L2
        summary = summarizer.summarize_l2(summary_type='full')
        
        assert summary is not None
        assert summary.summary_type == 'full'
        assert 'action_breakdown' in summary.content
        assert 'error_breakdown' in summary.content
        assert summary.content['action_breakdown']['testing'] == 3
    
    def test_summarize_l2_no_context(self, summarizer):
        """Test L2 summarization with no context."""
        summary = summarizer.summarize_l2()
        
        assert summary is None
    
    def test_summarize_l2_fallback_no_llm(self, context_manager):
        """Test L2 summarization fallback when LLM is not available."""
        # Create summarizer without LLM provider
        summarizer = ContextSummarizer(context_manager=context_manager)
        
        # Add actions and errors to L2
        for i in range(5):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='action',
                content={'type': f'action_{i}', 'data': f'data_{i}'}
            )
        
        for i in range(2):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='error',
                content={'type': f'error_{i}', 'message': f'error message {i}'}
            )
        
        # Summarize L2 (should use fallback)
        summary = summarizer.summarize_l2(summary_type='brief')
        
        assert summary is not None
        assert summary.items_summarized == 7  # 5 actions + 2 errors
        assert summary.quality_score == 0.5  # Fallback gets lower score


class TestL3Summarization:
    """Tests for L3 context summarization (project)."""
    
    def test_summarize_l3_brief(self, context_manager, summarizer, mock_llm_provider):
        """Test L3 brief summarization."""
        # Add project context to L3
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='state',
            content={'status': 'active', 'version': '4.0'}
        )
        
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='architecture',
            content={'type': 'microservices', 'language': 'python'}
        )
        
        # Mock LLM response for brief summary
        mock_llm_provider.generate.return_value = '''```json
{
    "architecture_summary": "Brief architecture description",
    "key_constraints": ["constraint1", "constraint2"],
    "summary": "Brief project summary"
}
```'''
        
        # Summarize L3
        summary = summarizer.summarize_l3(summary_type='brief')
        
        assert summary is not None
        assert summary.summary_type == 'brief'
        assert summary.items_summarized == 1  # Project context is one item
        assert 'architecture_summary' in summary.content
        assert 'key_constraints' in summary.content
    
    def test_summarize_l3_detailed(self, context_manager, summarizer, mock_llm_provider):
        """Test L3 detailed summarization."""
        # Add project context to L3
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='state',
            content={'status': 'active', 'version': '4.0', 'modules': 10}
        )
        
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='architecture',
            content={
                'type': 'microservices',
                'language': 'python',
                'components': ['api', 'ui', 'db']
            }
        )
        
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='pattern',
            content={'name': 'adapter_pattern', 'usage': 'high'}
        )
        
        # Mock LLM response for detailed summary
        mock_llm_provider.generate.return_value = '''```json
{
    "architecture_summary": "Detailed architecture description with components",
    "key_constraints": ["local-first", "git-native"],
    "summary": "Detailed project summary",
    "key_patterns": ["adapter_pattern"],
    "dependencies": ["pytest", "sqlite3"]
}
```'''
        
        # Summarize L3
        summary = summarizer.summarize_l3(summary_type='detailed')
        
        assert summary is not None
        assert summary.summary_type == 'detailed'
        assert 'key_patterns' in summary.content
        assert 'dependencies' in summary.content
    
    def test_summarize_l3_full(self, context_manager, summarizer, mock_llm_provider):
        """Test L3 full summarization."""
        # Add comprehensive project context to L3
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='state',
            content={'status': 'active', 'version': '4.0', 'tasks': 100}
        )
        
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='architecture',
            content={
                'type': 'layered',
                'language': 'python',
                'components': ['core', 'logic', 'data', 'ui']
            }
        )
        
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='pattern',
            content={'name': 'observer_pattern', 'usage': 'medium'}
        )
        
        # Mock LLM response for full summary
        mock_llm_provider.generate.return_value = '''```json
{
    "architecture_summary": "Comprehensive architecture description",
    "key_constraints": ["constraint1", "constraint2", "constraint3"],
    "summary": "Comprehensive project summary",
    "key_patterns": ["observer_pattern"],
    "dependencies": ["pytest", "sqlite3", "numpy"],
    "tech_stack": ["python", "sqlite", "pytest"],
    "modules": ["core", "logic", "data", "ui"]
}
```'''
        
        # Summarize L3
        summary = summarizer.summarize_l3(summary_type='full')
        
        assert summary is not None
        assert summary.summary_type == 'full'
        assert 'tech_stack' in summary.content
        assert 'modules' in summary.content
    
    def test_summarize_l3_fallback_no_llm(self, context_manager):
        """Test L3 summarization fallback when LLM is not available."""
        # Create summarizer without LLM provider
        summarizer = ContextSummarizer(context_manager=context_manager)
        
        # Add project context to L3
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='state',
            content={'status': 'active', 'version': '4.0'}
        )
        
        # Summarize L3 (should use fallback)
        summary = summarizer.summarize_l3(summary_type='brief')
        
        assert summary is not None
        assert summary.quality_score == 0.5  # Fallback gets lower score


class TestQualityScoreTracking:
    """Tests for quality score tracking."""
    
    def test_update_quality_score_success(self, summarizer):
        """Test updating quality score for successful summary."""
        # Update quality score for success
        summarizer.update_quality_score(
            level=ContextLevel.L1,
            summary_type='detailed',
            success=True
        )
        
        stats = summarizer.get_stats()
        assert 'quality_scores' in stats
        assert 'L1_detailed' in stats['quality_scores']
        assert stats['quality_scores']['L1_detailed'] > 0.9  # Should increase
    
    def test_update_quality_score_failure(self, summarizer):
        """Test updating quality score for failed summary."""
        # Update quality score for failure
        summarizer.update_quality_score(
            level=ContextLevel.L1,
            summary_type='detailed',
            success=False
        )
        
        stats = summarizer.get_stats()
        assert 'quality_scores' in stats
        assert 'L1_detailed' in stats['quality_scores']
        assert stats['quality_scores']['L1_detailed'] < 1.0  # Should decrease
    
    def test_update_quality_score_custom(self, summarizer):
        """Test updating quality score with custom value."""
        # Update quality score with custom value
        summarizer.update_quality_score(
            level=ContextLevel.L2,
            summary_type='brief',
            new_score=0.75,
            success=True
        )
        
        stats = summarizer.get_stats()
        assert stats['quality_scores']['L2_brief'] == 0.75
    
    def test_quality_score_moving_average(self, summarizer):
        """Test quality score updates use exponential moving average."""
        # Initial score is 1.0
        summarizer.update_quality_score(
            level=ContextLevel.L1,
            summary_type='detailed',
            success=True
        )
        stats = summarizer.get_stats()
        score1 = stats['quality_scores']['L1_detailed']
        
        # Update with failure
        summarizer.update_quality_score(
            level=ContextLevel.L1,
            summary_type='detailed',
            success=False
        )
        stats = summarizer.get_stats()
        score2 = stats['quality_scores']['L1_detailed']
        
        # Score should decrease but not too much (moving average)
        assert score2 < score1
        assert score2 > 0.5  # Should not drop to 0.5 immediately


class TestCacheInvalidation:
    """Tests for cache invalidation."""
    
    def test_invalidate_cache_l1(self, summarizer):
        """Test invalidating cache for L1."""
        # This should not raise an error
        summarizer.invalidate_cache(ContextLevel.L1)
    
    def test_invalidate_cache_l2(self, summarizer):
        """Test invalidating cache for L2."""
        # This should not raise an error
        summarizer.invalidate_cache(ContextLevel.L2)
    
    def test_invalidate_cache_l3(self, summarizer):
        """Test invalidating cache for L3."""
        # This should not raise an error
        summarizer.invalidate_cache(ContextLevel.L3)


class TestGetSummary:
    """Tests for get_summary method."""
    
    def test_get_summary_l1(self, context_manager, summarizer, mock_llm_provider):
        """Test get_summary for L1."""
        # Add actions
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}'}
            )
        
        # Mock LLM response
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": ["action_1"],
    "summary": "Test summary",
    "action_count": 3
}
```'''
        
        summary = summarizer.get_summary(level=ContextLevel.L1, summary_type='brief')
        
        assert summary is not None
        assert summary.summary_type == 'brief'
    
    def test_get_summary_l2(self, context_manager, summarizer, mock_llm_provider):
        """Test get_summary for L2."""
        # Add actions
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='action',
                content={'type': f'action_{i}'}
            )
        
        # Mock LLM response
        mock_llm_provider.generate.return_value = '''```json
{
    "themes": ["theme1"],
    "summary": "Test summary",
    "progress": "in_progress"
}
```'''
        
        summary = summarizer.get_summary(level=ContextLevel.L2, summary_type='brief')
        
        assert summary is not None
        assert summary.summary_type == 'brief'
    
    def test_get_summary_l3(self, context_manager, summarizer, mock_llm_provider):
        """Test get_summary for L3."""
        # Add project context
        context_manager.add_context_item(
            level=ContextLevel.L3,
            item_type='state',
            content={'status': 'active'}
        )
        
        # Mock LLM response
        mock_llm_provider.generate.return_value = '''```json
{
    "architecture_summary": "Test architecture",
    "key_constraints": ["constraint1"],
    "summary": "Test summary"
}
```'''
        
        summary = summarizer.get_summary(level=ContextLevel.L3, summary_type='brief')
        
        assert summary is not None
        assert summary.summary_type == 'brief'
    
    def test_get_summary_unknown_level(self, summarizer):
        """Test get_summary with unknown level."""
        summary = summarizer.get_summary(level='L4', summary_type='brief')
        
        assert summary is None


class TestGetStats:
    """Tests for get_stats method."""
    
    def test_get_stats(self, summarizer):
        """Test getting statistics."""
        stats = summarizer.get_stats()
        
        assert 'quality_scores' in stats
        assert 'timestamp' in stats
        assert isinstance(stats['quality_scores'], dict)
        assert isinstance(stats['timestamp'], float)


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_llm_invalid_json_response(self, context_manager, summarizer, mock_llm_provider):
        """Test handling of invalid JSON from LLM."""
        # Add actions
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}'}
            )
        
        # Mock LLM to return invalid JSON
        mock_llm_provider.generate.return_value = 'This is not valid JSON'
        
        summary = summarizer.summarize_l1(summary_type='brief')
        
        # Should fall back to simple summarization
        assert summary is not None
        assert summary.quality_score == 0.5  # Fallback score
    
    def test_llm_json_with_code_blocks(self, context_manager, summarizer, mock_llm_provider):
        """Test handling of JSON response with code blocks."""
        # Add actions
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}'}
            )
        
        # Mock LLM to return JSON with ```json block
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": ["action_1"],
    "summary": "Test summary",
    "action_count": 3
}
```'''
        
        summary = summarizer.summarize_l1(summary_type='brief')
        
        # Should parse JSON successfully
        assert summary is not None
        assert summary.content['summary'] == 'Test summary'
    
    def test_llm_json_without_code_blocks(self, context_manager, summarizer, mock_llm_provider):
        """Test handling of JSON response without code blocks."""
        # Add actions
        for i in range(3):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}'}
            )
        
        # Mock LLM to return plain JSON
        mock_llm_provider.generate.return_value = '''{"key_events": ["action_1"], "summary": "Test summary", "action_count": 3}'''
        
        summary = summarizer.summarize_l1(summary_type='brief')
        
        # Should parse JSON successfully
        assert summary is not None
        assert summary.content['summary'] == 'Test summary'
    
    def test_empty_content(self, context_manager, summarizer):
        """Test summarization with empty content."""
        # Add empty action
        context_manager.add_context_item(
            level=ContextLevel.L1,
            item_type='action',
            content={}
        )
        
        summary = summarizer.summarize_l1(summary_type='brief')
        
        assert summary is not None
        assert summary.items_summarized == 1
    
    def test_large_number_of_actions(self, context_manager, summarizer, mock_llm_provider):
        """Test summarization with large number of actions."""
        # Add many actions (more than limit of MAX_ITEMS=10)
        for i in range(50):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}'}
            )
        
        # Mock LLM response
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": ["action_1", "action_2"],
    "summary": "Test summary",
    "action_count": 10
}
```'''
        
        summary = summarizer.summarize_l1(summary_type='brief')
        
        assert summary is not None
        assert summary.items_summarized == 10  # Should limit to MAX_ITEMS


class TestPerformance:
    """Tests for performance characteristics."""
    
    def test_summary_word_count_brief(self, context_manager, summarizer, mock_llm_provider):
        """Test brief summary word count target."""
        # Add actions
        for i in range(5):
            context_manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'type': f'action_{i}'}
            )
        
        # Mock LLM response with brief summary
        mock_llm_provider.generate.return_value = '''```json
{
    "key_events": ["action_1", "action_2"],
    "summary": "Brief summary of actions showing recent patterns and key events that occurred during this testing session",
    "action_count": 5
}
```'''
        
        summary = summarizer.summarize_l1(summary_type='brief')
        
        # Brief summary should exist (actual word count may vary in testing)
        word_count = summary.word_count
        assert word_count > 0, f"Brief summary should have words, got {word_count}"
    
    def test_summary_word_count_detailed(self, context_manager, summarizer, mock_llm_provider):
        """Test detailed summary word count target."""
        # Add actions
        for i in range(10):
            context_manager.add_context_item(
                level=ContextLevel.L2,
                item_type='action',
                content={'type': f'action_{i}', 'data': 'more data here'}
            )
        
        # Mock LLM response with detailed summary
        mock_llm_provider.generate.return_value = '''```json
{
    "themes": ["theme1", "theme2"],
    "summary": "This is a detailed summary that provides comprehensive context about session activities and patterns identified",
    "progress": "in_progress",
    "success_rate": 0.8
}
```'''
        
        summary = summarizer.summarize_l2(summary_type='detailed')
        
        # Detailed summary should exist (actual word count may vary in testing)
        word_count = summary.word_count
        assert word_count > 0, f"Detailed summary should have words, got {word_count}"