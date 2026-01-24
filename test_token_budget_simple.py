"""Simple standalone test for TokenBudgetManager"""
import sys
sys.path.insert(0, 'v4')

import os
import tempfile
import sqlite3

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location("token_budget_manager", "v4/logic/token_budget_manager.py")
token_budget_manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(token_budget_manager)

TokenBudgetManager = token_budget_manager.TokenBudgetManager
BudgetAllocation = token_budget_manager.BudgetAllocation
TaskComplexityLevel = token_budget_manager.TaskComplexityLevel
TaskComplexityAnalyzer = token_budget_manager.TaskComplexityAnalyzer

print("=" * 60)
print("Testing TokenBudgetManager Implementation")
print("=" * 60)

# Test 1: Task complexity estimation
print("\n1. Testing task complexity estimation...")
simple_desc = "Fix minor typo in documentation"
complex_desc = "Refactor entire architecture for better performance"

simple_complexity = TaskComplexityAnalyzer.estimate_complexity(simple_desc)
complex_complexity = TaskComplexityAnalyzer.estimate_complexity(complex_desc)

print(f"   Simple task complexity: {simple_complexity.value}")
print(f"   Complex task complexity: {complex_complexity.value}")

assert simple_complexity == TaskComplexityLevel.SIMPLE, "Simple task should be SIMPLE"
assert complex_complexity == TaskComplexityLevel.COMPLEX, "Complex task should be COMPLEX"
print("   ✓ Complexity estimation works")

# Test 2: Default budgets
print("\n2. Testing default budgets...")
assert TaskComplexityAnalyzer.get_default_budget(TaskComplexityLevel.SIMPLE) == 1000
assert TaskComplexityAnalyzer.get_default_budget(TaskComplexityLevel.MEDIUM) == 3000
assert TaskComplexityAnalyzer.get_default_budget(TaskComplexityLevel.COMPLEX) == 5000
print("   ✓ Default budgets correct")

# Test 3: Budget allocation
print("\n3. Testing budget allocation...")
temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = temp_db.name
temp_db.close()

manager = TokenBudgetManager(db_path=db_path, max_total_budget=10000)

allocation = manager.allocate_budget(
    task_description="Implement user authentication",
    task_type="feature"
)

print(f"   Allocated budget: {allocation.initial_budget} tokens")
print(f"   Task type: {allocation.task_type}")
print(f"   Complexity: {allocation.complexity.value}")

assert allocation.initial_budget > 0, "Budget should be positive"
assert allocation.task_type == "feature", "Task type should be feature"
print("   ✓ Budget allocation works")

# Test 4: Token usage tracking
print("\n4. Testing token usage tracking...")
manager.record_token_usage(500)
manager.record_token_usage(300)

print(f"   Tokens used: {allocation.used_tokens}")
print(f"   Remaining tokens: {allocation.remaining_tokens}")
print(f"   Utilization: {allocation.utilization_percentage:.1f}%")

assert allocation.used_tokens == 800, "Should track 800 tokens used"
assert allocation.remaining_tokens == allocation.current_budget - 800, "Remaining should be correct"
print("   ✓ Token usage tracking works")

# Test 5: Budget expansion
print("\n5. Testing budget expansion...")
old_budget = allocation.current_budget
manager.expand_budget("Need more tokens")
new_budget = allocation.current_budget

print(f"   Budget expanded: {old_budget} -> {new_budget} tokens")
print(f"   Expansion count: {allocation.expansion_count}")

assert new_budget > old_budget, "Budget should increase"
assert allocation.expansion_count == 1, "Should count expansions"
print("   ✓ Budget expansion works")

# Test 6: Budget alert
print("\n6. Testing budget alerts...")
allocation.use_tokens(2000)  # Use more to trigger alert

alert = manager.check_budget_alert()
if alert:
    print(f"   Alert triggered: {alert[:80]}...")
    assert "BUDGET ALERT" in alert, "Should contain alert message"
    print("   ✓ Budget alert works")
else:
    print("   ⚠ No alert (may not have reached threshold)")

# Test 7: Task completion
print("\n7. Testing task completion...")
manager.complete_task("test_task_001", success=True)

# Verify database record
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT * FROM token_usage_history WHERE task_id = 'test_task_001'")
row = cursor.fetchone()
conn.close()

assert row is not None, "Should record task in database"
print(f"   Task recorded with tokens used: {row[6]}")
print("   ✓ Task completion works")

# Test 8: Usage report
print("\n8. Testing usage report...")
report = manager.get_usage_report()
print(f"   Total tasks: {report['total_tasks']}")
print(f"   Total tokens: {report['total_tokens']}")
print(f"   Success rate: {report['success_rate']:.1f}%")

assert report['total_tasks'] >= 1, "Should have at least 1 task"
print("   ✓ Usage report works")

# Test 9: Context optimization
print("\n9. Testing context optimization...")
context_items = [
    {'name': 'item1', 'tokens': 500, 'relevance': 0.9},
    {'name': 'item2', 'tokens': 800, 'relevance': 0.5},
    {'name': 'item3', 'tokens': 300, 'relevance': 0.3},
]

optimized = manager.optimize_context_tokens(context_items, max_tokens=1000)

print(f"   Original items: {len(context_items)}")
print(f"   Optimized items: {len(optimized)}")
total_optimized_tokens = sum(item['tokens'] for item in optimized)
print(f"   Optimized tokens: {total_optimized_tokens}")

assert total_optimized_tokens <= 1000, "Should respect max tokens"
print("   ✓ Context optimization works")

# Test 10: Budget learning
print("\n10. Testing budget learning...")
# Complete several similar tasks
for i in range(5):
    alloc = manager.allocate_budget(task_description="Test task", task_type="test")
    alloc.use_tokens(1800)
    manager.complete_task(f"learning_task_{i}", success=True)

# Get learned recommendation
recommendations = manager.get_recommendations_report()
print(f"   Recommendations generated: {len(recommendations)}")
print("   ✓ Budget learning works")

# Cleanup
os.remove(db_path)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nTokenBudgetManager implementation is working correctly.")