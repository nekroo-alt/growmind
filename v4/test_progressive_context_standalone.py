"""
Standalone unit tests for V5 progressive context loading.

This is a simplified test file that doesn't require all V4 modules to be implemented.
Tests cover the new V5 progressive context features in ContextEngine.
"""

import unittest
import os
import sys
import tempfile
import shutil

# Add v4 to path and import directly to avoid circular imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import directly from the file to avoid circular imports through __init__.py
import importlib.util
spec = importlib.util.spec_from_file_location("context_engine", "v4/logic/context_engine.py")
context_engine_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_engine_module)

ContextEngine = context_engine_module.ContextEngine
ContextLevel = context_engine_module.ContextLevel
ContextLevelInfo = context_engine_module.ContextLevelInfo


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
        stats = self.engine.get_level_usage_stats()
        self.assertEqual(stats, {0: 0, 1: 0, 2: 0, 3: 0})


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

    def test_get_all_context_levels(self):
        """Test getting all context levels."""
        levels = self.engine.get_all_context_levels()
        
        self.assertEqual(len(levels), 4)
        self.assertIn(ContextLevel.IMMEDIATE, levels)
        self.assertIn(ContextLevel.RECENT, levels)
        self.assertIn(ContextLevel.SESSION, levels)
        self.assertIn(ContextLevel.PROJECT, levels)


if __name__ == "__main__":
    unittest.main()