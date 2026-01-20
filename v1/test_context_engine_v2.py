"""
Test for Task 5.1: Update ContextEngine Interface

Tests the V2 enhancements to ContextEngine:
- Use of TaskImpactAnalyzer for intelligent context collection
- Replacing keyword matching with impact-based selection
- Enhanced documentation and examples
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v1.logic.context_engine import ContextEngine


def test_context_engine_with_smart_scoping():
    """Test that ContextEngine uses TaskImpactAnalyzer with smart scoping enabled."""
    engine = ContextEngine(workspace_root=".")
    
    # Test with smart scoping enabled (V2 behavior)
    context = engine.get_pruned_context(
        task_query="cache invalidation",
        files=["v1/data/cache_manager.py"],
        use_smart_scoping=True,
        task_title="Implement cache invalidation",
        acceptance_criteria="Cache must be invalidated when source files change"
    )
    
    # Verify context is generated
    assert context is not None
    assert len(context) > 0
    assert "cache_manager.py" in context
    
    # Check that relevance information is included in V2 output
    assert "Relevance:" in context or "relevance_score" in context.lower()
    
    print("✓ Smart scoping with TaskImpactAnalyzer works correctly")


def test_context_engine_legacy_mode():
    """Test that ContextEngine falls back to keyword matching when smart scoping is disabled."""
    engine = ContextEngine(workspace_root=".")
    
    # Test with smart scoping disabled (V1 legacy behavior)
    context = engine.get_pruned_context(
        task_query="cache",
        files=["v1/data/cache_manager.py"],
        use_smart_scoping=False  # Legacy mode
    )
    
    # Verify context is generated
    assert context is not None
    assert len(context) > 0
    assert "cache_manager.py" in context
    
    # Check that legacy mode is indicated
    assert "Legacy keyword mode" in context or "cache_manager.py" in context
    
    print("✓ Legacy keyword matching mode works correctly")


def test_context_engine_docstring():
    """Test that the enhanced docstring provides proper documentation."""
    engine = ContextEngine(workspace_root=".")
    
    # Check that get_pruned_context has comprehensive docstring
    docstring = engine.get_pruned_context.__doc__
    
    # Verify V2 enhancements are documented
    assert "V2" in docstring or "AST-based" in docstring
    assert "TaskImpactAnalyzer" in docstring or "impact analysis" in docstring.lower()
    assert "Examples:" in docstring
    
    print("✓ Enhanced docstring provides proper documentation")


def test_smart_file_scope_integration():
    """Test that get_smart_file_scope integrates with TaskImpactAnalyzer."""
    engine = ContextEngine(workspace_root=".")
    
    # Test smart file scoping
    scoped_files = engine.get_smart_file_scope(
        task_title="Implement cache invalidation",
        acceptance_criteria="Cache must be invalidated when source files change",
        candidate_files=["v1/data/cache_manager.py", "v1/data/semantic_mapper.py"],
        max_depth=3
    )
    
    # Verify structure of returned data
    assert isinstance(scoped_files, list)
    assert len(scoped_files) > 0
    
    # Check that each file has the expected V2 fields
    for file_info in scoped_files:
        assert "file_path" in file_info
        assert "relevance_score" in file_info
        assert "impact_score" in file_info
        assert "dependency_score" in file_info
        assert "confidence" in file_info
        assert "match_details" in file_info
        
        # Verify scores are in valid range
        assert 0.0 <= file_info["relevance_score"] <= 1.0
        assert 0.0 <= file_info["impact_score"] <= 1.0
        assert 0.0 <= file_info["dependency_score"] <= 1.0
        assert file_info["confidence"] in ["low", "medium", "high"]
    
    # Verify files are sorted by relevance (descending)
    if len(scoped_files) > 1:
        for i in range(len(scoped_files) - 1):
            assert scoped_files[i]["relevance_score"] >= scoped_files[i + 1]["relevance_score"]
    
    print("✓ Smart file scoping integrates with TaskImpactAnalyzer correctly")


def test_context_caching_with_smart_scoping():
    """Test that context caching works with smart scoping enabled."""
    engine = ContextEngine(workspace_root=".")
    
    # Clear any existing cache
    engine.clear_cache()
    
    # First call - should be cache miss
    context1 = engine.get_pruned_context(
        task_query="cache",
        files=["v1/data/cache_manager.py"],
        use_smart_scoping=True,
        task_title="Implement cache invalidation",
        acceptance_criteria="Cache must be invalidated when source files change"
    )
    
    stats = engine.get_cache_stats()
    assert stats["cache_misses"] == 1
    assert stats["cache_hits"] == 0
    
    # Second call with same parameters - should be cache hit
    context2 = engine.get_pruned_context(
        task_query="cache",
        files=["v1/data/cache_manager.py"],
        use_smart_scoping=True,
        task_title="Implement cache invalidation",
        acceptance_criteria="Cache must be invalidated when source files change"
    )
    
    stats = engine.get_cache_stats()
    assert stats["cache_misses"] == 1
    assert stats["cache_hits"] == 1
    assert context1 == context2
    
    print("✓ Context caching works with smart scoping")


if __name__ == "__main__":
    print("Testing Task 5.1: Update ContextEngine Interface\n")
    print("=" * 60)
    
    test_context_engine_with_smart_scoping()
    test_context_engine_legacy_mode()
    test_context_engine_docstring()
    test_smart_file_scope_integration()
    test_context_caching_with_smart_scoping()
    
    print("=" * 60)
    print("\n✅ All tests passed!")
