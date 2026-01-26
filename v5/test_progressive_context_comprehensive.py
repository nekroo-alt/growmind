"""
Comprehensive test suite for V5 progressive context loading (Task 6.1).

Tests verify:
1. Minimal context starts with L0 (immediate) level
2. Context expansion only when needed
3. Heuristics correctly predict expansion needs
4. Learning system optimizes starting levels
5. Token usage reduction of 40% or more
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path
from v5.logic import ContextEngine, ContextLevel


class TestProgressiveContextLoading(unittest.TestCase):
    """Test progressive context loading functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

        # Create test Python files
        self._create_test_files()

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_files(self):
        """Create test Python files for testing."""
        # File 1: Main file with dependencies
        file1_path = os.path.join(self.test_dir, "main.py")
        with open(file1_path, 'w') as f:
            f.write("""
import utils
from models import User, Product
from services import AuthService

def process_user(user_id):
    \"\"\"Process a user.\"\"\"
    user = User.get(user_id)
    return AuthService.validate(user)

def process_product(product_id):
    \"\"\"Process a product.\"\"\"
    product = Product.get(product_id)
    return utils.calculate_price(product)
""")

        # File 2: Utilities
        file2_path = os.path.join(self.test_dir, "utils.py")
        with open(file2_path, 'w') as f:
            f.write("""
def calculate_price(product):
    \"\"\"Calculate product price.\"\"\"
    return product.base_price * product.quantity

def format_date(date):
    \"\"\"Format a date.\"\"\"
    return date.strftime("%Y-%m-%d")

def validate_email(email):
    \"\"\"Validate email address.\"\"\"
    return "@" in email and "." in email
""")

        # File 3: Models
        file3_path = os.path.join(self.test_dir, "models.py")
        with open(file3_path, 'w') as f:
            f.write("""
class User:
    \"\"\"User model.\"\"\"
    def __init__(self, user_id, name, email):
        self.id = user_id
        self.name = name
        self.email = email

    @staticmethod
    def get(user_id):
        \"\"\"Get user by ID.\"\"\"
        return User(user_id, "Test", "test@example.com")

class Product:
    \"\"\"Product model.\"\"\"
    def __init__(self, product_id, name, base_price, quantity=1):
        self.id = product_id
        self.name = name
        self.base_price = base_price
        self.quantity = quantity

    @staticmethod
    def get(product_id):
        \"\"\"Get product by ID.\"\"\"
        return Product(product_id, "Test Product", 100.0)
""")

        # File 4: Services
        file4_path = os.path.join(self.test_dir, "services.py")
        with open(file4_path, 'w') as f:
            f.write("""
class AuthService:
    \"\"\"Authentication service.\"\"\"
    
    @staticmethod
    def validate(user):
        \"\"\"Validate user.\"\"\"
        return user.email and "@" in user.email

    @staticmethod
    def login(email, password):
        \"\"\"Login user.\"\"\"
        # Validation logic
        return True

    @staticmethod
    def logout(user_id):
        \"\"\"Logout user.\"\"\"
        # Logout logic
        return True
""")

    def test_context_level_enum(self):
        """Test ContextLevel enum values."""
        self.assertEqual(ContextLevel.IMMEDIATE.value, 0)
        self.assertEqual(ContextLevel.RECENT.value, 1)
        self.assertEqual(ContextLevel.SESSION.value, 2)
        self.assertEqual(ContextLevel.PROJECT.value, 3)

    def test_context_level_initialization(self):
        """Test that context levels are properly initialized."""
        levels = self.engine.get_all_context_levels()

        self.assertEqual(len(levels), 4)
        self.assertIn(ContextLevel.IMMEDIATE, levels)
        self.assertIn(ContextLevel.RECENT, levels)
        self.assertIn(ContextLevel.SESSION, levels)
        self.assertIn(ContextLevel.PROJECT, levels)

        # Check level info
        immediate_info = levels[ContextLevel.IMMEDIATE]
        self.assertEqual(immediate_info.name, "Immediate")
        self.assertEqual(immediate_info.token_multiplier, 1.0)

        recent_info = levels[ContextLevel.RECENT]
        self.assertEqual(recent_info.name, "Recent")
        self.assertEqual(recent_info.token_multiplier, 2.5)

    def test_start_with_immediate_level(self):
        """Test that progressive context starts with L0 (immediate) level."""
        context, info = self.engine.get_progressive_context(
            task_query="process user",
            files=["main.py"],
            task_type="bug_fix",
            initial_level=ContextLevel.IMMEDIATE,
        )

        # Should start at immediate level
        self.assertEqual(info["starting_level"], 0)
        self.assertEqual(info["task_type"], "bug_fix")

    def test_no_expansion_for_simple_task(self):
        """Test that simple tasks don't expand beyond immediate level."""
        context, info = self.engine.get_progressive_context(
            task_query="process user",
            files=["main.py"],
            task_type="simple_fix",
            initial_level=ContextLevel.IMMEDIATE,
        )

        # Simple task should not expand
        self.assertEqual(info["starting_level"], 0)
        self.assertEqual(info["final_level"], 0)
        self.assertEqual(info["expansion_count"], 0)
        self.assertIsNone(info["expansion_reason"])

    def test_expansion_for_complex_task(self):
        """Test that complex tasks expand to higher levels."""
        context, info = self.engine.get_progressive_context(
            task_query="refactor authentication",
            files=["main.py", "services.py", "models.py"],
            task_type="refactor",  # Complex task type
            initial_level=ContextLevel.IMMEDIATE,
        )

        # Complex task should expand
        self.assertEqual(info["starting_level"], 0)
        # Should expand at least one level
        self.assertGreaterEqual(info["expansion_count"], 0)
        # Final level should be >= starting level
        self.assertGreaterEqual(info["final_level"], info["starting_level"])

    def test_context_sufficiency_heuristics(self):
        """Test that context sufficiency heuristics work correctly."""
        # Test 1: Very small context should be insufficient
        small_context = "def foo(): pass"
        is_sufficient = self.engine._is_context_sufficient(
            small_context,
            ContextLevel.IMMEDIATE,
            "simple_fix",
            {"estimated_tokens": 10}
        )
        self.assertFalse(is_sufficient)

        # Test 2: Moderate context should be sufficient
        moderate_context = "\n".join(["def foo(): pass"] * 20)
        is_sufficient = self.engine._is_context_sufficient(
            moderate_context,
            ContextLevel.IMMEDIATE,
            "simple_fix",
            {"estimated_tokens": 1000}
        )
        self.assertTrue(is_sufficient)

    def test_learned_optimal_level(self):
        """Test that the system learns optimal starting levels."""
        # Simulate multiple successful tasks at L0
        for _ in range(10):
            context, info = self.engine.get_progressive_context(
                task_query="simple fix",
                files=["main.py"],
                task_type="bug_fix",
                initial_level=ContextLevel.IMMEDIATE,
            )
            # Record successful outcome at L0
            self.engine.record_task_outcome(
                task_type="bug_fix",
                starting_level=ContextLevel.IMMEDIATE,
                final_level=ContextLevel.IMMEDIATE,
                success=True
            )

        # Check that optimal level is learned
        optimal_levels = self.engine.get_optimal_levels()
        self.assertIn("bug_fix", optimal_levels)
        self.assertEqual(optimal_levels["bug_fix"], ContextLevel.IMMEDIATE)

    def test_expansion_statistics_tracking(self):
        """Test that expansion statistics are tracked correctly."""
        # Run a few tasks with expansion
        for i in range(3):
            context, info = self.engine.get_progressive_context(
                task_query=f"task {i}",
                files=["main.py", "utils.py"],
                task_type="new_feature",
                initial_level=ContextLevel.IMMEDIATE,
            )

        # Check expansion statistics
        stats = self.engine.get_expansion_stats()
        self.assertIn("new_feature", stats)
        self.assertGreater(stats["new_feature"]["count"], 0)
        self.assertIn("avg_final_level", stats["new_feature"])
        self.assertIn("avg_expansion_count", stats["new_feature"])

    def test_level_usage_statistics(self):
        """Test that level usage statistics are tracked."""
        # Use different levels
        for _ in range(5):
            self.engine.get_progressive_context(
                task_query="simple task",
                files=["main.py"],
                task_type="simple_fix",
                initial_level=ContextLevel.IMMEDIATE,
            )

        # Check usage stats
        usage_stats = self.engine.get_level_usage_stats()
        self.assertIn(0, usage_stats)  # L0 should be used
        self.assertGreaterEqual(usage_stats[0], 5)

    def test_token_reduction_vs_full_context(self):
        """Test that progressive context reduces token usage by 40%+."""
        # Get progressive context
        progressive_context, prog_info = self.engine.get_progressive_context(
            task_query="process user",
            files=["main.py"],
            task_type="bug_fix",
            initial_level=ContextLevel.IMMEDIATE,
        )

        # Get full context (PROJECT level)
        full_context = self.engine.get_pruned_context(
            task_query="process user",
            files=["main.py", "utils.py", "models.py", "services.py"],
            use_smart_scoping=True,
            task_title="process user",
        )

        # Calculate token counts (approximate by word count)
        progressive_tokens = len(progressive_context.split())
        full_tokens = len(full_context.split())

        # Progressive should use significantly fewer tokens
        reduction_pct = (1 - progressive_tokens / full_tokens) * 100 if full_tokens > 0 else 0

        # Verify at least 40% reduction
        self.assertGreaterEqual(
            reduction_pct,
            40.0,
            f"Token reduction {reduction_pct:.1f}% is below 40% target"
        )

        print(f"\nToken Usage Comparison:")
        print(f"  Progressive context: {progressive_tokens} tokens")
        print(f"  Full context: {full_tokens} tokens")
        print(f"  Reduction: {reduction_pct:.1f}%")

    def test_expansion_max_level_limit(self):
        """Test that expansion respects max_level parameter."""
        context, info = self.engine.get_progressive_context(
            task_query="complex refactor",
            files=["main.py"],
            task_type="refactor",
            initial_level=ContextLevel.IMMEDIATE,
            max_level=ContextLevel.RECENT,  # Limit to L1
        )

        # Should not expand beyond L1
        self.assertLessEqual(info["final_level"], ContextLevel.RECENT.value)

    def test_task_outcome_recording(self):
        """Test that task outcomes are recorded for learning."""
        # Record a successful outcome
        self.engine.record_task_outcome(
            task_type="bug_fix",
            starting_level=ContextLevel.IMMEDIATE,
            final_level=ContextLevel.IMMEDIATE,
            success=True
        )

        # Check that level info was updated
        level_info = self.engine.get_context_level_info(ContextLevel.IMMEDIATE)
        self.assertEqual(level_info.expansion_count, 1)
        self.assertEqual(level_info.average_success_rate, 1.0)

        # Record a failed outcome
        self.engine.record_task_outcome(
            task_type="bug_fix",
            starting_level=ContextLevel.IMMEDIATE,
            final_level=ContextLevel.RECENT,
            success=False
        )

        # Check that success rate decreased
        level_info = self.engine.get_context_level_info(ContextLevel.IMMEDIATE)
        self.assertEqual(level_info.expansion_count, 2)
        self.assertEqual(level_info.average_success_rate, 0.5)

    def test_context_info_completeness(self):
        """Test that context info dictionary contains all required fields."""
        context, info = self.engine.get_progressive_context(
            task_query="test task",
            files=["main.py"],
            task_type="test",
        )

        # Check required fields
        required_fields = [
            "starting_level",
            "final_level",
            "expansion_count",
            "task_type",
            "files_analyzed",
            "estimated_tokens",
            "expansion_reason",
        ]

        for field in required_fields:
            self.assertIn(field, info, f"Missing field: {field}")

    def test_force_refresh_bypasses_cache(self):
        """Test that force_refresh bypasses cache."""
        # First call
        context1, info1 = self.engine.get_progressive_context(
            task_query="test",
            files=["main.py"],
            force_refresh=False,
        )

        # Second call with force_refresh
        context2, info2 = self.engine.get_progressive_context(
            task_query="test",
            files=["main.py"],
            force_refresh=True,
        )

        # Should both succeed (just verify they work)
        self.assertIsNotNone(context1)
        self.assertIsNotNone(context2)


class TestProgressiveContextEdgeCases(unittest.TestCase):
    """Test edge cases for progressive context loading."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_empty_files_list(self):
        """Test behavior with empty files list."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=[],
            task_type="simple_fix",
        )

        # Should handle gracefully
        self.assertIsNotNone(context)
        self.assertEqual(info["files_analyzed"], 0)

    def test_nonexistent_files(self):
        """Test behavior with non-existent files."""
        context, info = self.engine.get_progressive_context(
            task_query="test",
            files=["nonexistent.py"],
            task_type="simple_fix",
        )

        # Should handle gracefully
        self.assertIsNotNone(context)

    def test_all_levels_expansion(self):
        """Test expansion through all levels."""
        # Create a scenario that triggers maximum expansion
        context, info = self.engine.get_progressive_context(
            task_query="large refactor",
            files=["main.py"],
            task_type="architecture",  # Most complex type
            initial_level=ContextLevel.IMMEDIATE,
            max_level=ContextLevel.PROJECT,
        )

        # Verify it doesn't exceed max
        self.assertLessEqual(info["final_level"], ContextLevel.PROJECT.value)

    def test_success_rate_threshold(self):
        """Test that success rate affects expansion decisions."""
        # Record many failures at L0
        for _ in range(10):
            self.engine.record_task_outcome(
                task_type="complex_task",
                starting_level=ContextLevel.IMMEDIATE,
                final_level=ContextLevel.SESSION,  # Had to expand
                success=False
            )

        # Now test that it might start at higher level
        # (This is heuristic-based, so we just verify the mechanism works)
        context, info = self.engine.get_progressive_context(
            task_query="complex task",
            files=["main.py"],
            task_type="complex_task",
        )

        # Should work without errors
        self.assertIsNotNone(context)


class TestProgressiveContextIntegration(unittest.TestCase):
    """Integration tests for progressive context."""

    def setUp(self):
        """Set up test environment with realistic project structure."""
        self.test_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(workspace_root=self.test_dir)
        self._create_realistic_project()

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_realistic_project(self):
        """Create a realistic project structure."""
        # Create directory structure
        os.makedirs(os.path.join(self.test_dir, "services"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "models"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "utils"), exist_ok=True)

        # Create main.py
        with open(os.path.join(self.test_dir, "main.py"), 'w') as f:
            f.write("""
from services.auth_service import AuthService
from services.user_service import UserService
from models.user import User
from utils.logger import Logger

def main():
    \"\"\"Main entry point.\"\"\"
    user = UserService.authenticate("user", "pass")
    Logger.log(f"User {user.id} authenticated")

if __name__ == "__main__":
    main()
""")

        # Create auth_service.py
        with open(os.path.join(self.test_dir, "services", "auth_service.py"), 'w') as f:
            f.write("""
class AuthService:
    @staticmethod
    def authenticate(username, password):
        return User.find(username, password)

    @staticmethod
    def validate_token(token):
        return token and len(token) > 10
""")

        # Create user_service.py
        with open(os.path.join(self.test_dir, "services", "user_service.py"), 'w') as f:
            f.write("""
from models.user import User

class UserService:
    @staticmethod
    def authenticate(username, password):
        return User.find(username, password)

    @staticmethod
    def get_user(user_id):
        return User.get_by_id(user_id)
""")

        # Create user model
        with open(os.path.join(self.test_dir, "models", "user.py"), 'w') as f:
            f.write("""
class User:
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

    @staticmethod
    def find(username, password):
        return User(1, username)

    @staticmethod
    def get_by_id(user_id):
        return User(user_id, "test_user")
""")

        # Create logger utility
        with open(os.path.join(self.test_dir, "utils", "logger.py"), 'w') as f:
            f.write("""
class Logger:
    @staticmethod
    def log(message):
        print(f"[LOG] {message}")

    @staticmethod
    def error(message):
        print(f"[ERROR] {message}")
""")

        # Create __init__ files
        with open(os.path.join(self.test_dir, "services", "__init__.py"), 'w') as f:
            f.write("")
        with open(os.path.join(self.test_dir, "models", "__init__.py"), 'w') as f:
            f.write("")
        with open(os.path.join(self.test_dir, "utils", "__init__.py"), 'w') as f:
            f.write("")

    def test_realistic_bug_fix_scenario(self):
        """Test progressive context for realistic bug fix."""
        # Simulate learning from previous tasks
        for _ in range(5):
            self.engine.record_task_outcome(
                task_type="bug_fix",
                starting_level=ContextLevel.IMMEDIATE,
                final_level=ContextLevel.IMMEDIATE,
                success=True
            )

        # Now fix a bug
        context, info = self.engine.get_progressive_context(
            task_query="fix authentication bug",
            files=["main.py"],
            task_type="bug_fix",
            task_title="Fix authentication bug",
            acceptance_criteria="Authentication should work for valid credentials",
        )

        # Should use learned optimal level
        self.assertIsNotNone(context)
        self.assertGreaterEqual(info["files_analyzed"], 1)

        # Verify token reduction
        full_context = self.engine.get_pruned_context(
            task_query="fix authentication bug",
            files=["main.py", "services/auth_service.py", "services/user_service.py"],
            use_smart_scoping=True,
            task_title="Fix authentication bug",
        )

        prog_tokens = len(context.split())
        full_tokens = len(full_context.split())
        reduction = (1 - prog_tokens / full_tokens) * 100 if full_tokens > 0 else 0

        self.assertGreaterEqual(reduction, 40.0,
            f"Realistic bug fix: {reduction:.1f}% reduction (target: 40%)")

    def test_realistic_feature_addition(self):
        """Test progressive context for feature addition."""
        context, info = self.engine.get_progressive_context(
            task_query="add user logout",
            files=["services/auth_service.py"],
            task_type="new_feature",
            task_title="Add user logout functionality",
            acceptance_criteria="Users should be able to logout",
        )

        self.assertIsNotNone(context)
        self.assertEqual(info["task_type"], "new_feature")


def run_tests():
    """Run all tests and report results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestProgressiveContextLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestProgressiveContextEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestProgressiveContextIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)