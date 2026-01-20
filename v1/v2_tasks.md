# L4D V2 Enhancement Tasks: AST-Based Context Collection

## Overview

This document defines a series of tasks to enhance L4D v1 to use Abstract Syntax Tree (AST) analysis for accurately collecting minimum but informative context for tasks, including task definition. The goal is to improve the precision and efficiency of context gathering while reducing token usage and improving implementation accuracy.

## Current Limitations in V1

1. **Simple Keyword Matching**: ContextEngine uses naive keyword matching against function/class names
2. **Shallow Dependency Analysis**: SemanticMapper tracks dependencies but doesn't analyze call graphs or data flow
3. **Coarse Context Collection**: Planner limits to 30 files without intelligent filtering
4. **No Task-Specific Context**: All tasks receive similar context regardless of actual impact
5. **Limited Dependency Tracking**: No understanding of how changes propagate through the codebase

## Enhancement Goals

1. **Precise Context Collection**: Only include code that will actually be affected by the task
2. **Minimum Token Usage**: Reduce context window consumption while maintaining informativeness
3. **Intelligent Task Definition**: Use AST analysis to inform task breakdown and dependency tracking
4. **Impact Analysis**: Understand downstream effects of changes before implementation
5. **Context Caching**: Store and reuse context analysis results

---

## Task Categories

### Phase 1: Enhanced AST Analysis Infrastructure
### Phase 2: Task-Specific Context Collection
### Phase 3: Intelligent Task Definition
### Phase 4: Context Caching and Optimization
### Phase 5: Integration and Testing

---

## Phase 1: Enhanced AST Analysis Infrastructure

### Task 1.1: Enhanced SemanticMapper with Call Graph Analysis ✅ **COMPLETE**

**Title**: Implement call graph analysis in SemanticMapper

**Acceptance Criteria**:
- `SemanticMapper` can construct a call graph showing which functions call which ✓
- Call graph includes inter-class method calls (e.g., `self.method()` calls) ✓
- Call graph identifies external function calls (from other modules) ✓
- Call graph data structure includes: caller, callee, line number, and call depth ✓

**Module**: `data/semantic_mapper.py`

**Estimated Lines**: ~50

**Dependencies**: None

**Technical Notes**:
- Use AST's `ast.Call` nodes to identify function/method invocations
- Track call depth to prevent infinite recursion in analysis
- Store call graph as an adjacency list or similar structure

---

### Task 1.2: Data Flow Analysis in SemanticMapper ✅ **COMPLETE**

**Title**: Add data flow analysis to track variable usage and mutations

**Acceptance Criteria**:
- `SemanticMapper` can track which variables are read and written in each function ✓
- Identify parameter passing between functions ✓
- Track attribute assignments (e.g., `self.value = x`) ✓
- Detect mutable state changes that affect other functions ✓

**Module**: `data/semantic_mapper.py`

**Estimated Lines**: ~60

**Dependencies**: Task 1.1

**Technical Notes**:
- Use `ast.Assign`, `ast.AugAssign`, `ast.AnnAssign` for writes
- Use `ast.Name` with `Load` context for reads
- Track data dependencies across function calls

---

### Task 1.3: Import Dependency Analyzer ✅ **COMPLETE**

**Title**: Create import dependency analyzer to understand module-level dependencies

**Acceptance Criteria**:
- Parse `import`, `from ... import` statements ✓
- Track which external modules/packages are used ✓
- Identify circular dependencies between project modules ✓
- Build a module dependency graph ✓

**Module**: `data/semantic_mapper.py`

**Estimated Lines**: ~40

**Dependencies**: None

**Technical Notes**:
- Use `ast.Import` and `ast.ImportFrom` nodes
- Map imports to actual module files in the project
- Handle dynamic imports (warnings only, not full analysis)

---

### Task 1.4: Type Hint Extraction ✅ **COMPLETE**

**Title**: Extract type hints from function signatures and class attributes

**Acceptance Criteria**:
- Extract parameter type hints from function signatures ✓
- Extract return type annotations ✓
- Extract class attribute type hints (if using `__annotations__`) ✓
- Store type information in semantic map ✓

**Module**: `data/semantic_mapper.py`

**Estimated Lines**: ~30

**Dependencies**: None

**Technical Notes**:
- Use `ast.arg.annotation`, `ast.FunctionDef.returns`
- Parse type hints from `__annotations__` dict
- Handle complex types (e.g., `List[str]`, `Optional[int]`)

---

## Phase 2: Task-Specific Context Collection

### Task 2.1: Task Impact Analyzer ✅ **COMPLETE**

**Title**: Create TaskImpactAnalyzer to predict which code a task will affect

**Acceptance Criteria**:
- Analyze task title and acceptance criteria to identify target modules ✓
- Parse acceptance criteria for function/class references ✓
- Predict which files will need to be modified based on task description ✓
- Return a prioritized list of files with impact confidence scores ✓

**Module**: `logic/task_impact_analyzer.py` (new)

**Estimated Lines**: ~80

**Dependencies**: Task 1.1, 1.2, 1.3

**Technical Notes**:
- Use LLM to parse natural language task description
- Map identified entities to actual code elements using semantic map
- Calculate impact scores based on direct vs indirect dependencies

---

### Task 2.2: Dependency Chain Traversal ✅ **COMPLETE**

**Title**: Implement dependency chain traversal to collect transitive dependencies

**Acceptance Criteria**:
- Given a target function/class, collect all upstream dependencies ✓
- Collect all downstream consumers (functions that call this) ✓
- Limit traversal depth to avoid exponential explosion ✓
- Return dependency chain with depth levels ✓

**Module**: `logic/dependency_traverser.py` (new)

**Estimated Lines**: ~70

**Dependencies**: Task 1.1, 1.2

**Technical Notes**:
- Use BFS or DFS to traverse call graph
- Stop at system boundaries (external modules)
- Include type hints to help identify dependency boundaries

---

### Task 2.3: Minimal Context Pruner ✅ **COMPLETE**

**Title**: Create context pruner that selects minimum informative code snippets

**Acceptance Criteria**:
- Select only the essential code for each relevant function/class ✓
- Include function signatures, docstrings, and key logic ✓
- Exclude implementation details that don't affect the task ✓
- Add context comments explaining why each snippet is included ✓

**Module**: `logic/context_pruner.py` (new)

**Estimated Lines**: ~60

**Dependencies**: Task 2.1, 2.2

**Technical Notes**:
- Heuristic: include signature, imports, key logic (not all lines)
- For classes: include `__init__`, relevant methods, class-level attributes
- For functions: include signature, imports, core logic
- Add "why this matters" comments for LLM understanding

---

### Task 2.4: Smart File Scoping ✅ **COMPLETE**

**Title**: Implement intelligent file scoping based on task impact

**Acceptance Criteria**:
- Automatically determine which files to analyze for a given task
- Skip files that are irrelevant to the task (even if they contain matching keywords)
- Include related files that don't match keywords but are in dependency chain
- Return file list with relevance scores

**Module**: `logic/context_engine.py` (enhance)

**Estimated Lines**: ~40

**Dependencies**: Task 2.1, 2.2

**Technical Notes**:
- Replace simple keyword matching with impact-based selection
- Use dependency analysis to find indirect dependencies
- Limit file count based on impact confidence, not arbitrary limits

---

## Phase 3: Intelligent Task Definition

### Task 3.1: Task Dependency Graph ✅ **COMPLETE**

**Title**: Create task dependency graph to track relationships between tasks

**Acceptance Criteria**:
- Store task dependencies in `task.db` (new table or columns) ✓
- Identify when one task depends on completion of another ✓
- Prevent execution of dependent tasks until prerequisites are met ✓
- Visualize task dependency structure (optional)

**Module**: `data/db_manager.py` (enhance)

**Estimated Lines**: ~50

**Dependencies**: None

**Technical Notes**:
- Add `depends_on` column to tasks table (JSON array of task IDs) ✓
- Update Planner to check dependencies before task selection ✓
- Validate no circular dependencies in task graph ✓

---

### Task 3.2: AST-Informed Task Breakdown ✅ **COMPLETE**

**Title**: Enhance Planner to use AST analysis for more accurate task breakdown

**Acceptance Criteria**:
- Use existing code analysis to suggest natural task boundaries ✓
- Break down tasks at logical code units (e.g., "add method to class X") ✓
- Estimate token impact of proposed tasks during breakdown ✓
- Validate that subtasks don't overlap in code modifications ✓

**Module**: `logic/planner.py` (enhance)

**Estimated Lines**: ~60

**Dependencies**: Task 2.1, 2.2, 3.1

**Technical Notes**:
- Feed semantic map and dependency analysis to LLM during breakdown
- Prompt LLM to respect code structure and existing boundaries
- Calculate estimated lines/impact for each proposed task

---

### Task 3.3: Context-Aware Acceptance Criteria ✅ **COMPLETE**

**Title**: Generate acceptance criteria that verify correct context usage

**Acceptance Criteria**:
- Acceptance criteria include checks for proper context integration ✓
- Verify that new code maintains existing dependency contracts ✓
- Include criteria for not breaking downstream consumers ✓
- Test both direct functionality and side effects ✓

**Module**: `logic/planner.py` (enhance)

**Estimated Lines**: ~350

**Dependencies**: Task 3.2

**Technical Notes**:
- Generate integration tests as part of acceptance criteria ✓
- Include mutation testing requirements ✓
- Check for breaking changes in public APIs ✓

---

### Task 3.4: Task Complexity Estimator ✅ **COMPLETE**

**Title**: Implement complexity estimator based on AST metrics

**Acceptance Criteria**:
- Calculate cyclomatic complexity for functions/classes
- Estimate task effort based on complexity of affected code
- Flag tasks that are likely to exceed 30-line limit before breakdown
- Suggest refactoring for overly complex code areas

**Module**: `logic/complexity_estimator.py` (new)

**Estimated Lines**: ~50

**Dependencies**: Task 1.1, 1.2

**Technical Notes**:
- Cyclomatic complexity: count decision points (if, for, while, except)
- Consider dependency depth in complexity calculation
- Use complexity to validate task breakdown quality

---

## Phase 4: Context Caching and Optimization

### Task 4.1: AST Analysis Cache ✅ **COMPLETE**

**Title**: Implement caching for AST analysis results

**Acceptance Criteria**:
- Store semantic maps and analysis results in cache ✓
- Invalidate cache when source files change (check file modification times) ✓
- Reduce redundant AST parsing for repeated operations ✓
- Cache size management (LRU eviction if needed) ✓

**Module**: `data/cache_manager.py` (new)

**Estimated Lines**: ~80

**Dependencies**: Task 1.1, 1.2, 1.3, 1.4

**Technical Notes**:
- Use file hash or modification time for cache invalidation ✓
- Store cache in `.l4_cache/` directory (add to `.gitignore`) ✓
- Serialize semantic maps using pickle or JSON ✓

---

### Task 4.2: Context Memoization ✅ **COMPLETE**

**Title**: Memoize context collection for similar tasks

**Acceptance Criteria**:
- Store context collections indexed by task keywords/impact set ✓
- Reuse context for tasks targeting the same code areas ✓
- Incrementally update context when related tasks complete ✓
- Track cache hit rates for optimization ✓

**Module**: `logic/context_engine.py` (enhance)

**Estimated Lines**: ~50

**Dependencies**: Task 4.1

**Technical Notes**:
- Use fuzzy matching for similar task queries ✓
- Cache context at different granularity (file-level, function-level) ✓
- Update cache after successful git commits ✓

---

### Task 4.3: Incremental Context Update ✅ **COMPLETE**

**Title**: Update context incrementally after each task completion

**Acceptance Criteria**:
- After task completion, update semantic maps for modified files
- Re-analyze only changed files, not entire codebase
- Update dependency chains affected by changes
- Maintain cache consistency across task executions

**Module**: `logic/context_engine.py` (enhance)

**Estimated Lines**: ~60

**Dependencies**: Task 4.1, 4.2

**Technical Notes**:
- Use git diff to identify changed files
- Clear cache only for affected files
- Rebuild affected dependency chains

---

### Task 4.4: Token Usage Optimization ✅ **COMPLETE**

**Title**: Optimize context size to minimize token usage

**Acceptance Criteria**:
- Compress context representation while preserving informativeness ✓
- Use summaries for well-understood code areas ✓
- Prefer inline context for complex/novel code ✓
- Track token usage per task and optimize thresholds ✓

**Module**: `logic/context_pruner.py` (enhance)

**Estimated Lines**: ~40

**Dependencies**: Task 2.3, 4.1

**Technical Notes**:
- Adaptive pruning: more context for complex tasks, less for simple ones ✓
- Use caching to avoid re-sending stable context ✓
- Implement context budgeting (max tokens per task) ✓

---

## Phase 5: Integration and Testing

### Task 5.1: Update ContextEngine Interface ✅ **COMPLETE**

**Title**: Refactor ContextEngine to use new AST-based analysis

**Acceptance Criteria**:
- `ContextEngine.get_pruned_context()` uses TaskImpactAnalyzer ✓
- Replace keyword matching with impact-based selection ✓
- Maintain backward compatibility with existing code ✓
- Update docstrings and usage examples ✓

**Module**: `logic/context_engine.py` (refactor)

**Estimated Lines**: ~40

**Dependencies**: Task 2.1, 2.2, 2.3, 2.4

**Technical Notes**:
- Preserve existing public API where possible ✓
- Deprecate old methods gradually ✓
- Add migration guide if API changes significantly ✓

---

### Task 5.2: Enhance Planner with AST Context ✅ **COMPLETE**

**Title**: Update Planner to use AST-enhanced context collection

**Acceptance Criteria**:
- `Planner.breakdown_requirements()` uses TaskImpactAnalyzer ✓
- Include semantic map in LLM prompt for better task breakdown ✓
- Validate subtasks don't exceed 30-line limit using complexity analysis ✓
- Log context size and token usage metrics ✓

**Module**: `logic/planner.py` (enhance)

**Estimated Lines**: ~50

**Dependencies**: Task 5.1, 3.2, 3.4

**Technical Notes**:
- Pass task impact analysis to LLM ✓
- Use complexity estimator to validate subtask sizes ✓
- Monitor and log context quality metrics ✓

---

### Task 5.3: Implementor Context Integration ✅ **COMPLETE**

**Title**: Update Implementor to use minimal informative context

**Acceptance Criteria**:
- `Implementor` receives task-specific context from ContextEngine ✓
- Context includes only relevant code for the specific task ✓
- Context includes dependency chain information ✓
- Implementor logs context size and quality metrics ✓

**Module**: `logic/implementor.py` (enhance)

**Estimated Lines**: ~30

**Dependencies**: Task 5.1

**Technical Notes**:
- Pass context through the TDD cycle ✓
- Use context to guide test generation ✓
- Ensure tests verify dependency contracts ✓

---

### Task 5.4: Verifier Context Validation ✅ **COMPLETE**

**Title**: Enhance Verifier to check context completeness

**Acceptance Criteria**:
- Verifier checks that implementation uses provided context appropriately ✓
- Validates that new code doesn't violate dependency contracts ✓
- Checks that all downstream consumers are tested ✓
- Flags incomplete context usage as failure ✓

**Module**: `logic/verifier.py` (enhance)

**Estimated Lines**: ~40

**Dependencies**: Task 5.3

**Technical Notes**:
- Use semantic map to verify no unexpected dependencies added
- Check that all modified code was in context
- Validate integration test coverage

---

### Task 5.5: Unit Tests for AST Analysis ✅ **COMPLETE**

**Title**: Write comprehensive unit tests for new AST analysis components

**Acceptance Criteria**:
- Test SemanticMapper with call graph analysis ✓
- Test TaskImpactAnalyzer with various task descriptions ✓
- Test DependencyTraverser with complex dependency chains ✓
- Test ContextPruner with different code structures ✓
- Achieve >80% code coverage for new modules ✓ (SemanticMapper: 88%, TaskImpactAnalyzer: 93%, DependencyTraverser: 91%, ContextPruner: 90%)

**Module**: `tests/` (new directory)

**Estimated Lines**: ~200

**Dependencies**: All Phase 1-4 tasks

**Technical Notes**:
- Use pytest for testing framework ✓
- Create sample code fixtures for testing ✓
- Test edge cases (circular dependencies, complex types) ✓

---

### Task 5.6: Integration Tests for Context Collection ✅ **COMPLETE**

**Title**: Write integration tests for end-to-end context collection

**Acceptance Criteria**:
- Test full context collection workflow from task to implementation ✓
- Verify context size reduction compared to V1 ✓
- Test caching and incremental updates ✓
- Verify token usage improvements ✓
- Test with real project scenarios ✓

**Module**: `tests/` (new directory)

**Estimated Lines**: ~150

**Dependencies**: Task 5.5

**Technical Notes**:
- Use actual L4D platform code as test fixture ✓
- Measure and report token usage metrics ✓
- Test error handling and cache invalidation ✓

---

### Task 5.7: Performance Benchmarks ✅ **COMPLETE**

**Title**: Create performance benchmarks for AST analysis

**Acceptance Criteria**:
- Benchmark AST parsing time for various file sizes ✓
- Benchmark context collection time with/without caching ✓
- Benchmark token usage: V1 vs V2 ✓
- Establish performance baselines and regression tests ✓

**Module**: `tests/benchmarks.py` (new)

**Estimated Lines**: ~100

**Dependencies**: Task 5.6

**Technical Notes**:
- Use pytest-benchmark for measurements ✓
- Test with projects of different sizes ✓
- Generate performance report ✓

---

### Task 5.8: Documentation and Migration Guide

**Title**: Document new AST-based context collection system

**Acceptance Criteria**:
- Document all new modules and their APIs
- Create migration guide from V1 to V2
- Update PRD and tech.md with new architecture details
- Add examples of context collection usage
- Document performance characteristics and best practices

**Module**: `meta/`, `docs/` (update existing)

**Estimated Lines**: ~150

**Dependencies**: All previous tasks

**Technical Notes**:
- Use clear diagrams for dependency chains
- Include code examples for common patterns
- Document configuration options (if any)
- Update README with new features

---

## Implementation Order

### Priority 1 (Core Infrastructure)
- Task 1.1: Enhanced SemanticMapper with Call Graph Analysis
- Task 1.2: Data Flow Analysis in SemanticMapper
- Task 1.3: Import Dependency Analyzer
- Task 2.1: Task Impact Analyzer

### Priority 2 (Context Collection)
- Task 2.2: Dependency Chain Traversal
- Task 2.3: Minimal Context Pruner
- Task 2.4: Smart File Scoping
- Task 5.1: Update ContextEngine Interface

### Priority 3 (Task Definition Enhancement)
- Task 3.1: Task Dependency Graph
- Task 3.2: AST-Informed Task Breakdown
- Task 3.4: Task Complexity Estimator
- Task 5.2: Enhance Planner with AST Context

### Priority 4 (Optimization and Caching)
- Task 4.1: AST Analysis Cache
- Task 4.2: Context Memoization
- Task 4.3: Incremental Context Update
- Task 4.4: Token Usage Optimization

### Priority 5 (Integration and Quality)
- Task 5.3: Implementor Context Integration
- Task 5.4: Verifier Context Validation
- Task 3.3: Context-Aware Acceptance Criteria
- Task 5.5: Unit Tests for AST Analysis
- Task 5.6: Integration Tests for Context Collection
- Task 5.7: Performance Benchmarks
- Task 5.8: Documentation and Migration Guide

---

## Success Metrics

### Token Usage
- **Goal**: Reduce average context tokens per task by 40-60%
- **Measurement**: Compare V1 vs V2 token usage across sample tasks

### Context Accuracy
- **Goal**: Increase task completion rate (first attempt) from ~70% to ~90%
- **Measurement**: Track task retry rates and context-related failures

### Performance
- **Goal**: Context collection time < 2 seconds for typical project
- **Measurement**: Benchmark context collection with caching enabled

### Task Quality
- **Goal**: Reduce tasks that need re-breakdown by 50%
- **Measurement**: Track task re-planning frequency

---

## Required Updates to Meta Documents

### meta/prd.md Updates Needed
- Update Section 2.1 (The Context Bank) to describe AST-based context collection
- Update Section 3A (The Planner) to mention AST-informed breakdown
- Add section on Context Caching and Optimization
- Update success metrics for token usage and task quality

### meta/tech.md Updates Needed
- Update Module 2 description to include new AST analysis modules
- Update Module 3 (logic/) to list new modules:
  - `logic/task_impact_analyzer.py`
  - `logic/dependency_traverser.py`
  - `logic/context_pruner.py`
  - `logic/complexity_estimator.py`
- Update Module 6 (data/) to include `data/cache_manager.py`
- Update Operational Flow Summary to include context caching steps
- Add performance characteristics section

---

## Risks and Mitigations

### Risk 1: AST Analysis Slows Down Development
- **Mitigation**: Implement aggressive caching, analyze only changed files
- **Fallback**: Provide option to disable AST analysis for rapid prototyping

### Risk 2: Complex Dependencies Create Large Contexts
- **Mitigation**: Strict depth limits on dependency traversal
- **Fallback**: Use summaries for well-understood dependencies

### Risk 3: Incorrect Impact Analysis Misses Required Code
- **Mitigation**: Conservative approach - include borderline dependencies
- **Fallback**: Allow manual context overrides

### Risk 4: Cache Staleness Causes Incorrect Context
- **Mitigation**: Robust cache invalidation based on file hashes
- **Fallback**: Option to clear cache manually

---

## Future Enhancements (Beyond V2)

1. **Semantic Similarity**: Use embeddings to find semantically related code
2. **Test Coverage Analysis**: Include test coverage in impact analysis
3. **Cross-Language Support**: Extend AST analysis to JavaScript/TypeScript
4. **Dynamic Analysis**: Use runtime traces to supplement static analysis
5. **Machine Learning**: Learn from past tasks to improve impact prediction
