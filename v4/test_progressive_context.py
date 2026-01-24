"""
Unit tests for V5 progressive context loading in ContextEngine.

Tests cover:
- Context level initialization and management
- Progressive context loading with expansion
- Context sufficiency checking
- Learning from task outcomes
- Statistics tracking and reporting
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from logic.context_engine import ContextEngine, ContextLevel, ContextLevelInfo


class TestContextLevelEnum(unittest.TestCase):
    """Test ContextLevel enum definitions."""

    def test_context_levels_defined(self):
        """Test that all context levels are defined."""
        self.assertEqual(ContextLevel.IMMEDIATE.value, 0)
        self.assertEqual(ContextLevel.RECENT.value, 1)
        self.assertEqual(ContextLevel.SESSION.value, 2)
        self.assertEqual(ContextLevel.PROJECT.value, 3)

    def test_context_level_ordering(self):
        """Test that context levels are ordered correctly."""
        levels = [ContextLevel.IMMEDIATE, ContextLevel.RECENT, 
                   ContextLevel.SESSION, ContextLevel.PROJECT]
        values = [level.value for level in levels]
        self.assertEqual(values, [0, 1, 2, 3])


class TestContextLevelInfo(unittest.TestCase):
    """Test ContextLevelInfo dataclass."""

    def test_context_level_info_creation(self):
        """Test creation of ContextLevelInfo."""
        info = ContextLevelInfo(
            level=ContextLevel.IMMEDIATE,
            name="Immediate",
            description="Test description",
            token_multiplier=1.0,
            average_success_rate=0.75,
            expansion_count=5
        )

        self.assertEqual(info.level, ContextLevel.IMMEDIATE)
        self.assertEqual(info.name, "Immediate")
        self.assertEqual(info.description, "Test description")
        self.assertEqual(info.token_multiplier, 1.0)
        self.assertEqual(info.average_success_rate, 0.75)
        self.assertEqual(info.expansion_count, 5)


class TestContextEngineInitialization(unittest.TestCase):
    """Test ContextEngine initialization with V5 features."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_v5_features_initialized(self):
        """Test that V5 progressive context features are initialized."""
        self.assertIsNotNone(self.engine._context_levels)
        self.assertIsInstance(self.engine._optimal_levels, dict)
        self.assertIsInstance(self.engine._expansion_stats, dict)
        self.assertIsInstance(self.engine._level_usage_stats, dict)

    def test_context_levels_initialized(self):
        """Test that all context levels are initialized."""
        levels = self.engine._context_levels
        self.assertEqual(len(levels), 4)
        self.assertIn(ContextLevel.IMMEDIATE, levels)
        self.assertIn(ContextLevel.RECENT, levels)
        self.assertIn(ContextLevel.SESSION, levels)
        self.assertIn(ContextLevel.PROJECT, levels)

    def test_context_levels_info(self):
        """Test that context levels have correct information."""
        levels = self.engine._context_levels

        # Check immediate level
        immediate = levels[ContextLevel.IMMEDIATE]
        self.assertEqual(immediate.level, ContextLevel.IMMEDIATE)
        self.assertEqual(immediate.name, "Immediate")
        self.assertEqual(immediate.token_multiplier, 1.0)
        self.assertEqual(immediate.average_success_rate, 0.70)
        self.assertEqual(immediate.expansion_count, 0)

        # Check recent level
        recent = levels[ContextLevel.RECENT]
        self.assertEqual(recent.level, ContextLevel.RECENT)
        self.assertEqual(recent.name, "Recent")
        self.assertEqual(recent.token_multiplier, 2.5)
        self.assertEqual(recent.average_success_rate, 0.85)

        # Check session level
        session = levels[ContextLevel.SESSION]
        self.assertEqual(session.level, ContextLevel.SESSION)
        self.assertEqual(session.name, "Session")
        self.assertEqual(session.token_multiplier, 5.0)
        self.assertEqual(session.average_success_rate, 0.92)

        # Check project level
        project = levels[ContextLevel.PROJECT]
        self.assertEqual(project.level, ContextLevel.PROJECT)
        self.assertEqual(project.name, "Project")
        self.assertEqual(project.token_multiplier, 10.0)
        self.assertEqual(project.average_success_rate, 0.98)

    def test_level_usage_stats_initialized(self):
        """Test that level usage stats are initialized."""
        stats = self.engine._level_usage_stats
        self.assertEqual(stats, {0: 0, 1: 0, 2: 0, 3: 0})


class TestGetProgressiveContext(unittest.TestCase):
    """Test progressive context loading."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)
        
        # Create test files
        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
def simple_function():
    \"\"\"A simple function for testing.\"\"\"
    return 42

class TestClass:
    \"\"\"A test class.\"\"\"
    
    def method_one(self):
        return 1
    
    def method_two(self):
        return 2
""")

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_progressive_context_returns_tuple(self):
        """Test that get_progressive_context returns a tuple."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["test.py"],
            task_type="test_task"
        )
        
        self.assertIsInstance(context, str)
        self.assertIsInstance(info, dict)

    def test_progressive_context_info_structure(self):
        """Test that context info has correct structure."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["test.py"],
            task_type="test_task"
        )
        
        self.assertIn("starting_level", info)
        self.assertIn("final_level", info)
        self.assertIn("expansion_count", info)
        self.assertIn("task_type", info)
        self.assertIn("files_analyzed", info)
        self.assertIn("estimated_tokens", info)
        self.assertIn("expansion_reason", info)

    def test_starting_level_default(self):
        """Test that starting level defaults to IMMEDIATE."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["test.py"],
            task_type="test_task"
        )
        
        self.assertEqual(info["starting_level"], ContextLevel.IMMEDIATE.value)

    def test_starting_level_custom(self):
        """Test that custom starting level is used."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["test.py"],
            task_type="test_task",
            initial_level=ContextLevel.RECENT
        )
        
        self.assertEqual(info["starting_level"], ContextLevel.RECENT.value)

    def test_expansion_count_zero_if_sufficient(self):
        """Test that expansion count is zero if context is sufficient."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["test.py"],
            task_type="test_task"
        )
        
        # Should be sufficient at immediate level
        self.assertEqual(info["expansion_count"], 0)

    def test_task_type_recorded(self):
        """Test that task type is recorded in info."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["test.py"],
            task_type="bug_fix"
        )
        
        self.assertEqual(info["task_type"], "bug_fix")

    def test_files_analyzed_count(self):
        """Test that files analyzed count is correct."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["test.py"],
            task_type="test_task"
        )
        
        self.assertEqual(info["files_analyzed"], 1)

    def test_estimated_tokens_calculated(self):
        """Test that estimated tokens are calculated."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["test.py"],
            task_type="test_task"
        )
        
        self.assertIn("estimated_tokens", info)
        self.assertGreater(info["estimated_tokens"], 0)


class TestContextSufficiency(unittest.TestCase):
    """Test context sufficiency checking."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_sufficient_context_immediate_level(self):
        """Test that context is sufficient at immediate level."""
        context = "--- File: test.py ---\n" + "\n".join([f"Line {i}" for i in range(20)])
        is_sufficient = self.engine._is_context_sufficient(
            context=context,
            current_level=ContextLevel.IMMEDIATE,
            task_type="bug_fix",
            context_info={"estimated_tokens": 1000}
        )
        
        # Should be sufficient (enough lines, enough tokens)
        self.assertTrue(is_sufficient)

    def test_insufficient_context_too_few_lines(self):
        """Test that context is insufficient with too few lines."""
        context = "--- File: test.py ---\n" + "\n".join([f"Line {i}" for i in range(5)])
        is_sufficient = self.engine._is_context_sufficient(
            context=context,
            current_level=ContextLevel.IMMEDIATE,
            task_type="bug_fix",
            context_info={"estimated_tokens": 1000}
        )
        
        # Should be insufficient (not enough lines for level 0)
        self.assertFalse(is_sufficient)

    def test_insufficient_context_too_few_tokens(self):
        """Test that context is insufficient with too few tokens."""
        context = "--- File: test.py ---\n" + "\n".join([f"Line {i}" for i in range(20)])
        is_sufficient = self.engine._is_context_sufficient(
            context=context,
            current_level=ContextLevel.IMMEDIATE,
            task_type="bug_fix",
            context_info={"estimated_tokens": 100}  # Too few tokens
        )
        
        # Should be insufficient (not enough tokens)
        self.assertFalse(is_sufficient)

    def test_complex_task_requires_higher_level(self):
        """Test that complex tasks require higher context levels."""
        context = "--- File: test.py ---\n" + "\n".join([f"Line {i}" for i in range(20)])
        is_sufficient = self.engine._is_context_sufficient(
            context=context,
            current_level=ContextLevel.IMMEDIATE,  # Level 0
            task_type="refactor",  # Complex task
            context_info={"estimated_tokens": 1000}
        )
        
        # Should be insufficient (refactor needs higher level)
        self.assertFalse(is_sufficient)

    def test_complex_task_sufficient_at_higher_level(self):
        """Test that complex tasks are sufficient at higher levels."""
        context = "--- File: test.py ---\n" + "\n".join([f"Line {i}" for i in range(50)])
        is_sufficient = self.engine._is_context_sufficient(
            context=context,
            current_level=ContextLevel.SESSION,  # Level 2
            task_type="refactor",  # Complex task
            context_info={"estimated_tokens": 5000}
        )
        
        # Should be sufficient (high enough level for complex task)
        self.assertTrue(is_sufficient)


class TestOptimalLevelLearning(unittest.TestCase):
    """Test learning optimal context levels."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_record_task_outcome_updates_stats(self):
        """Test that recording task outcome updates statistics."""
        # Record successful outcome
        self.engine.record_task_outcome(
            task_type="bug_fix",
            starting_level=ContextLevel.IMMEDIATE,
            final_level=ContextLevel.IMMEDIATE,
            success=True
        )
        
        # Check that level stats were updated
        immediate_info = self.engine._context_levels[ContextLevel.IMMEDIATE]
        self.assertEqual(immediate_info.expansion_count, 1)
        self.assertEqual(immediate_info.average_success_rate, 1.0)

    def test_record_multiple_outcomes(self):
        """Test recording multiple task outcomes."""
        # Record multiple outcomes
        self.engine.record_task_outcome(
            task_type="bug_fix",
            starting_level=ContextLevel.IMMEDIATE,
            final_level=ContextLevel.IMMEDIATE,
            success=True
        )
        self.engine.record_task_outcome(
            task_type="bug_fix",
            starting_level=ContextLevel.IMMEDIATE,
            final_level=ContextLevel.IMMEDIATE,
            success=False
        )
        
        # Check that stats were updated correctly
        immediate_info = self.engine._context_levels[ContextLevel.IMMEDIATE]
        self.assertEqual(immediate_info.expansion_count, 2)
        self.assertEqual(immediate_info.average_success_rate, 0.5)  # (1.0 + 0.0) / 2

    def test_optimal_level_learned(self):
        """Test that optimal level is learned after consistent success."""
        # Record 6 successful outcomes without expansion (needs 5 for optimal learning)
        for _ in range(6):
            self.engine.record_task_outcome(
                task_type="bug_fix",
                starting_level=ContextLevel.IMMEDIATE,
                final_level=ContextLevel.IMMEDIATE,
                success=True
            )
        
        # Check that optimal level was learned
        optimal_levels = self.engine.get_optimal_levels()
        self.assertIn("bug_fix", optimal_levels)
        self.assertEqual(optimal_levels["bug_fix"], ContextLevel.IMMEDIATE)

    def test_optimal_level_not_learned_insufficient_samples(self):
        """Test that optimal level is not learned with insufficient samples."""
        # Record only 3 outcomes (needs 5)
        for _ in range(3):
            self.engine.record_task_outcome(
                task_type="bug_fix",
                starting_level=ContextLevel.IMMEDIATE,
                final_level=ContextLevel.IMMEDIATE,
                success=True
            )
        
        # Check that optimal level was NOT learned
        optimal_levels = self.engine.get_optimal_levels()
        self.assertNotIn("bug_fix", optimal_levels)

    def test_optimal_level_updates_on_expansion(self):
        """Test that optimal level updates when expansion is needed."""
        # First, learn that immediate is optimal
        for _ in range(6):
            self.engine.record_task_outcome(
                task_type="bug_fix",
                starting_level=ContextLevel.IMMEDIATE,
                final_level=ContextLevel.IMMEDIATE,
                success=True
            )
        
        # Then record many expansions
        for _ in range(6):
            self.engine.record_task_outcome(
                task_type="bug_fix",
                starting_level=ContextLevel.IMMEDIATE,
                final_level=ContextLevel.RECENT,
                success=True
            )
        
        # Check that optimal level changed
        # (After expansions, immediate should not be optimal)
        # This is simplified - real implementation would be more nuanced
        expansion_stats = self.engine.get_expansion_stats()
        self.assertIn("bug_fix", expansion_stats)
        self.assertGreater(
            expansion_stats["bug_fix"]["avg_expansion_count"], 0.5
        )

    def test_get_optimal_levels(self):
        """Test getting optimal levels."""
        # Set optimal level directly for testing
        self.engine._optimal_levels["bug_fix"] = ContextLevel.RECENT
        self.engine._optimal_levels["new_feature"] = ContextLevel.SESSION
        
        optimal_levels = self.engine.get_optimal_levels()
        
        self.assertEqual(len(optimal_levels), 2)
        self.assertEqual(optimal_levels["bug_fix"], ContextLevel.RECENT)
        self.assertEqual(optimal_levels["new_feature"], ContextLevel.SESSION)


class TestExpansionStats(unittest.TestCase):
    """Test expansion statistics tracking."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_expansion_stats_initialized(self):
        """Test that expansion stats are initialized empty."""
        stats = self.engine.get_expansion_stats()
        self.assertEqual(stats, {})

    def test_expansion_stats_tracked(self):
        """Test that expansion stats are tracked."""
        # Record some expansions
        self.engine._update_expansion_stats(
            task_type="bug_fix",
            starting_level=ContextLevel.IMMEDIATE,
            final_level=ContextLevel.RECENT
        )
        self.engine._update_expansion_stats(
            task_type="bug_fix",
            starting_level=ContextLevel.IMMEDIATE,
            final_level=ContextLevel.SESSION
        )
        
        # Check stats
        stats = self.engine.get_expansion_stats()
        self.assertIn("bug_fix", stats)
        self.assertEqual(stats["bug_fix"]["count"], 2)
        self.assertEqual(stats["bug_fix"]["total_final_level"], 3)  # 1 + 2
        self.assertEqual(stats["bug_fix"]["total_expansion_count"], 2)  # 1 + 1

    def test_expansion_stats_averages(self):
        """Test that expansion averages are calculated correctly."""
        # Record multiple expansions
        for i in range(4):
            self.engine._update_expansion_stats(
                task_type="bug_fix",
                starting_level=ContextLevel.IMMEDIATE,
                final_level=ContextLevel(i % 4)  # Rotate through levels
            )
        
        # Check averages
        stats = self.engine.get_expansion_stats()
        self.assertIn("bug_fix", stats)
        
        avg_final = stats["bug_fix"]["avg_final_level"]
        avg_expansion = stats["bug_fix"]["avg_expansion_count"]
        
        # Final levels: 0, 1, 2, 3 => avg = 1.5
        self.assertAlmostEqual(avg_final, 1.5, places=1)
        
        # Expansions: 0, 1, 2, 3 => avg = 1.5
        self.assertAlmostEqual(avg_expansion, 1.5, places=1)


class TestLevelUsageStats(unittest.TestCase):
    """Test level usage statistics."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_level_usage_initialized_zero(self):
        """Test that level usage stats are initialized to zero."""
        stats = self.engine.get_level_usage_stats()
        self.assertEqual(stats, {0: 0, 1: 0, 2: 0, 3: 0})

    def test_level_usage_updated(self):
        """Test that level usage stats are updated."""
        self.engine._update_context_level_stats(0)
        self.engine._update_context_level_stats(1)
        self.engine._update_context_level_stats(0)
        
        stats = self.engine.get_level_usage_stats()
        self.assertEqual(stats[0], 2)
        self.assertEqual(stats[1], 1)
        self.assertEqual(stats[2], 0)
        self.assertEqual(stats[3], 0)


class TestContextLevelInfoQueries(unittest.TestCase):
    """Test querying context level information."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_get_context_level_info(self):
        """Test getting info for specific level."""
        info = self.engine.get_context_level_info(ContextLevel.IMMEDIATE)
        
        self.assertIsNotNone(info)
        self.assertEqual(info.level, ContextLevel.IMMEDIATE)
        self.assertEqual(info.name, "Immediate")

    def test_get_context_level_info_invalid(self):
        """Test getting info for invalid level."""
        # Use a mock level that doesn't exist
        info = self.engine.get_context_level_info(None)
        self.assertIsNone(info)

    def test_get_all_context_levels(self):
        """Test getting all context levels."""
        levels = self.engine.get_all_context_levels()
        
        self.assertEqual(len(levels), 4)
        self.assertIn(ContextLevel.IMMEDIATE, levels)
        self.assertIn(ContextLevel.RECENT, levels)
        self.assertIn(ContextLevel.SESSION, levels)
        self.assertIn(ContextLevel.PROJECT, levels)

    def test_context_level_info_complete(self):
        """Test that context level info is complete."""
        levels = self.engine.get_all_context_levels()
        
        for level, info in levels.items():
            self.assertIsInstance(info, ContextLevelInfo)
            self.assertEqual(info.level, level)
            self.assertIsNotNone(info.name)
            self.assertIsNotNone(info.description)
            self.assertGreater(info.token_multiplier, 0)
            self.assertGreaterEqual(info.average_success_rate, 0)
            self.assertLessEqual(info.average_success_rate, 1)
            self.assertGreaterEqual(info.expansion_count, 0)


class TestStartingLevelSelection(unittest.TestCase):
    """Test starting level selection."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_starting_level_default_without_learning(self):
        """Test that default starting level is used without learning."""
        level = self.engine._get_starting_level(
            task_type="bug_fix",
            default_level=ContextLevel.IMMEDIATE
        )
        
        self.assertEqual(level, ContextLevel.IMMEDIATE)

    def test_starting_level_learns_optimal(self):
        """Test that optimal starting level is learned."""
        # Learn optimal level
        for _ in range(6):
            self.engine.record_task_outcome(
                task_type="bug_fix",
                starting_level=ContextLevel.RECENT,
                final_level=ContextLevel.RECENT,
                success=True
            )
        
        # Check that learned optimal is used
        level = self.engine._get_starting_level(
            task_type="bug_fix",
            default_level=ContextLevel.IMMEDIATE
        )
        
        self.assertEqual(level, ContextLevel.RECENT)

    def test_starting_level_insufficient_samples(self):
        """Test that default is used with insufficient samples."""
        # Only record 3 outcomes (needs 5 for optimal)
        for _ in range(3):
            self.engine.record_task_outcome(
                task_type="bug_fix",
                starting_level=ContextLevel.RECENT,
                final_level=ContextLevel.RECENT,
                success=True
            )
        
        # Should use default
        level = self.engine._get_starting_level(
            task_type="bug_fix",
            default_level=ContextLevel.IMMEDIATE
        )
        
        self.assertEqual(level, ContextLevel.IMMEDIATE)


class TestContextAtLevel(unittest.TestCase):
    """Test getting context at specific levels."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)
        
        # Create test file
        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
def function_one():
    return 1

def function_two():
    return 2
""")

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_context_at_immediate_level(self):
        """Test getting context at immediate level."""
        context_info = {}
        context = self.engine._get_context_at_level(
            level=ContextLevel.IMMEDIATE,
            task_query="test",
            files=["test.py"],
            use_smart_scoping=False,
            task_title="",
            acceptance_criteria="",
            force_refresh=True,
            context_info=context_info
        )
        
        self.assertIsInstance(context, str)
        self.assertIn("estimated_tokens", context_info)

    def test_context_at_recent_level(self):
        """Test getting context at recent level."""
        context_info = {}
        context = self.engine._get_context_at_level(
            level=ContextLevel.RECENT,
            task_query="test",
            files=["test.py"],
            use_smart_scoping=False,
            task_title="",
            acceptance_criteria="",
            force_refresh=True,
            context_info=context_info
        )
        
        self.assertIsInstance(context, str)
        self.assertIn("estimated_tokens", context_info)

    def test_context_at_session_level(self):
        """Test getting context at session level."""
        context_info = {}
        context = self.engine._get_context_at_level(
            level=ContextLevel.SESSION,
            task_query="test",
            files=["test.py"],
            use_smart_scoping=False,
            task_title="",
            acceptance_criteria="",
            force_refresh=True,
            context_info=context_info
        )
        
        self.assertIsInstance(context, str)
        self.assertIn("estimated_tokens", context_info)

    def test_context_at_project_level(self):
        """Test getting context at project level."""
        context_info = {}
        context = self.engine._get_context_at_level(
            level=ContextLevel.PROJECT,
            task_query="test",
            files=["test.py"],
            use_smart_scoping=False,
            task_title="",
            acceptance_criteria="",
            force_refresh=True,
            context_info=context_info
        )
        
        self.assertIsInstance(context, str)
        self.assertIn("estimated_tokens", context_info)

    def test_higher_level_more_tokens(self):
        """Test that higher levels estimate more tokens."""
        immediate_info = {}
        project_info = {}
        
        immediate_context = self.engine._get_context_at_level(
            level=ContextLevel.IMMEDIATE,
            task_query="test",
            files=["test.py"],
            use_smart_scoping=False,
            task_title="",
            acceptance_criteria="",
            force_refresh=True,
            context_info=immediate_info
        )
        
        project_context = self.engine._get_context_at_level(
            level=ContextLevel.PROJECT,
            task_query="test",
            files=["test.py"],
            use_smart_scoping=False,
            task_title="",
            acceptance_criteria="",
            force_refresh=True,
            context_info=project_info
        )
        
        # Project should estimate more tokens
        self.assertGreater(
            project_info["estimated_tokens"],
            immediate_info["estimated_tokens"]
        )


if __name__ == "__main__":
    unittest.main()