# L4D V5 Enhancement Tasks: Simplicity, Effectiveness, and Cost Efficiency

## Overview

This document defines a series of tasks to enhance L4D v4 with housekeeping capabilities and evolve the product to be **simpler, more effective, and cost-efficient**. The goal is to create a system that:

1. **Automatic Housekeeping**: Identify and remove unused files and code without breaking functionality
2. **Simplified Workflow**: Streamlined user experience with minimum friction
3. **Layered Context**: Progressive context expansion to reduce token usage
4. **Cost Optimization**: Reduce LLM API calls and token consumption
5. **Quality Focus**: Improve outcome quality through better context management
6. **Ease of Use**: Lower barrier to entry and reduce configuration complexity

---

## Current Limitations in V4

1. **No Housekeeping**: Unused files and code accumulate over time
2. **Complex Configuration**: Many environment variables and settings to configure
3. **High Token Usage**: Always loads full context regardless of task complexity
4. **Excessive LLM Calls**: Calls LLM for decisions that could be made locally
5. **Steep Learning Curve**: Users need to understand complex architecture
6. **Manual Cleanup**: Requires manual intervention to remove old checkpoints, logs, telemetry
7. **No Dependency Analysis**: Cannot identify unused dependencies
8. **No Dead Code Detection**: Cannot identify and remove dead code

---

## Enhancement Goals

1. **Automatic Housekeeping**: Automatically identify and clean unused files and code
2. **Simplified Configuration**: Reduce configuration complexity with smart defaults
3. **Progressive Context**: Start with minimal context, expand only when needed
4. **Cost Optimization**: Reduce LLM API calls by 40% through local decision making
5. **Quality Enhancement**: Improve outcome quality through better context layering
6. **User-Friendly**: Simplified CLI and onboarding experience

---

## Task Categories

### Phase 1: Code Analysis and Dependency Tracking
### Phase 2: Unused Code Detection
### Phase 3: Automatic Housekeeping
### Phase 4: Cost Optimization
### Phase 5: Simplified Configuration
### Phase 6: Progressive Context Management
### Phase 7: Quality Enhancement
### Phase 8: User Experience Improvements

---

## Phase 1: Code Analysis and Dependency Tracking

### Task 1.1: Enhanced AST Analysis with Call Graph Persistence ✅ **COMPLETE**

**Title**: Enhance AST analysis to track persistent call graphs across sessions

**Acceptance Criteria**:
- [x] Persist call graphs to SQLite database for faster subsequent analysis
- [x] Track function/class usage statistics over time
- [x] Identify hot functions (frequently called) vs cold functions (rarely called)
- [x] Track import dependencies and usage frequency
- [x] Support incremental updates to call graphs
- [x] Export call graphs for external analysis

**Module**: Enhanced `data/semantic_mapper.py`, added `data/call_graph_persistence.py` (new)

**Estimated Lines**: ~350

**Dependencies**: V4 semantic_mapper

**Implementation**:
- Created `CallGraphPersistence` class with full persistent call graph functionality
- Implemented SQLite schema with call_graph, function_usage, import_dependencies, and file_metadata tables
- Added call graph storage and retrieval with automatic incrementing of call counts
- Implemented hot/cold function identification based on configurable thresholds
- Added import dependency tracking for both module imports and from imports
- Implemented export functionality in JSON, DOT, and GraphML formats
- Added call graph merging from multiple databases
- Implemented comprehensive statistics generation
- Enhanced `SemanticMapper` to use `CallGraphPersistence` for persistent call graph tracking
- Added 13 comprehensive unit tests all passing

**Status**: ✅ IMPLEMENTED - 2025-01-24

**Technical Notes**:
- Call graph schema:
  ```sql
  CREATE TABLE call_graph (
      source_file TEXT,
      source_function TEXT,
      target_file TEXT,
      target_function TEXT,
      call_count INTEGER DEFAULT 1,
      last_call_timestamp DATETIME,
      PRIMARY KEY (source_file, source_function, target_file, target_function)
  );
  
  CREATE TABLE function_usage (
      file_path TEXT,
      function_name TEXT,
      call_count INTEGER,
      last_used DATETIME,
      PRIMARY KEY (file_path, function_name)
  );
  ```
- Incremental update: Only re-analyze changed files
- Merge call graphs from multiple analysis runs
- Export as JSON, GraphML, or DOT format

---

### Task 1.2: Import Dependency Analysis ✅ **COMPLETE**

**Title**: Analyze and track import dependencies across the codebase

**Acceptance Criteria**:
- [x] Track all imports in Python files (absolute, relative, from imports)
- [x] Identify unused imports (imported but not used)
- [x] Identify circular import dependencies
- [x] Identify import depth (how many levels deep)
- [x] Track import usage frequency over time
- [x] Generate import dependency report

**Module**: `logic/import_analyzer.py` (new)

**Estimated Lines**: ~200 (actual: ~600 with comprehensive features)

**Dependencies**: Task 1.1

**Implementation**:
- Created `ImportAnalyzer` class with full import dependency analysis
- Implemented AST-based import tracking for both simple and from imports
- Added unused import detection with name usage analysis
- Implemented circular dependency detection using DFS algorithm
- Added import depth calculation using BFS
- Generated comprehensive reports in text, JSON, and markdown formats
- Added caching for performance optimization
- Integrated with CallGraphPersistence for usage tracking
- Created comprehensive unit tests

**Status**: ✅ IMPLEMENTED - 2025-01-24

**Technical Notes**:
- Import detection:
  ```python
  # Simple imports (import module)
  # From imports (from module import name1, name2)
  # Relative imports (from . import module)
  ```
- Unused import detection:
  - Uses AST to track variable usage
  - Identifies unused module imports
  - Identifies unused names in from imports
- Circular dependency detection:
  - Uses DFS to detect cycles in dependency graph
  - Distinguishes between direct (A->B->A) and indirect cycles
  - Provides fix suggestions
- Import depth calculation:
  - Uses BFS to calculate maximum depth
  - Identifies leaf files (no dependents)
- Report formats:
  - Text: Human-readable summary
  - JSON: Machine-readable data
  - Markdown: Documentation-friendly format

**Technical Notes**:
- Import analysis:
  - Parse AST to extract all imports
  - Track which imported names are actually used
  - Detect unused imports
  - Detect circular dependencies using graph algorithms
  - Calculate import depth (maximum nesting level)
- Output report:
  ```
  Unused Imports:
  - utils.py: unused_function, unused_class
  - models.py: deprecated_model
  
  Circular Dependencies:
  - module_a → module_b → module_c → module_a
  
  Import Depth:
  - Average: 2.3
  - Maximum: 5 (module_x → module_y → module_z → module_a → module_b → module_c)
  ```
- Suggest fixes for circular imports

---

### Task 1.3: File Usage Tracker

**Title**: Track file usage patterns to identify unused files

**Acceptance Criteria**:
- Track which files are imported/referenced in the codebase
- Track which files are executed (entry points, scripts)
- Track file modification timestamps
- Track file size over time
- Identify potential unused files (not imported, not executed, old)
- Generate file usage report

**Module**: `logic/file_usage_tracker.py` (new)

**Estimated Lines**: ~250

**Dependencies**: Task 1.2

**Technical Notes**:
- File usage tracking:
  - Parse all Python files to identify imports
  - Identify entry points (main blocks, if __name__ == '__main__')
  - Track test files and their coverage
  - Track documentation files
- Unused file criteria:
  - Not imported by any other file
  - Not an entry point (no main block)
  - Not a test file (not in tests/ directory)
  - Last modified > 30 days ago
  - Not in documentation or configuration
- File usage report:
  ```
  Potentially Unused Files:
  - old_utils.py (last modified: 2024-12-01, size: 5KB)
  - deprecated_feature.py (last modified: 2024-11-15, size: 12KB)
  
  Most Used Files:
  - core/start.py (imported by 15 files)
  - logic/implementor.py (imported by 12 files)
  ```

---

## Phase 2: Unused Code Detection

### Task 2.1: Dead Function Detection

**Title**: Detect unused functions in the codebase

**Acceptance Criteria**:
- Identify functions that are never called
- Identify functions that are called only by tests (consider for removal in production)
- Identify functions with zero or low call count
- Distinguish between public API functions (may be used externally) vs internal functions
- Generate dead function report
- Suggest safe removal candidates

**Module**: `logic/dead_code_detector.py` (new)

**Estimated Lines**: ~300

**Dependencies**: Task 1.1, 1.3

**Technical Notes**:
- Dead function detection:
  - Use call graph from Task 1.1
  - Functions with call_count = 0 are dead code
  - Check if function is part of public API (has __all__, exported from __init__)
  - Check if function is called only by test files
- Report categories:
  - **Dead**: Never called, not in public API
  - **Test-Only**: Called only by test files
  - **Low Usage**: Called less than N times (configurable)
- Safe removal suggestions:
  - High confidence: Dead, not in public API, no tests
  - Medium confidence: Dead, but has tests
  - Low confidence: Test-only or low usage (may be used in future)

---

### Task 2.2: Dead Class Detection

**Title**: Detect unused classes in the codebase

**Acceptance Criteria**:
- Identify classes that are never instantiated
- Identify classes with methods that are never called
- Identify classes inherited from but never directly used
- Distinguish between abstract base classes vs concrete classes
- Generate dead class report
- Suggest safe removal candidates

**Module**: `logic/dead_code_detector.py` (enhance)

**Estimated Lines**: ~200 (additional)

**Dependencies**: Task 2.1

**Technical Notes**:
- Dead class detection:
  - Track class instantiations
  - Track method calls per class
  - Identify abstract base classes (ABC, abstract methods)
  - Identify mixins (classes with __init__ but no state)
- Report categories:
  - **Dead Class**: Never instantiated, no subclasses
  - **Abstract Base**: Not instantiated, but has subclasses
  - **Mixin**: Used for inheritance, not direct instantiation
  - **Low Usage**: Instantiated less than N times

---

### Task 2.3: Unused Variable Detection

**Title**: Detect unused variables in Python code

**Acceptance Criteria**:
- Identify local variables that are assigned but never used
- Identify class attributes that are never accessed
- Identify module-level variables that are never imported
- Exclude variables with special names (e.g., _variable)
- Generate unused variable report
- Suggest safe removal candidates

**Module**: `logic/dead_code_detector.py` (enhance)

**Estimated Lines**: ~150 (additional)

**Dependencies**: Task 2.1

**Technical Notes**:
- Unused variable detection:
  - Use AST to track variable assignments and references
  - Track scope (local, class, module)
  - Exclude special variables (starts with _, __all__, __version__, etc.)
- Report categories:
  - **Local Variables**: Assigned but not referenced in scope
  - **Class Attributes**: Set but never accessed
  - **Module Variables**: Defined but never imported/referenced
- False positive handling:
  - Variables used only in comments/docstrings
  - Variables used in string formatting
  - Variables used in getattr/setattr

---

## Phase 3: Automatic Housekeeping

### Task 3.1: Safe Deletion Pipeline

**Title**: Implement safe deletion pipeline for unused code

**Acceptance Criteria**:
- Create backup before any deletion
- Run all tests before and after deletion
- Validate that deletion doesn't break imports
- Validate that deletion doesn't break tests
- Rollback automatically if tests fail
- Log all deletions with reason

**Module**: `logic/housekeeping_pipeline.py` (new)

**Estimated Lines**: ~400

**Dependencies**: Task 2.1, 2.2, 2.3

**Technical Notes**:
- Safe deletion process:
  1. Create backup (git commit or file copy)
  2. Run test suite to establish baseline
  3. Delete identified dead code
  4. Run test suite again
  5. If tests pass: Commit changes
  6. If tests fail: Rollback from backup
- Backup strategies:
  - Git commit with descriptive message
  - Copy files to .backup/ directory
  - Create checkpoint using existing checkpoint system
- Validation checks:
  - All imports resolve
  - All tests pass
  - No syntax errors
  - No runtime errors in basic smoke tests
- CLI command:
  ```bash
  l4-dev housekeep --dry-run          # Preview deletions
  l4-dev housekeep --auto            # Automatic safe deletion
  l4-dev housekeep --confirm         # Require confirmation for each deletion
  ```

---

### Task 3.2: Automatic Cleanup of Old Data

**Title**: Implement automatic cleanup of old checkpoints, logs, and telemetry

**Acceptance Criteria**:
- Clean up old checkpoints based on age and count limits
- Rotate log files based on size and age
- Archive old telemetry data
- Clean up old session data
- Configure cleanup policies
- Generate cleanup report

**Module**: Enhance `data/checkpoint_manager.py`, add `logic/cleanup_manager.py` (new)

**Estimated Lines**: ~300

**Dependencies**: V3 checkpoint_manager, telemetry_manager

**Technical Notes**:
- Cleanup policies:
  ```python
  cleanup_policy = {
      'checkpoints': {
          'max_age_hours': 24,
          'max_count': 10,
          'keep_critical': True
      },
      'logs': {
          'max_size_mb': 10,
          'backup_count': 5,
          'max_age_days': 7
      },
      'telemetry': {
          'archive_age_days': 30,
          'delete_age_days': 90
      },
      'sessions': {
          'max_sessions': 10,
          'max_age_days': 30
      }
  }
  ```
- Cleanup actions:
  - Delete old checkpoints
  - Rotate and compress log files
  - Archive old telemetry to separate database
  - Delete archived telemetry after retention period
- Cleanup report:
  ```
  Cleanup Summary:
  - Deleted 5 old checkpoints (freed 250MB)
  - Rotated 3 log files
  - Archived telemetry from 2024-12-01 to 2025-01-01
  - Deleted 2 old sessions
  ```
- CLI command:
  ```bash
  l4-dev cleanup --dry-run
  l4-dev cleanup --auto
  l4-dev cleanup --policy my_policy.json
  ```

---

### Task 3.3: Dependency Cleanup

**Title**: Identify and remove unused dependencies

**Acceptance Criteria**:
- Analyze imports in Python files to identify used packages
- Compare with requirements.txt / setup.py / pyproject.toml
- Identify unused dependencies (installed but not imported)
- Identify outdated dependencies (newer version available)
- Generate dependency cleanup report
- Support safe removal with backup

**Module**: `logic/dependency_analyzer.py` (new)

**Estimated Lines**: ~250

**Dependencies**: Task 1.2

**Technical Notes**:
- Dependency analysis:
  - Parse all Python files to extract imports
  - Map imports to package names (e.g., `from fastapi import FastAPI` → `fastapi`)
  - Compare with installed packages
- Report categories:
  - **Unused**: Installed but not imported
  - **Outdated**: Newer version available
  - **Pinned**: Exact version specified in requirements
- Safety checks:
  - Don't remove dependencies that are sub-dependencies
  - Don't remove dependencies with indirect usage (dynamic imports)
  - Create backup of requirements.txt before modification
- CLI command:
  ```bash
  l4-dev deps --unused              # Show unused dependencies
  l4-dev deps --outdated            # Show outdated dependencies
  l4-dev deps --cleanup             # Safe removal of unused dependencies
  ```

---

## Phase 4: Cost Optimization

### Task 4.1: LLM Call Cache ✅ **COMPLETE**

**Title**: Implement intelligent caching of LLM calls

**Acceptance Criteria**:
- [x] Cache LLM responses based on prompt hash
- [x] Support TTL for cached responses
- [x] Support semantic similarity matching (placeholder for future implementation)
- [x] Track cache hit/miss rates
- [x] Invalidate cache when context changes
- [x] Export cache statistics

**Module**: `data/llm_cache_manager.py` (new)

**Estimated Lines**: ~350

**Dependencies**: V3 telemetry, llm_base/provider

**Implementation**:
- Created `LLMCacheManager` with full caching functionality
- Implemented prompt hashing using SHA256
- TTL-based expiration with configurable hours
- Hit/miss tracking and statistics
- File-based cache invalidation
- Daily statistics aggregation
- 16 comprehensive unit tests all passing

**Status**: ✅ IMPLEMENTED - 2025-01-24

**Technical Notes**:
- Cache key: Hash of prompt + model + temperature
- Cache schema:
  ```sql
  CREATE TABLE llm_cache (
      prompt_hash TEXT PRIMARY KEY,
      prompt TEXT,
      response TEXT,
      model TEXT,
      temperature REAL,
      created_at DATETIME,
      expires_at DATETIME,
      hit_count INTEGER DEFAULT 0,
      last_hit DATETIME,
      similarity_enabled INTEGER DEFAULT 0
  );
  
  CREATE TABLE cache_stats (
      stat_date TEXT PRIMARY KEY,
      hits INTEGER DEFAULT 0,
      misses INTEGER DEFAULT 0,
      requests INTEGER DEFAULT 0,
      hit_rate REAL DEFAULT 0.0,
      tokens_saved INTEGER DEFAULT 0
  );
  ```
- Cache invalidation:
  - TTL-based (default 24 hours)
  - Context-based (invalidate when related files change)
  - Manual invalidation
- Semantic matching:
  - Placeholder implementation ready for embeddings
  - Match if similarity > threshold (e.g., 0.95)
- Expected savings: 30-40% reduction in LLM calls

---

### Task 4.2: Local Decision Making

**Title**: Implement local decision making to avoid LLM calls

**Acceptance Criteria**:
- Identify decisions that can be made without LLM
- Implement rule-based decision engine
- Implement decision trees for common scenarios
- Fall back to LLM for complex decisions
- Track decision accuracy
- Report savings from local decisions

**Module**: `logic/local_decision_engine.py` (new)

**Estimated Lines**: ~400

**Dependencies**: V4 reasoning_engine

**Technical Notes**:
- Decisions suitable for local logic:
  - File selection based on task impact (use AST, not LLM)
  - Simple context expansion rules
  - Basic error classification (transient vs permanent)
  - Retry logic for transient errors
  - Progress threshold validation
  - Basic trap detection (exact match loops)
- Decision tree example:
  ```python
  def should_retry_error(error, attempt_count):
      # Local decision, no LLM needed
      if error in RATE_LIMIT_ERRORS:
          return attempt_count < 3
      elif error in NETWORK_ERRORS:
          return attempt_count < 5
      elif error in PERMANENT_ERRORS:
          return False
      else:
          return None  # Fall back to LLM
  ```
- Expected savings: 20-30% reduction in LLM calls

---

### Task 4.3: Adaptive Token Budget

**Title**: Implement adaptive token budget management

**Acceptance Criteria**:
- Dynamically adjust token budget based on task complexity
- Start with minimal budget, expand if needed
- Track token usage per task type
- Predict token requirements for similar tasks
- Alert when approaching token budget limits
- Optimize token usage by pruning low-value context

**Module**: `logic/token_budget_manager.py` (new)

**Estimated Lines**: ~300

**Dependencies**: V4 context_engine, complexity_estimator

**Technical Notes**:
- Adaptive budgeting:
  - Simple task (bug fix): 1000 tokens
  - Medium task (new feature): 3000 tokens
  - Complex task (refactoring): 5000 tokens
  - Learn optimal budgets from historical data
- Budget expansion:
  - Start with minimal budget based on task type
  - Expand if task not completed within budget
  - Track expansion events for learning
- Token optimization:
  - Prune low-value context (low relevance score)
  - Summarize long contexts
  - Remove redundant information
- Expected savings: 15-20% reduction in token usage

---

### Task 4.4: Cost Tracking and Reporting

**Title**: Implement comprehensive cost tracking and reporting

**Acceptance Criteria**:
- Track LLM API costs (tokens × price)
- Track cost per task, per session, per project
- Track cost trends over time
- Predict future costs
- Generate cost reports
- Alert on cost overruns

**Module**: Enhance `data/telemetry_manager.py`, add `logic/cost_tracker.py` (new)

**Estimated Lines**: ~250

**Dependencies**: V3 telemetry_manager

**Technical Notes**:
- Cost tracking:
  - Track tokens used per LLM call
  - Track model used (GPT-4, GPT-3.5, Claude, etc.)
  - Calculate cost using model pricing
  - Track cache hits (no cost)
- Cost metrics:
  - Cost per task (avg, min, max)
  - Cost per session
  - Cost per project
  - Cost trend (increasing/decreasing)
- Cost prediction:
  - Predict cost for next N tasks
  - Predict monthly cost
  - Alert if predicted cost exceeds budget
- Cost report:
  ```
  Cost Report (2025-01-01 to 2025-01-24):
  - Total Cost: $15.67
  - Cost per Task: $2.34 (avg), $0.50 (min), $8.50 (max)
  - Tasks Completed: 7
  - Cache Hit Rate: 35% (saved $5.48)
  - Predicted Monthly Cost: $18.50
  ```
- CLI command:
  ```bash
  l4-dev cost --report
  l4-dev cost --by-task
  l4-dev cost --by-session
  l4-dev cost --trend
  ```

---

## Phase 5: Simplified Configuration

### Task 5.1: Smart Configuration Defaults ✅ **COMPLETE**

**Title**: Implement intelligent default configuration

**Acceptance Criteria**:
- [x] Remove need for most environment variables with smart defaults
- [x] Auto-detect optimal settings based on project size
- [x] Auto-detect optimal settings based on user machine
- [x] Provide configuration wizard for first-time users
- [x] Override defaults with explicit configuration
- [x] Document default values

**Module**: Enhanced `core/config.py`, added `core/config_wizard.py`

**Estimated Lines**: ~400

**Implementation**:
- Added `SmartDefaults` class with auto-detection of project size and system resources
- Added `ConfigWizard` class for interactive first-time setup
- Added built-in V5 profiles: minimal, balanced, max
- Enhanced `ConfigManager` to use smart defaults by default
- Version updated to 5.0.0

**Dependencies**: Existing config system

**Status**: ✅ IMPLEMENTED - 2025-01-24

**Technical Notes**:
- Smart defaults:
  ```python
  smart_defaults = {
      'cache_dir': '.l4_cache',
      'cache_enabled': True,
      'cache_size_mb': min(100, available_disk_space // 10),
      'max_depth': 3 if project_size < 'medium' else 2,
      'token_budget': 3000 if task_complexity == 'medium' else 1000,
      'llm_model': 'gpt-4' if budget_available else 'gpt-3.5-turbo',
      'adaptive_reasoning': True,
      'progress_tracking': True,
      'trap_detection': True
  }
  ```
- Auto-detection:
  - Project size: Count files, lines of code
  - Available resources: Disk space, RAM, CPU
  - Budget available: Ask user or estimate from usage
  - User preferences: Track past behavior
- Configuration wizard:
  ```bash
  $ l4-dev init
  Welcome to L4D Setup!
  
  Detected project: Medium (234 files, 15,432 lines)
  Available resources: 16GB RAM, 50GB disk space
  
  Configuration:
  [✓] Enable caching (recommended)
  [✓] Enable adaptive reasoning (recommended)
  [✓] Enable trap detection (recommended)
  [ ] Enable advanced features (requires more resources)
  
  LLM Model:
  [1] GPT-4 (best quality, higher cost)
  [2] GPT-3.5-turbo (good quality, lower cost) [recommended]
  [3] Claude (alternative)
  
  Select model [1-3]: 2
  
  Configuration saved to .l4_config.json
  ```

---

### Task 5.2: Configuration Validation

**Title**: Implement configuration validation and error reporting

**Acceptance Criteria**:
- Validate all configuration values
- Detect conflicting settings
- Detect deprecated settings
- Provide clear error messages
- Suggest fixes for invalid settings
- Support configuration migration

**Module**: Enhance `core/config.py`

**Estimated Lines**: ~200

**Dependencies**: Task 5.1

**Technical Notes**:
- Validation rules:
  - Type checking (string, int, float, bool)
  - Range checking (0-1 for probabilities, positive integers)
  - Path validation (directories exist, writable)
  - LLM API key validation
- Conflict detection:
  - Cannot have both cache_enabled=False and adaptive_reasoning=True
  - Cannot have token_budget > max_model_context
  - Cannot have cache_size_mb > available_disk_space
- Error messages:
  ```
  Configuration Error: Invalid token_budget
  - Value: 100000
  - Maximum allowed: 32000 (model: gpt-4)
  - Suggestion: Set token_budget to 3000 or use a model with larger context
  ```
- Migration:
  - Detect deprecated settings
  - Auto-migrate to new settings
  - Warn user about migration
  - Backup old configuration

---

### Task 5.3: Configuration Profiles

**Title**: Implement configuration profiles for different use cases

**Acceptance Criteria**:
- Define profiles for different use cases (development, production, testing)
- Support custom profiles
- Switch between profiles easily
- Inherit from base profiles
- Override specific settings per profile
- Generate profile comparison

**Module**: Enhance `core/config.py`

**Estimated Lines**: ~250

**Dependencies**: Task 5.1

**Technical Notes**:
- Built-in profiles:
  ```python
  profiles = {
      'minimal': {
          'description': 'Minimal configuration for small projects',
          'cache_enabled': True,
          'cache_size_mb': 50,
          'adaptive_reasoning': False,
          'progress_tracking': False,
          'trap_detection': False,
          'llm_model': 'gpt-3.5-turbo',
          'token_budget': 2000
      },
      'balanced': {
          'description': 'Balanced configuration for most use cases',
          'cache_enabled': True,
          'cache_size_mb': 100,
          'adaptive_reasoning': True,
          'progress_tracking': True,
          'trap_detection': True,
          'llm_model': 'gpt-4',
          'token_budget': 3000
      },
      'max': {
          'description': 'Maximum features for large projects',
          'cache_enabled': True,
          'cache_size_mb': 500,
          'adaptive_reasoning': True,
          'progress_tracking': True,
          'trap_detection': True,
          'llm_model': 'gpt-4',
          'token_budget': 5000
      }
  }
  ```
- Profile inheritance:
  ```python
  custom_profile = {
      'inherits': 'balanced',
      'overrides': {
          'token_budget': 4000,
          'cache_size_mb': 200
      }
  }
  ```
- CLI commands:
  ```bash
  l4-dev profile list              # List all profiles
  l4-dev profile show balanced     # Show profile details
  l4-dev profile use minimal       # Switch to minimal profile
  l4-dev profile diff balanced max  # Compare profiles
  ```

---

## Phase 6: Progressive Context Management

### Task 6.1: Minimal Context Starter

**Title**: Implement minimal context loading for simple tasks

**Acceptance Criteria**:
- Start with minimal context (only current file)
- Expand context only when needed
- Use heuristics to predict if expansion needed
- Track expansion frequency per task type
- Learn optimal starting context per task type
- Reduce initial token usage by 40%

**Module**: Enhance `logic/context_engine.py` (V2)

**Estimated Lines**: ~300

**Dependencies**: V4 context_hierarchy, context_expander

**Technical Notes**:
- Minimal context strategy:
  - **Level 0**: Only current file and immediate dependencies (imports)
  - **Level 1**: Add functions that call current function (upstream)
  - **Level 2**: Add functions called by current function (downstream)
  - **Level 3**: Full context (as in V4)
- Expansion heuristics:
  - Expand if task complexity > threshold
  - Expand if LLM request needs clarification
  - Expand if progress is stalled
  - Expand if error occurs
- Learning:
  - Track which level succeeded for each task type
  - Start with learned optimal level next time
- Expected savings: 30-40% reduction in initial context tokens

---

### Task 6.2: Context Relevance Filtering

**Title**: Implement relevance-based context filtering

**Acceptance Criteria**:
- Score context items by relevance to current task
- Filter out low-relevance items (< 0.3 score)
- Include high-relevance items (> 0.7 score)
- Allow medium-relevance items (0.3-0.7) based on token budget
- Update relevance scores based on LLM feedback
- Track relevance accuracy

**Module**: Enhance `logic/context_scorer.py` (V4)

**Estimated Lines**: ~200

**Dependencies**: V4 context_scorer

**Technical Notes**:
- Relevance factors (already in V4, but refine):
  - **Recency**: More recent = higher relevance (0-1)
  - **Similarity**: Semantic similarity to task (0-1)
  - **Dependency**: Direct/indirect dependency (0.5-1)
  - **Impact**: High-impact changes = higher relevance (0-1)
- Scoring formula:
  ```python
  score = 0.2*recency + 0.3*similarity + 0.3*dependency + 0.2*impact
  ```
- Filtering strategy:
  - Always include: score > 0.7
  - Include if space: 0.3 < score <= 0.7
  - Exclude: score <= 0.3
- Learning:
  - Track which filtered items were actually needed
  - Adjust weights based on accuracy

---

### Task 6.3: Context Compression

**Title**: Implement intelligent context compression

**Acceptance Criteria**:
- Compress long contexts using LLM summarization
- Preserve critical details (signatures, key logic)
- Remove verbose details (comments, whitespace)
- Use different compression levels based on importance
- Cache compressed contexts
- Track compression ratio

**Module`: `logic/context_compressor.py` (new)

**Estimated Lines**: ~250

**Dependencies**: V4 context_summarizer

**Technical Notes**:
- Compression levels:
  - **Level 0**: No compression (full context)
  - **Level 1**: Remove comments, docstrings, whitespace (20-30% reduction)
  - **Level 2**: Summarize functions with signatures only (40-50% reduction)
  - **Level 3**: Summarize entire file (60-70% reduction)
- Compression strategy:
  - Use Level 1 for L0-L1 contexts (recent)
  - Use Level 2 for L2 contexts (session)
  - Use Level 3 for L3 contexts (project)
- Preservation rules:
  - Always preserve function signatures
  - Always preserve class definitions
  - Always preserve imports
  - Always preserve critical logic (detected by complexity)
  - Preserve comments with TODO, FIXME, HACK
- Expected savings: 25-35% reduction in context tokens

---

## Phase 7: Quality Enhancement

### Task 7.1: Context Quality Metrics

**Title**: Implement metrics to measure context quality

**Acceptance Criteria**:
- Define context quality metrics (completeness, relevance, freshness)
- Measure context quality for each task
- Track context quality over time
- Correlate context quality with task success
- Generate context quality reports
- Improve context quality based on metrics

**Module**: `logic/context_quality_tracker.py` (new)

**Estimated Lines**: ~300

**Dependencies**: V4 context_scorer

**Technical Notes**:
- Quality metrics:
  - **Completeness**: % of required context items included
  - **Relevance**: Average relevance score of included items
  - **Freshness**: Average age of context items (newer = better)
  - **Conciseness**: Information density (more = better)
  - **Diversity**: Variety of context sources (files, modules)
- Quality calculation:
  ```python
  quality = (
      0.3*completeness +
      0.3*relevance +
      0.2*freshness +
      0.1*conciseness +
      0.1*diversity
  )
  ```
- Correlation analysis:
  - Track success rate per quality level
  - Identify quality threshold for optimal performance
- Quality report:
  ```
  Context Quality Report:
  - Average Quality: 0.78 (out of 1.0)
  - Completeness: 0.85
  - Relevance: 0.76
  - Freshness: 0.72
  - Conciseness: 0.68
  - Diversity: 0.82
  
  Tasks with quality > 0.75: 92% success rate
  Tasks with quality < 0.50: 45% success rate
  ```

---

### Task 7.2: Automated Context Improvement

**Title**: Implement automated context improvement based on metrics

**Acceptance Criteria**:
- Identify low-quality contexts
- Suggest context improvements automatically
- Apply improvements with user approval
- Track improvement effectiveness
- Learn from successful improvements
- Generate improvement suggestions

**Module**: Enhance `logic/context_engine.py` (V2)

**Estimated Lines**: ~250

**Dependencies**: Task 7.1

**Technical Notes**:
- Improvement suggestions:
  - **Low Completeness**: Add missing dependencies
  - **Low Relevance**: Replace low-relevance items with high-relevance ones
  - **Low Freshness**: Update stale context items
  - **Low Conciseness**: Compress verbose contexts
  - **Low Diversity**: Add context from different sources
- Automated improvement:
  ```python
  if context_quality < threshold:
      suggestions = generate_improvements(context, quality_metrics)
      for suggestion in suggestions:
          if suggestion.confidence > 0.8:
              apply_suggestion(suggestion)
          else:
              ask_user(suggestion)
  ```
- Learning:
  - Track which improvements succeeded
  - Learn to predict which improvements work
  - Automate high-confidence improvements
- Expected improvement: 15-20% increase in task success rate

---

### Task 7.3: Layered Context Architecture

**Title**: Implement layered context architecture for progressive loading

**Acceptance Criteria**:
- Define context layers (immediate, recent, session, project)
- Load layers progressively as needed
- Cache frequently used layers
- Prioritize layers based on task needs
- Track layer usage patterns
- Optimize layer loading based on patterns

**Module**: Enhance `data/context_hierarchy.py` (V4)

**Estimated Lines**: ~350

**Dependencies**: V4 context_hierarchy

**Technical Notes**:
- Context layers:
  - **Layer 0 (Immediate)**: Current file, current function, immediate dependencies
  - **Layer 1 (Recent)**: Last 10 actions, last 5 errors, recent telemetry
  - **Layer 2 (Session)**: Session history, task progress, patterns learned
  - **Layer 3 (Project)**: Project state, architecture, long-term patterns
- Progressive loading:
  - Always load Layer 0 (fast, minimal)
  - Load Layer 1 if task needs recent context
  - Load Layer 2 if task needs session context
  - Load Layer 3 if task needs project context
- Layer prioritization:
  - Learn which layers are needed for each task type
  - Pre-load frequently used layers
  - Lazy load rarely used layers
- Caching:
  - Keep Layer 0 in memory (hot)
  - Cache Layer 1 in memory (warm)
  - Cache Layer 2 on disk (cold)
  - Load Layer 3 on demand
- Expected benefit: 30-40% reduction in initial load time

---

## Phase 8: User Experience Improvements

### Task 8.1: Simplified CLI Interface

**Title**: Simplify CLI interface for ease of use

**Acceptance Criteria**:
- Reduce number of required commands
- Provide sensible defaults for all commands
- Add interactive mode for beginners
- Provide helpful error messages with suggestions
- Add command auto-completion
- Document common workflows

**Module**: Enhance `v4/l4_cli.py`

**Estimated Lines**: ~400

**Dependencies**: Existing CLI

**Technical Notes**:
- Simplified commands:
  ```bash
  # V4 (complex)
  l4-dev start --config my_config.json --profile production --verbose
  
  # V5 (simple)
  l4-dev start    # Uses smart defaults from V5.1
  
  # Interactive mode
  l4-dev start --interactive
  > What would you like to do?
  > [1] Implement a new feature
  > [2] Fix a bug
  > [3] Refactor code
  > [4] Run tests
  > Selection: 1
  > Describe the feature: Add user authentication
  ```
- Error messages with suggestions:
  ```
  Error: Git repository is not clean
  - Uncommitted changes in: core/start.py, logic/implementor.py
  - Suggestion: Run 'git commit' or 'git stash' before continuing
  - Or run with --force to proceed anyway (not recommended)
  ```
- Auto-completion:
  - Bash completion script
  - Fish completion script
  - Zsh completion script
- Common workflows:
  ```bash
  l4-dev workflow simple          # Simple feature implementation
  l4-dev workflow complex         # Complex feature with planning
  l4-dev workflow debug           # Debug failing tests
  l4-dev workflow refactor        # Refactor code
  ```

---

### Task 8.2: Quick Start Guide

**Title**: Implement quick start guide for new users

**Acceptance Criteria**:
- Provide step-by-step setup instructions
- Include example project structure
- Include example tasks and expected outputs
- Include troubleshooting section
- Provide video tutorial (optional)
  - Provide interactive tutorial

**Module**: `docs/QUICKSTART.md` (new)

**Estimated Lines**: ~600

**Dependencies**: All V5 features

**Technical Notes**:
- Quick start structure:
  ```markdown
  # L4D Quick Start Guide
  
  ## 1. Installation
  pip install l4d
  
  ## 2. Initialize Project
  cd my_project
  l4-dev init
  
  ## 3. Configure
  l4-dev config wizard
  
  ## 4. First Task
  l4-dev start --task "Add user login feature"
  
  ## 5. Monitor Progress
  l4-dev progress
  
  ## 6. View Results
  l4-dev report
  ```
- Example project:
  ```
  my_project/
  ├── product.md          # Product requirements
  ├── technical.md        # Technical specifications
  ├── src/
  │   ├── __init__.py
  │   ├── main.py
  │   └── utils.py
  └── tests/
      ├── __init__.py
      └── test_main.py
  ```
- Example outputs:
  ```
  $ l4-dev start --task "Add user login feature"
  
  [INFO] Starting L4D...
  [INFO] Task: Add user login feature
  [INFO] Analyzing requirements...
  [INFO] Creating task breakdown...
  [INFO] Created 5 subtasks
  [INFO] Starting task 1/5: Create user model
  [INFO] Writing test: test_user_model.py
  [INFO] Implementing: models/user.py
  [INFO] Running tests... PASSED
  [INFO] Committing: Add user model
  [INFO] Task 1/5 completed
  ...
  [SUCCESS] All tasks completed!
  ```
- Interactive tutorial:
  ```bash
  l4-dev tutorial
  Welcome to L4D Interactive Tutorial!
  
  Lesson 1: Basic Task
  Let's implement a simple function that adds two numbers.
  
  Step 1: Create a task
  $ l4-dev start --task "Add a function to add two numbers"
  
  [Press Enter to continue...]
  ```

---

### Task 8.3: Progressive Documentation

**Title**: Implement progressive documentation for different user levels

**Acceptance Criteria**:
- Provide beginner documentation (simple concepts, examples)
- Provide intermediate documentation (advanced features, best practices)
- Provide expert documentation (internals, customization)
- Provide quick reference for common tasks
- Provide API reference for developers
- Update documentation automatically

**Module**: Update `docs/` directory structure

**Estimated Lines**: ~2000 (total documentation)

**Dependencies**: All V5 features

**Technical Notes**:
- Progressive documentation structure:
  ```
  docs/
  ├── beginner/
  │   ├── QUICKSTART.md
  │   ├── BASIC_TASKS.md
  │   ├── COMMON_WORKFLOWS.md
  │   └── TROUBLESHOOTING.md
  ├── intermediate/
  │   ├── ADVANCED_FEATURES.md
  │   ├── BEST_PRACTICES.md
  │   ├── CONFIGURATION.md
  │   └── OPTIMIZATION.md
  ├── expert/
  │   ├── ARCHITECTURE.md
  │   ├── CUSTOMIZATION.md
  │   ├── INTERNALS.md
  │   └── EXTENDING.md
  ├── reference/
  │   ├── API.md
  │   ├── CLI.md
  │   └── CONFIG.md
  └── tutorials/
      ├── BASIC_TUTORIAL.md
      ├── ADVANCED_TUTORIAL.md
      └── EXPERT_TUTORIAL.md
  ```
- Beginner documentation:
  - Simple language, lots of examples
  - Focus on common use cases
  - Hide complexity behind simple commands
  - Provide copy-paste examples
- Intermediate documentation:
  - Explain concepts in detail
  - Cover advanced features
  - Best practices and patterns
  - Performance optimization
- Expert documentation:
  - Deep dive into internals
  - Extending and customizing
  - Architecture details
  - Contributing guidelines
- Auto-update:
  - Extract documentation from code comments
  - Generate API reference from docstrings
  - Update examples based on latest version

---

## Implementation Order

### Priority 1 (High Impact, Low Risk)
- Task 5.1: Smart Configuration Defaults
- Task 4.1: LLM Call Cache
- Task 6.1: Minimal Context Starter

### Priority 2 (Foundational Infrastructure)
- Task 1.1: Enhanced AST Analysis with Call Graph Persistence
- Task 1.2: Import Dependency Analysis
- Task 1.3: File Usage Tracker

### Priority 3 (Core Housekeeping)
- Task 2.1: Dead Function Detection
- Task 2.2: Dead Class Detection
- Task 2.3: Unused Variable Detection
- Task 3.1: Safe Deletion Pipeline

### Priority 4 (Cost Optimization)
- Task 4.2: Local Decision Making
- Task 4.3: Adaptive Token Budget
- Task 4.4: Cost Tracking and Reporting

### Priority 5 (Quality Enhancement)
- Task 6.2: Context Relevance Filtering
- Task 6.3: Context Compression
- Task 7.1: Context Quality Metrics
- Task 7.2: Automated Context Improvement
- Task 7.3: Layered Context Architecture

### Priority 6 (User Experience)
- Task 5.2: Configuration Validation
- Task 5.3: Configuration Profiles
- Task 8.1: Simplified CLI Interface
- Task 8.2: Quick Start Guide
- Task 8.3: Progressive Documentation

### Priority 7 (Cleanup)
- Task 3.2: Automatic Cleanup of Old Data
- Task 3.3: Dependency Cleanup

---

## Success Metrics

### Housekeeping Effectiveness
- **Goal**: Identify and safely remove 80% of dead code
- **Measurement**: Compare dead code detected vs total code, verify no test failures

### Cost Optimization
- **Goal**: Reduce LLM API costs by 40%
- **Measurement**: Compare cost per task before and after V5

### Token Usage Reduction
- **Goal**: Reduce token usage by 30%
- **Measurement**: Compare average tokens per task before and after V5

### Configuration Simplicity
- **Goal**: Reduce required configuration variables by 70%
- **Measurement**: Count configuration variables before and after V5

### Context Quality
- **Goal**: Improve context quality score by 20%
- **Measurement**: Track context quality metrics over time

### Task Success Rate
- **Goal**: Improve task success rate by 15%
- **Measurement**: Compare success rate before and after V5

### User Onboarding Time
- **Goal**: Reduce onboarding time to < 30 minutes
- **Measurement**: Time from installation to first successful task

### Documentation Coverage
- **Goal**: Provide documentation for 100% of features
- **Measurement**: Count features with and without documentation

---

## Required Updates to Meta Documents

### meta/prd.md Updates Needed

**New Section: V5 Philosophy - Simplicity and Effectiveness**:
- Describe simplified workflow philosophy
- Describe progressive context management
- Describe cost optimization goals
- Describe quality enhancement approach

**New Section: Housekeeping Capabilities**:
- Describe automatic code cleanup
- Describe dependency management
- Describe data cleanup

**New Section: Cost Optimization**:
- Describe LLM call caching
- Describe local decision making
- Describe adaptive token budgeting
- Describe cost tracking

**Update Section 3 (Agent Specifications)**:
- Update agents to use minimal context
- Update agents to use local decisions
- Update agents to track cost

**New Section: V5 Enhancements**:
- Document all V5 features
- Document simplifications
- Document cost savings

---

### meta/tech.md Updates Needed

**Section 1.2 (The Context Bank)**:
- Add `call_graph.db` for persistent call graphs
- Add `llm_cache.db` for LLM response caching
- Add `cost_tracker.db` for cost tracking

**Section 2 (Module Hierarchy Reference)**:
- Add new modules in `logic/`:
  - `logic/import_analyzer.py` - Import dependency analysis
  - `logic/file_usage_tracker.py` - File usage tracking
  - `logic/dead_code_detector.py` - Dead code detection
  - `logic/housekeeping_pipeline.py` - Safe deletion pipeline
  - `logic/dependency_analyzer.py` - Dependency analysis
  - `logic/llm_cache.py` - LLM call caching
  - `logic/local_decision_engine.py` - Local decision making
  - `logic/token_budget_manager.py` - Token budget management
  - `logic/cost_tracker.py` - Cost tracking
  - `logic/context_compressor.py` - Context compression
  - `logic/context_quality_tracker.py` - Context quality metrics
- Enhance existing modules:
  - `data/semantic_mapper.py` - Add call graph persistence
  - `data/checkpoint_manager.py` - Add cleanup policies
  - `core/config.py` - Add smart defaults and profiles
  - `logic/context_engine.py` - Add minimal context strategy

**Section 3 (Functional Modules to Develop)**:
- Add descriptions for all new V5 modules

**Section 4 (Operational Flow Summary)**:
- Update flow to use minimal context
- Add LLM caching
- Add local decision making
- Add cost tracking

**New Section: V5 Configuration**:
- Document smart defaults
- Document configuration profiles
- Document configuration validation

**New Section: V5 Module Dependencies**:
- Update dependency graph to include new V5 modules

---

## Risks and Mitigations

### Risk 1: Housekeeping Removes Needed Code
- **Mitigation**: Extensive testing before deletion, backup/rollback, conservative deletion criteria
- **Fallback**: Manual review of all deletions, require confirmation
- **Monitoring**: Track deletions, monitor for issues after deletion

### Risk 2: LLM Cache Returns Stale Results
- **Mitigation**: Cache invalidation based on file changes, TTL, semantic similarity
- **Fallback**: Disable cache for critical operations
- **Monitoring**: Track cache accuracy, alert on potential issues

### Risk 3: Local Decisions Are Wrong
- **Mitigation**: Conservative decisions, fall back to LLM for complex cases
- **Fallback**: Allow user to override decisions
- **Monitoring**: Track decision accuracy, adjust rules based on feedback

### Risk 4: Minimal Context Misses Critical Information
- **Mitigation**: Progressive expansion, quality metrics, learning from failures
- **Fallback**: Fall back to full context if task fails
- **Monitoring**: Track task success rate per context level

### Risk 5: Smart Defaults Don't Work for All Projects
- **Mitigation**: Allow manual override, provide multiple profiles
- **Fallback**: Manual configuration wizard
- **Monitoring**: Track default usage, adjust based on feedback

### Risk 6: Cost Optimization Reduces Quality
- **Mitigation**: Quality metrics, validate against baseline
- **Fallback**: Disable optimization for quality-critical tasks
- **Monitoring**: Track quality metrics alongside cost savings

---

## Future Enhancements (Beyond V5)

1. **Collaborative Housekeeping**: Share housekeeping patterns across projects
2. **ML-Based Dead Code Detection**: Use ML to identify dead code more accurately
3. **Cross-Language Support**: Housekeeping for JavaScript, TypeScript, Go, etc.
4. **Predictive Housekeeping**: Predict code that will become unused
5. **Cost Optimization Marketplace**: Share cost optimization strategies
6. **Automated Refactoring**: Not just remove, but refactor dead code
7. **Dependency Upgrade Automation**: Automatic dependency upgrades with testing
8. **Real-time Context Quality**: Continuous monitoring and improvement
9. **User Behavior Learning**: Learn user preferences and adapt defaults
10. **Self-Optimizing System**: System automatically tunes itself for optimal performance

---

## Summary

V5 transforms L4D from a powerful but complex tool into a **simple, effective, and cost-efficient** development companion with:

**Key Capabilities**:
- Automatic housekeeping (dead code detection, cleanup, dependency management)
- Simplified configuration (smart defaults, profiles, validation)
- Cost optimization (LLM caching, local decisions, adaptive budgeting)
- Progressive context (minimal starter, relevance filtering, compression)
- Quality enhancement (quality metrics, automated improvement, layered architecture)
- User experience improvements (simplified CLI, quick start, progressive docs)

**Benefits**:
- 80% of dead code safely removed
- 40% reduction in LLM API costs
- 30% reduction in token usage
- 70% reduction in required configuration
- 20% improvement in context quality
- 15% improvement in task success rate
- 30-minute onboarding time
- 100% documentation coverage

**Core Philosophy**: **"Start Simple, Expand as Needed"** - Begin with minimal context and configuration, expand progressively only when necessary, optimize for cost without sacrificing quality, and provide a simple, effective user experience.

**Architecture**: Built on V4's adaptive reasoning foundation, adding housekeeping, cost optimization, progressive context, and user experience layers for a simpler, more efficient development experience.