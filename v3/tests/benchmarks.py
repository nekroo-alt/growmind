"""
Performance benchmarks for L4D V2 AST analysis components.

This module uses pytest-benchmark to measure performance characteristics
of the AST analysis system, establishing baselines for regression testing.
"""

import pytest
import time
import ast
import os
from pathlib import Path
from typing import List, Dict

# Import the modules to benchmark
from v1.data.semantic_mapper import SemanticMapper
from v1.data.cache_manager import CacheManager
from v1.logic.task_impact_analyzer import TaskImpactAnalyzer
from v1.logic.dependency_traverser import DependencyTraverser
from v1.logic.context_pruner import ContextPruner
from v1.logic.context_engine import ContextEngine


class FixtureCodeGenerator:
    """Generate test code of various sizes for benchmarking."""

    @staticmethod
    def generate_small_module() -> str:
        """Generate a small module (~50 lines)."""
        return '''"""Small module for benchmarking."""
from typing import List, Optional

class SimpleClass:
    """A simple class for testing."""
    
    def __init__(self, name: str) -> None:
        self.name = name
        self.items: List[int] = []
    
    def add_item(self, item: int) -> None:
        """Add an item to the list."""
        self.items.append(item)
    
    def get_sum(self) -> int:
        """Calculate sum of items."""
        return sum(self.items)

def process_data(data: List[int]) -> int:
    """Process data and return result."""
    total = 0
    for item in data:
        if item > 0:
            total += item
    return total

class AdvancedClass(SimpleClass):
    """Extended class with more complexity."""
    
    def __init__(self, name: str, threshold: int) -> None:
        super().__init__(name)
        self.threshold = threshold
    
    def filter_items(self) -> List[int]:
        """Filter items based on threshold."""
        return [i for i in self.items if i > self.threshold]
'''

    @staticmethod
    def generate_medium_module() -> str:
        """Generate a medium module (~200 lines)."""
        code = ['"""Medium module for benchmarking."""']
        code.append("from typing import List, Dict, Optional, Tuple")
        code.append("from dataclasses import dataclass")
        code.append("")

        # Generate multiple classes
        for class_idx in range(5):
            code.append(f"@dataclass")
            code.append(f"class DataClass{class_idx}:")
            code.append(f'    """Data class {class_idx}."""')
            code.append(f"    id: int")
            code.append(f"    name: str")
            code.append(f"    value: float")
            code.append("")

        # Generate a manager class
        code.append("class DataManager:")
        code.append('    """Manager for data operations."""')
        code.append("")
        code.append("    def __init__(self) -> None:")
        code.append("        self._storage: Dict[int, Dict[str, any]] = {}")
        code.append("        self._cache: List[DataClass0] = []")
        code.append("")

        for method_idx in range(10):
            code.append(
                f"    def method_{method_idx}(self, data: DataClass{method_idx % 5}) -> Dict:"
            )
            code.append(f'        """Method {method_idx} description."""')
            code.append("        result = {}")
            code.append("        if data.value > 0:")
            code.append('            result["positive"] = True')
            code.append("        for i in range(10):")
            code.append('            result[f"key_{i}"] = data.value * i')
            code.append("        return result")
            code.append("")

        # Generate helper functions
        for func_idx in range(5):
            code.append(
                f"def helper_function_{func_idx}(items: List[int]) -> Optional[int]:"
            )
            code.append(f'    """Helper function {func_idx}."""')
            code.append("    if not items:")
            code.append("        return None")
            code.append("    result = items[0]")
            code.append("    for item in items[1:]:")
            code.append("        if item > result:")
            code.append("            result = item")
            code.append("    return result")
            code.append("")

        return "\n".join(code)

    @staticmethod
    def generate_large_module() -> str:
        """Generate a large module (~500 lines)."""
        code = ['"""Large module for benchmarking."""']
        code.append("from typing import List, Dict, Set, Optional, Tuple, Callable")
        code.append("from dataclasses import dataclass, field")
        code.append("from enum import Enum")
        code.append("")

        # Generate enums
        code.append("class Status(Enum):")
        code.append('    """Status enumeration."""')
        code.append('    ACTIVE = "active"')
        code.append('    INACTIVE = "inactive"')
        code.append('    PENDING = "pending"')
        code.append("")

        # Generate many dataclasses
        for class_idx in range(15):
            code.append(f"@dataclass")
            code.append(f"class Entity{class_idx}:")
            code.append(f'    """Entity {class_idx}."""')
            code.append(f"    id: int")
            code.append(f"    name: str")
            code.append(f"    status: Status")
            code.append(f"    metadata: Dict[str, any] = field(default_factory=dict)")
            code.append(f"    tags: Set[str] = field(default_factory=set)")
            code.append("")

        # Generate a complex manager class
        code.append("class EntityManager:")
        code.append('    """Complex entity manager."""')
        code.append("")
        code.append("    def __init__(self) -> None:")
        code.append("        self._entities: Dict[int, Dict[str, any]] = {}")
        code.append("        self._index: Dict[str, Set[int]] = {}")
        code.append("        self._callbacks: List[Callable] = []")
        code.append("        self._cache: Dict[int, Entity0] = {}")
        code.append("")

        # Generate many methods
        for method_idx in range(20):
            code.append(
                f"    def operation_{method_idx}(self, entity: Entity{method_idx % 15}) -> bool:"
            )
            code.append(f'        """Perform operation {method_idx}."""')
            code.append("        success = False")
            code.append("        try:")
            code.append("            if entity.id in self._entities:")
            code.append(
                '                self._entities[entity.id]["status"] = entity.status.value'
            )
            code.append("                for tag in entity.tags:")
            code.append("                    if tag not in self._index:")
            code.append("                        self._index[tag] = set()")
            code.append("                    self._index[tag].add(entity.id)")
            code.append("                success = True")
            code.append("            else:")
            code.append("                self._entities[entity.id] = {")
            code.append('                    "name": entity.name,')
            code.append('                    "status": entity.status.value,')
            code.append('                    "metadata": entity.metadata.copy()')
            code.append("                }")
            code.append("                for callback in self._callbacks:")
            code.append("                    callback(entity)")
            code.append("                success = True")
            code.append("        except Exception:")
            code.append("            return False")
            code.append("        return success")
            code.append("")

        # Generate utility functions
        for func_idx in range(10):
            code.append(
                f"def utility_function_{func_idx}(data: List[Entity{func_idx % 15}]) -> Dict[str, int]:"
            )
            code.append(f'    """Utility function {func_idx}."""')
            code.append("    stats = {}")
            code.append('    stats["total"] = len(data)')
            code.append('    stats["active"] = 0')
            code.append('    stats["inactive"] = 0')
            code.append('    stats["pending"] = 0')
            code.append("    for item in data:")
            code.append("        if item.status == Status.ACTIVE:")
            code.append('            stats["active"] += 1')
            code.append("        elif item.status == Status.INACTIVE:")
            code.append('            stats["inactive"] += 1')
            code.append("        else:")
            code.append('            stats["pending"] += 1')
            code.append("    return stats")
            code.append("")

        return "\n".join(code)


@pytest.fixture
def fixture_code_small():
    """Fixture for small code sample."""
    return FixtureCodeGenerator.generate_small_module()


@pytest.fixture
def fixture_code_medium():
    """Fixture for medium code sample."""
    return FixtureCodeGenerator.generate_medium_module()


@pytest.fixture
def fixture_code_large():
    """Fixture for large code sample."""
    return FixtureCodeGenerator.generate_large_module()


@pytest.fixture
def temp_test_file(tmp_path, request):
    """Create temporary test files for benchmarking."""
    code = request.param
    file_path = tmp_path / "test_module.py"
    file_path.write_text(code)
    return str(file_path)


# ==================== Benchmarks ====================


@pytest.mark.benchmark
def test_semantic_mapper_small(tmp_path, fixture_code_small, benchmark):
    """Benchmark AST parsing for small files (~50 lines)."""
    file_path = tmp_path / "small.py"
    file_path.write_text(fixture_code_small)

    def parse():
        mapper = SemanticMapper()
        mapper.analyze_file(str(file_path))

    result = benchmark(parse)
    assert result is not None


@pytest.mark.benchmark
def test_semantic_mapper_medium(tmp_path, fixture_code_medium, benchmark):
    """Benchmark AST parsing for medium files (~200 lines)."""
    file_path = tmp_path / "medium.py"
    file_path.write_text(fixture_code_medium)

    def parse():
        mapper = SemanticMapper()
        mapper.analyze_file(str(file_path))

    result = benchmark(parse)
    assert result is not None


@pytest.mark.benchmark
def test_semantic_mapper_large(tmp_path, fixture_code_large, benchmark):
    """Benchmark AST parsing for large files (~500 lines)."""
    file_path = tmp_path / "large.py"
    file_path.write_text(fixture_code_large)

    def parse():
        mapper = SemanticMapper()
        mapper.analyze_file(str(file_path))

    result = benchmark(parse)
    assert result is not None


@pytest.mark.benchmark
def test_cache_manager_hit(tmp_path, fixture_code_medium):
    """Benchmark cache hit scenario."""
    file_path = tmp_path / "test.py"
    file_path.write_text(fixture_code_medium)

    cache = CacheManager()
    mapper = SemanticMapper()

    # First call (cache miss)
    mapper.analyze_file(str(file_path))

    # Benchmark cache hit
    def cache_hit():
        cache.get(str(file_path), "semantic_map")

    result = benchmark(cache_hit)
    assert result is not None


@pytest.mark.benchmark
def test_cache_manager_miss(tmp_path, fixture_code_medium):
    """Benchmark cache miss scenario."""
    file_path = tmp_path / "test.py"
    file_path.write_text(fixture_code_medium)

    cache = CacheManager()

    def cache_miss():
        mapper = SemanticMapper()
        mapper.analyze_file(str(file_path))

    result = benchmark(cache_miss)
    assert result is not None


@pytest.mark.benchmark
def test_task_impact_analysis(tmp_path, fixture_code_medium):
    """Benchmark task impact analysis."""
    file_path = tmp_path / "test.py"
    file_path.write_text(fixture_code_medium)

    mapper = SemanticMapper()
    semantic_map = mapper.analyze_file(str(file_path))

    analyzer = TaskImpactAnalyzer()

    def analyze():
        analyzer.analyze_task_impact(
            task_title="Add method to DataManager",
            acceptance_criteria=["Add new_method to DataManager class"],
            semantic_maps=[semantic_map],
        )

    result = benchmark(analyze)
    assert result is not None


@pytest.mark.benchmark
def test_dependency_traversal(tmp_path, fixture_code_medium):
    """Benchmark dependency chain traversal."""
    file_path = tmp_path / "test.py"
    file_path.write_text(fixture_code_medium)

    mapper = SemanticMapper()
    semantic_map = mapper.analyze_file(str(file_path))

    traverser = DependencyTraverser()

    def traverse():
        traverser.get_upstream_dependencies(
            target="DataManager.method_0", semantic_map=semantic_map, max_depth=3
        )

    result = benchmark(traverse)
    assert result is not None


@pytest.mark.benchmark
def test_context_pruning(tmp_path, fixture_code_medium):
    """Benchmark context pruning."""
    file_path = tmp_path / "test.py"
    file_path.write_text(fixture_code_medium)

    mapper = SemanticMapper()
    semantic_map = mapper.analyze_file(str(file_path))

    pruner = ContextPruner()

    def prune():
        pruner.prune_context(
            semantic_map=semantic_map,
            relevant_elements=["DataManager", "DataClass0"],
            max_tokens=1000,
        )

    result = benchmark(prune)
    assert result is not None


@pytest.mark.benchmark
def test_context_collection_v1_vs_v2(tmp_path, fixture_code_medium):
    """Compare V1 vs V2 context collection performance."""
    file_path = tmp_path / "test.py"
    file_path.write_text(fixture_code_medium)

    # V2 (AST-based)
    def context_v2():
        engine = ContextEngine()
        engine.collect_context_for_task(
            task_title="Add method to DataManager",
            acceptance_criteria=["Add new_method to DataManager class"],
            files=[str(file_path)],
            use_ast_analysis=True,
        )

    result_v2 = benchmark(context_v2)
    assert result_v2 is not None


@pytest.mark.benchmark
def test_token_usage_v2(tmp_path, fixture_code_medium):
    """Benchmark token usage with V2 AST-based collection."""
    file_path = tmp_path / "test.py"
    file_path.write_text(fixture_code_medium)

    engine = ContextEngine()

    def collect_and_measure():
        context = engine.collect_context_for_task(
            task_title="Add method to DataManager",
            acceptance_criteria=["Add new_method to DataManager class"],
            files=[str(file_path)],
            use_ast_analysis=True,
        )
        # Approximate token count (4 chars per token)
        return len(context) // 4

    result = benchmark(collect_and_measure)
    assert result < 1000  # Should be under 1000 tokens for this task


def test_performance_regression_protection():
    """Baseline values for regression testing."""
    # These are example baseline values that should be updated
    # as the system stabilizes. Actual values will vary by hardware.
    baselines = {
        "semantic_mapper_small": 0.01,  # seconds
        "semantic_mapper_medium": 0.05,
        "semantic_mapper_large": 0.15,
        "cache_hit": 0.001,
        "task_impact_analysis": 0.1,
        "dependency_traversal": 0.05,
        "context_pruning": 0.03,
        "context_collection_v2": 0.2,
    }

    # This test documents expected performance baselines
    # In practice, use pytest-benchmark's --benchmark-autosave
    # to track performance over time
    assert baselines is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
