# L4D V2 API Reference

Complete API documentation for L4D V2 components.

---

## Table of Contents

- [SemanticMapper](#semanticmapper)
- [TaskImpactAnalyzer](#taskimpactanalyzer)
- [DependencyTraverser](#dependencytraverser)
- [ContextPruner](#contextpruner)
- [ComplexityEstimator](#complexityestimator)
- [CacheManager](#cachemanager)
- [ContextEngine](#contextengine)
- [Planner](#planner)
- [Implementor](#implementor)
- [Verifier](#verifier)

---

## SemanticMapper

**Module**: `v1.data.semantic_mapper`

**Purpose**: Analyzes Python source code using AST to extract semantic information including call graphs, data flow, imports, and type hints.

### Constructor

```python
SemanticMapper(project_root: str)
```

**Parameters:**
- `project_root` (str): Root directory of the project to analyze

**Example:**
```python
from v1.data.semantic_mapper import SemanticMapper

mapper = SemanticMapper(project_root="/path/to/project")
```

### Methods

#### analyze_file()

```python
analyze_file(file_path: str) -> SemanticMap
```

Analyzes a single Python file and returns a semantic map.

**Parameters:**
- `file_path` (str): Path to the Python file (relative to project_root)

**Returns**: `SemanticMap` object containing:
- `call_graph`: Dict[str, List[CallNode]]
- `data_flow`: Dict[str, DataFlowInfo]
- `imports`: List[ImportInfo]
- `type_hints`: Dict[str, TypeHint]

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `SyntaxError`: If file has syntax errors

**Example:**
```python
semantic_map = mapper.analyze_file("src/utils.py")
```

#### get_call_graph()

```python
get_call_graph(file_path: str = None) -> Dict[str, List[CallNode]]
```

Returns the call graph for the analyzed code.

**Parameters:**
- `file_path` (str, optional): Specific file to get call graph for. If None, returns all.

**Returns**: Dictionary mapping function names to lists of CallNode objects.

**CallNode Structure:**
```python
{
    'name': str,           # Function/method name
    'line_number': int,    # Line number of call
    'caller': str,        # Function that makes the call
    'is_external': bool,  # True if from external module
    'depth': int          # Call depth
}
```

**Example:**
```python
call_graph = mapper.get_call_graph()
for caller, callees in call_graph.items():
    for callee in callees:
        print(f"{caller} -> {callee['name']} at line {callee['line_number']}")
```

#### get_data_flow()

```python
get_data_flow(file_path: str = None) -> Dict[str, DataFlowInfo]
```

Returns data flow analysis showing variable reads and writes.

**Parameters:**
- `file_path` (str, optional): Specific file to get data flow for

**Returns**: Dictionary mapping function names to DataFlowInfo objects.

**DataFlowInfo Structure:**
```python
{
    'reads': Set[str],      # Variables read
    'writes': Set[str],     # Variables written
    'parameters': List[str], # Function parameters
    'returns': str,         # Return variable (if tracked)
    'mutations': Set[str]   # Mutable state changes
}
```

**Example:**
```python
data_flow = mapper.get_data_flow()
for func_name, flow in data_flow.items():
    print(f"{func_name}:")
    print(f"  Reads: {flow['reads']}")
    print(f"  Writes: {flow['writes']}")
```

#### get_imports()

```python
get_imports(file_path: str = None) -> List[ImportInfo]
```

Returns import dependency information.

**Parameters:**
- `file_path` (str, optional): Specific file to get imports for

**Returns**: List of ImportInfo objects.

**ImportInfo Structure:**
```python
{
    'module': str,         # Module name
    'name': str,           # Imported name (for from-imports)
    'alias': str,          # Import alias
    'line_number': int,    # Line number
    'is_external': bool    # True if from external package
}
```

**Example:**
```python
imports = mapper.get_imports("src/module.py")
for imp in imports:
    print(f"Import: {imp['module']} -> {imp['name']}")
```

#### get_type_hints()

```python
get_type_hints(file_path: str = None) -> Dict[str, TypeHint]
```

Returns type hint information.

**Parameters:**
- `file_path` (str, optional): Specific file to get type hints for

**Returns**: Dictionary mapping function/class names to TypeHint objects.

**TypeHint Structure:**
```python
{
    'parameters': Dict[str, str],  # Parameter type hints
    'return_type': str,              # Return type hint
    'attributes': Dict[str, str]    # Class attribute types
}
```

**Example:**
```python
type_hints = mapper.get_type_hints()
for func_name, hints in type_hints.items():
    print(f"{func_name}:")
    print(f"  Params: {hints['parameters']}")
    print(f"  Returns: {hints['return_type']}")
```

#### get_all_functions()

```python
get_all_functions() -> List[str]
```

Returns a list of all function names in the analyzed codebase.

**Returns**: List of function names (with module prefix)

**Example:**
```python
functions = mapper.get_all_functions()
print(f"Found {len(functions)} functions")
```

#### get_all_classes()

```python
get_all_classes() -> List[str]
```

Returns a list of all class names in the analyzed codebase.

**Returns**: List of class names (with module prefix)

**Example:**
```python
classes = mapper.get_all_classes()
print(f"Found {len(classes)} classes")
```

---

## TaskImpactAnalyzer

**Module**: `v1.logic.task_impact_analyzer`

**Purpose**: Analyzes task descriptions to predict which code will be affected.

### Constructor

```python
TaskImpactAnalyzer(semantic_mapper: SemanticMapper, llm_provider=None)
```

**Parameters:**
- `semantic_mapper` (SemanticMapper): Initialized semantic mapper
- `llm_provider` (optional): LLM provider for NLP analysis

**Example:**
```python
from v1.logic.task_impact_analyzer import TaskImpactAnalyzer
from v1.data.semantic_mapper import SemanticMapper

mapper = SemanticMapper(project_root=".")
analyzer = TaskImpactAnalyzer(mapper)
```

### Methods

#### analyze_task()

```python
analyze_task(
    task_title: str,
    acceptance_criteria: List[str],
    max_depth: int = 3
) -> ImpactReport
```

Analyzes a task to predict its impact on the codebase.

**Parameters:**
- `task_title` (str): Title of the task
- `acceptance_criteria` (List[str]): List of acceptance criteria
- `max_depth` (int, optional): Maximum depth for dependency traversal (default: 3)

**Returns**: `ImpactReport` object.

**ImpactReport Structure:**
```python
{
    'task_title': str,
    'target_modules': List[str],
    'target_functions': List[str],
    'target_classes': List[str],
    'affected_files': List[ImpactFile],
    'dependency_chain': List[str],
    'confidence_scores': Dict[str, float],
    'token_estimate': int
}
```

**ImpactFile Structure:**
```python
{
    'file_path': str,
    'confidence': float,  # 0.0 to 1.0
    'reason': str
}
```

**Example:**
```python
impact = analyzer.analyze_task(
    task_title="Add error handling to user registration",
    acceptance_criteria=[
        "Catch ValidationError exceptions",
        "Log errors to the logging module"
    ]
)

print(f"Target modules: {impact.target_modules}")
print(f"High confidence files: {[f for f in impact.affected_files if f.confidence > 0.8]}")
```

---

## DependencyTraverser

**Module**: `v1.logic.dependency_traverser`

**Purpose**: Traverses call graphs to collect transitive dependencies.

### Constructor

```python
DependencyTraverser(semantic_mapper: SemanticMapper)
```

**Parameters:**
- `semantic_mapper` (SemanticMapper): Initialized semantic mapper

**Example:**
```python
from v1.logic.dependency_traverser import DependencyTraverser

traverser = DependencyTraverser(mapper)
```

### Methods

#### get_upstream_dependencies()

```python
get_upstream_dependencies(
    target: str,
    max_depth: int = 3,
    include_external: bool = False
) -> List[DependencyNode]
```

Collects all upstream dependencies (functions/classes that the target depends on).

**Parameters:**
- `target` (str): Function or class name to analyze
- `max_depth` (int, optional): Maximum traversal depth (default: 3)
- `include_external` (bool, optional): Include external dependencies (default: False)

**Returns**: List of DependencyNode objects.

**DependencyNode Structure:**
```python
{
    'name': str,
    'type': str,           # 'function' or 'class'
    'module': str,
    'depth': int,
    'is_external': bool
}
```

**Example:**
```python
deps = traverser.get_upstream_dependencies(
    "process_payment",
    max_depth=3,
    include_external=False
)

for dep in deps:
    print(f"{'  ' * dep['depth']}{dep['name']} (depth {dep['depth']})")
```

#### get_downstream_consumers()

```python
get_downstream_consumers(
    target: str,
    max_depth: int = 3
) -> List[DependencyNode]
```

Collects all downstream consumers (functions/classes that call the target).

**Parameters:**
- `target` (str): Function or class name to analyze
- `max_depth` (int, optional): Maximum traversal depth (default: 3)

**Returns**: List of DependencyNode objects

**Example:**
```python
callers = traverser.get_downstream_consumers(
    "process_payment",
    max_depth=2
)

print(f"Called by: {[c['name'] for c in callers]}")
```

---

## ContextPruner

**Module**: `v1.logic.context_pruner`

**Purpose**: Selects minimum informative code snippets to reduce token usage.

### Constructor

```python
ContextPruner(
    semantic_mapper: SemanticMapper,
    max_lines_per_function: int = 30
)
```

**Parameters:**
- `semantic_mapper` (SemanticMapper): Initialized semantic mapper
- `max_lines_per_function` (int, optional): Maximum lines to include per function (default: 30)

**Example:**
```python
from v1.logic.context_pruner import ContextPruner

pruner = ContextPruner(mapper, max_lines_per_function=25)
```

### Methods

#### prune_context()

```python
prune_context(
    target_functions: List[str],
    include_dependencies: bool = True,
    max_lines: int = None
) -> PrunedContext
```

Prunes code to include only essential information.

**Parameters:**
- `target_functions` (List[str]): List of function names to include
- `include_dependencies` (bool, optional): Include function dependencies (default: True)
- `max_lines` (int, optional): Maximum total lines across all functions (default: None)

**Returns**: `PrunedContext` object.

**PrunedContext Structure:**
```python
{
    'snippets': Dict[str, str],  # Function name -> code snippet
    'token_count': int,
    'line_count': int,
    'included_dependencies': List[str],
    'excluded_details': List[str]
}
```

**Example:**
```python
context = pruner.prune_context(
    target_functions=['validate_user', 'save_user'],
    include_dependencies=True,
    max_lines=100
)

print(f"Context size: {context['token_count']} tokens")
print(f"Functions included: {list(context['snippets'].keys())}")

for func_name, snippet in context['snippets'].items():
    print(f"\n{func_name}:")
    print(snippet)
```

---

## ComplexityEstimator

**Module**: `v1.logic.complexity_estimator`

**Purpose**: Calculates cyclomatic complexity and estimates task effort.

### Constructor

```python
ComplexityEstimator(semantic_mapper: SemanticMapper)
```

**Parameters:**
- `semantic_mapper` (SemanticMapper): Initialized semantic mapper

**Example:**
```python
from v1.logic.complexity_estimator import ComplexityEstimator

estimator = ComplexityEstimator(mapper)
```

### Methods

#### calculate_complexity()

```python
calculate_complexity(function_name: str) -> ComplexityInfo
```

Calculates cyclomatic complexity for a function.

**Parameters:**
- `function_name` (str): Name of the function to analyze

**Returns**: `ComplexityInfo` object.

**ComplexityInfo Structure:**
```python
{
    'function_name': str,
    'cyclomatic': int,      # Cyclomatic complexity
    'decision_points': int, # Number of if/for/while/except
    'lines_of_code': int,
    'estimated_lines': int, # Estimated lines to modify
    'difficulty': str        # 'low', 'medium', 'high'
}
```

**Example:**
```python
complexity = estimator.calculate_complexity("process_payment")
print(f"Cyclomatic complexity: {complexity['cyclomatic']}")
print(f"Decision points: {complexity['decision_points']}")
print(f"Difficulty: {complexity['difficulty']}")
```

#### estimate_effort()

```python
estimate_effort(target_functions: List[str]) -> EffortInfo
```

Estimates total effort for modifying multiple functions.

**Parameters:**
- `target_functions` (List[str]): List of function names to estimate

**Returns**: `EffortInfo` object.

**EffortInfo Structure:**
```python
{
    'total_complexity': int,
    'total_lines': int,
    'estimated_hours': float,
    'exceeds_30_lines': bool,
    'recommended_action': str  # 'implement', 'breakdown', 'refactor'
}
```

**Example:**
```python
effort = estimator.estimate_effort(['process_payment', 'validate_payment'])
print(f"Total complexity: {effort['total_complexity']}")
print(f"Estimated hours: {effort['estimated_hours']}")
print(f"Recommended: {effort['recommended_action']}")

if effort['exceeds_30_lines']:
    print("⚠️  Task exceeds 30-line limit, consider breakdown")
```

---

## CacheManager

**Module**: `v1.data.cache_manager`

**Purpose**: Manages caching of AST analysis results.

### Constructor

```python
CacheManager(
    cache_dir: str = ".l4_cache",
    cache_size_mb: int = 100,
    enabled: bool = True
)
```

**Parameters:**
- `cache_dir` (str, optional): Directory for cache storage (default: ".l4_cache")
- `cache_size_mb` (int, optional): Maximum cache size in MB (default: 100)
- `enabled` (bool, optional): Enable/disable caching (default: True)

**Example:**
```python
from v1.data.cache_manager import CacheManager

cache = CacheManager(
    cache_dir=".l4_cache",
    cache_size_mb=200,
    enabled=True
)
```

### Methods

#### put()

```python
put(key: str, value: Any, source_files: List[str] = None)
```

Stores a value in the cache.

**Parameters:**
- `key` (str): Cache key
- `value` (Any): Value to store (must be pickle-serializable)
- `source_files` (List[str], optional): Source files for invalidation

**Example:**
```python
cache.put("semantic_map:src/utils.py", semantic_map, source_files=["src/utils.py"])
```

#### get()

```python
get(key: str, source_files: List[str] = None) -> Any
```

Retrieves a value from the cache with automatic invalidation.

**Parameters:**
- `key` (str): Cache key
- `source_files` (List[str], optional): Source files to check for changes

**Returns**: Cached value or None if cache miss/invalid

**Example:**
```python
semantic_map = cache.get(
    "semantic_map:src/utils.py",
    source_files=["src/utils.py"]
)

if semantic_map:
    print("Using cached semantic map")
else:
    print("Cache miss, re-analyzing")
```

#### invalidate_for_file()

```python
invalidate_for_file(file_path: str)
```

Invalidates all cache entries associated with a file.

**Parameters:**
- `file_path` (str): File path to invalidate

**Example:**
```python
cache.invalidate_for_file("src/utils.py")
```

#### clear_all()

```python
clear_all()
```

Clears all cached data.

**Example:**
```python
cache.clear_all()
```

#### get_stats()

```python
get_stats() -> CacheStats
```

Returns cache statistics.

**Returns**: `CacheStats` object.

**CacheStats Structure:**
```python
{
    'total_entries': int,
    'total_size_mb': float,
    'hit_rate': float,
    'hits': int,
    'misses': int
}
```

**Example:**
```python
stats = cache.get_stats()
print(f"Cache entries: {stats['total_entries']}")
print(f"Cache size: {stats['total_size_mb']:.2f} MB")
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

---

## ContextEngine

**Module**: `v1.logic.context_engine`

**Purpose**: Main engine for collecting task-specific context.

### Constructor

```python
ContextEngine(
    semantic_mapper: SemanticMapper,
    cache_manager: CacheManager,
    config: ContextEngineConfig = None
)
```

**Parameters:**
- `semantic_mapper` (SemanticMapper): Initialized semantic mapper
- `cache_manager` (CacheManager): Initialized cache manager
- `config` (ContextEngineConfig, optional): Configuration options

**Example:**
```python
from v1.logic.context_engine import ContextEngine, ContextEngineConfig

config = ContextEngineConfig(
    max_traversal_depth=3,
    token_budget=4000,
    include_type_hints=True
)

engine = ContextEngine(mapper, cache, config=config)
```

### Methods

#### get_pruned_context()

```python
get_pruned_context(
    task_title: str,
    acceptance_criteria: List[str],
    max_tokens: int = 4000
) -> PrunedContext
```

Collects minimal, task-specific context.

**Parameters:**
- `task_title` (str): Title of the task
- `acceptance_criteria` (List[str]): Acceptance criteria
- `max_tokens` (int, optional): Maximum tokens in context (default: 4000)

**Returns**: `PrunedContext` object (same as ContextPruner output)

**Example:**
```python
context = engine.get_pruned_context(
    task_title="Add error handling to user registration",
    acceptance_criteria=[
        "Catch ValidationError",
        "Log errors",
        "Return user-friendly messages"
    ],
    max_tokens=4000
)

print(f"Context size: {context['token_count']} tokens")
print(f"Files included: {len(context['snippets'])}")
```

#### get_relevant_files()

```python
get_relevant_files(task_description: str) -> List[RelevantFile]
```

Returns list of files relevant to a task.

**Parameters:**
- `task_description` (str): Description of the task

**Returns**: List of `RelevantFile` objects.

**RelevantFile Structure:**
```python
{
    'file_path': str,
    'confidence': float,
    'reason': str
}
```

**Example:**
```python
files = engine.get_relevant_files("Add user authentication")
for file_info in files:
    print(f"{file_info['file_path']} (confidence: {file_info['confidence']:.2f})")
```

---

## Planner

**Module**: `v1.logic.planner`

**Purpose**: Breaks down requirements into atomic tasks.

### Constructor

```python
Planner(
    semantic_mapper: SemanticMapper = None,
    complexity_estimator: ComplexityEstimator = None
)
```

**Parameters:**
- `semantic_mapper` (SemanticMapper, optional): For AST-informed breakdown
- `complexity_estimator` (ComplexityEstimator, optional): For complexity validation

**Example:**
```python
from v1.logic.planner import Planner

planner = Planner(semantic_mapper=mapper, complexity_estimator=estimator)
```

### Methods

#### breakdown_requirements()

```python
breakdown_requirements(
    requirements: str,
    max_lines_per_task: int = 30
) -> List[Task]
```

Breaks down requirements into atomic tasks.

**Parameters:**
- `requirements` (str): High-level requirements
- `max_lines_per_task` (int, optional): Maximum lines per task (default: 30)

**Returns**: List of `Task` objects.

**Task Structure:**
```python
{
    'id': str,
    'title': str,
    'description': str,
    'acceptance_criteria': List[str],
    'estimated_lines': int,
    'complexity': int,
    'depends_on': List[str]
}
```

**Example:**
```python
tasks = planner.breakdown_requirements(
    "Add user authentication with OAuth2 support"
)

for task in tasks:
    print(f"{task['title']} (complexity: {task['complexity']})")
    print(f"  Acceptance criteria: {len(task['acceptance_criteria'])} items")
```

#### validate_subtask_complexity()

```python
validate_subtask_complexity(task: Task) -> ValidationResult
```

Validates that a task doesn't exceed complexity limits.

**Parameters:**
- `task` (Task): Task to validate

**Returns**: `ValidationResult` object.

**ValidationResult Structure:**
```python
{
    'is_valid': bool,
    'complexity': int,
    'estimated_lines': int,
    'issues': List[str],
    'recommendations': List[str]
}
```

**Example:**
```python
result = planner.validate_subtask_complexity(task)
if not result['is_valid']:
    print(f"Task too complex: {result['issues']}")
    print(f"Recommendations: {result['recommendations']}")
```

---

## Implementor

**Module**: `v1.logic.implementor`

**Purpose**: Implements tasks using TDD methodology.

### Constructor

```python
Implementor(semantic_mapper: SemanticMapper = None)
```

**Parameters:**
- `semantic_mapper` (SemanticMapper, optional): For context-aware implementation

**Example:**
```python
from v1.logic.implementor import Implementor

implementor = Implementor(semantic_mapper=mapper)
```

### Methods

#### execute()

```python
execute(task: Task, context: PrunedContext = None) -> ImplementationResult
```

Executes a task using TDD cycle.

**Parameters:**
- `task` (Task): Task to implement
- `context` (PrunedContext, optional): Minimal context for implementation

**Returns**: `ImplementationResult` object.

**ImplementationResult Structure:**
```python
{
    'success': bool,
    'test_passed': bool,
    'code_written': str,
    'test_code': str,
    'lines_added': int,
    'context_used': PrunedContext
}
```

**Example:**
```python
result = implementor.execute(task, context=context)

if result['success']:
    print(f"✅ Task completed successfully")
    print(f"Lines added: {result['lines_added']}")
else:
    print(f"❌ Task failed: {result['error']}")
```

---

## Verifier

**Module**: `v1.logic.verifier`

**Purpose**: Verifies implementation correctness and context completeness.

### Constructor

```python
Verifier(semantic_mapper: SemanticMapper = None)
```

**Parameters:**
- `semantic_mapper` (SemanticMapper, optional): For semantic verification

**Example:**
```python
from v1.logic.verifier import Verifier

verifier = Verifier(semantic_mapper=mapper)
```

### Methods

#### verify()

```python
verify(
    task: Task,
    implementation: ImplementationResult,
    context: PrunedContext = None
) -> VerificationResult
```

Verifies implementation correctness.

**Parameters:**
- `task` (Task): Original task
- `implementation` (ImplementationResult): Implementation to verify
- `context` (PrunedContext, optional): Context used for implementation

**Returns**: `VerificationResult` object.

**VerificationResult Structure:**
```python
{
    'passed': bool,
    'tests_passed': int,
    'tests_failed': int,
    'context_complete': bool,
    'dependency_contracts_ok': bool,
    'downstream_tested': bool,
    'issues': List[str],
    'warnings': List[str]
}
```

**Example:**
```python
result = verifier.verify(task, implementation, context=context)

if result['passed']:
    print(f"✅ Verification passed")
    print(f"Tests: {result['tests_passed']}/{result['tests_passed'] + result['tests_failed']}")
else:
    print(f"❌ Verification failed")
    for issue in result['issues']:
        print(f"  - {issue}")

if result['warnings']:
    print(f"Warnings:")
    for warning in result['warnings']:
        print(f"  - {warning}")
```

---

## Type Definitions

### ContextEngineConfig

```python
@dataclass
class ContextEngineConfig:
    max_traversal_depth: int = 3
    token_budget: int = 4000
    cache_size_mb: int = 100
    include_type_hints: bool = True
    add_context_comments: bool = True
    cache_enabled: bool = True
```

### SemanticMap

```python
@dataclass
class SemanticMap:
    call_graph: Dict[str, List[CallNode]]
    data_flow: Dict[str, DataFlowInfo]
    imports: List[ImportInfo]
    type_hints: Dict[str, TypeHint]
    file_path: str
```

---

## Error Handling

All components raise standard Python exceptions:

- `FileNotFoundError`: File not found during analysis
- `SyntaxError`: Invalid Python syntax
- `ValueError`: Invalid parameters or configuration
- `RuntimeError`: Runtime errors during execution

### Example Error Handling

```python
try:
    semantic_map = mapper.analyze_file("nonexistent.py")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except SyntaxError as e:
    print(f"Syntax error in file: {e}")
```

---

## Configuration Examples

### Production Configuration

```python
from v1.logic.context_engine import ContextEngineConfig

config = ContextEngineConfig(
    max_traversal_depth=3,
    token_budget=4000,
    cache_size_mb=200,
    include_type_hints=True,
    add_context_comments=True,
    cache_enabled=True
)
```

### Development Configuration

```python
config = ContextEngineConfig(
    max_traversal_depth=2,  # Faster for development
    token_budget=2000,      # Smaller context
    cache_size_mb=50,       # Smaller cache
    include_type_hints=True,
    add_context_comments=True,
    cache_enabled=True
)
```

### Debug Configuration

```python
config = ContextEngineConfig(
    max_traversal_depth=5,  # Deeper analysis
    token_budget=8000,      # More context
    cache_size_mb=500,      # Larger cache
    include_type_hints=True,
    add_context_comments=True,
    cache_enabled=False  # Disable cache for debugging
)
```

---

## Performance Tips

1. **Always enable caching** in production for 15x+ performance improvement
2. **Limit traversal depth** to 3 for most use cases
3. **Set appropriate token budgets** (4000-6000 tokens is typical)
4. **Use context pruning** to reduce token usage by 60%
5. **Monitor cache hit rates** and adjust cache size as needed

---

## See Also

- [V2 Architecture Documentation](./V2_ARCHITECTURE.md)
- [Migration Guide](./MIGRATION_V1_TO_V2.md)
- [Performance Benchmarks](./PERFORMANCE.md)
