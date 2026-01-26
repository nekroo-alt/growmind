# Migration Guide: V5 to V6

This guide helps you upgrade from V5 to V6 of the L4 Self-Evolving Development Platform.

---

## Table of Contents

1. [Overview](#overview)
2. [Breaking Changes](#breaking-changes)
3. [CLI Command Changes](#cli-command-changes)
4. [Configuration Changes](#configuration-changes)
5. [Upgrade Steps](#upgrade-steps)
6. [Rollback Steps](#rollback-steps)
7. [Troubleshooting](#troubleshooting)

---

## Overview

V6 represents a major restructuring and cleanup release focused on:
- **Code Organization**: Eliminated duplicate CLI files and consolidated test structure
- **Modular Architecture**: Created dedicated modules for CLI commands and utilities
- **Dead Code Removal**: Implemented comprehensive dead code detection and removal
- **Test Organization**: Moved all tests into proper `v5/tests/` directory structure
- **Documentation**: Updated README.md to V6.0 with comprehensive documentation

**Key Changes**:
- Single consolidated CLI file (`l4_cli.py`)
- Modular CLI structure (`v5/cli/v3_commands.py`, `v4_commands.py`, `v5_commands.py`)
- Utilities module (`v5/utilities/`)
- Test reorganization by feature/component
- Enhanced documentation and examples

---

## Breaking Changes

### 1. CLI Entry Point Changes

**V5 Entry Point**:
```python
# setup.py (V5)
entry_points={
    'console_scripts': [
        'l4-dev=v5.l4_cli_v5_new:main'  # Incorrect entry point
    ]
}
```

**V6 Entry Point**:
```python
# setup.py (V6)
entry_points={
    'console_scripts': [
        'l4-dev=v5.l4_cli:main'  # Corrected to single CLI file
    ]
}
```

**Impact**: The CLI entry point has been corrected. After upgrade, `l4-dev --help` will show all V3, V4, and V5 commands from a single source.

### 2. Duplicate CLI Files Removed

**Removed Files**:
- `v5/l4_cli_v5_new.py` (deleted - was duplicate with stub implementations)

**Kept File**:
- `v5/l4_cli.py` (consolidated with all V3, V4, V5 commands)

**Impact**: No changes to CLI command usage. All commands remain available but now from a single source file.

### 3. Test Files Moved

**Root-level test files removed** (deleted in V6):
- `test_debug_cycle.py`
- `test_debug_failures.py`
- `test_debug_no_cycle.py`
- `test_file_usage_minimal.py`
- `test_file_usage_tracker_standalone.py`
- `test_import_analyzer_direct.py`
- `test_token_budget_simple.py`
- `verify_blocked.py`

**New test structure**:
- `v5/tests/unit/core/` (2 files)
- `v5/tests/unit/data/` (2 files)
- `v5/tests/unit/logic/` (32 files)

**Impact**: If you had scripts referencing these root-level test files, update paths to use `v5/tests/unit/` structure.

### 4. Import Path Changes

**V5 Imports**:
```python
from l4_cli import main
from test_file_usage_tracker import FileUsageTracker
```

**V6 Imports**:
```python
from v5.l4_cli import main
from v5.tests.unit.test_file_usage_tracker import FileUsageTracker
```

**Impact**: Update import statements in your code to use `v5.` prefix for V5 modules.

---

## CLI Command Changes

### V3 Commands (unchanged)

All V3 commands remain available and work the same:

```bash
l4-dev start                    # Start development session
l4-dev status                   # Show current status
l4-dev logs                     # View logs
l4-dev health                   # Health check
l4-dev telemetry                # Telemetry data
l4-dev checkpoints              # List checkpoints
l4-dev sessions                 # List sessions
l4-dev resume <session_id>       # Resume session
l4-dev recover                  # Recovery mode
```

### V4 Commands (unchanged)

All V4 commands remain available and work the same:

```bash
l4-dev decisions                # View decision history
l4-dev explain <decision_id>    # Explain a decision
l4-dev progress                 # Show progress
```

### V5 Commands (unchanged)

All V5 commands remain available and work the same:

```bash
l4-dev workflow <type>          # Run workflow (simple, complex, debug, refactor)
l4-dev housekeep [options]       # Housekeeping operations
l4-dev cleanup [options]        # Cleanup old data
l4-dev cost [options]            # Cost tracking
l4-dev deps [options]            # Dependency management
l4-dev quality [options]         # Quality reporting
l4-dev profile                   # Performance profiling
```

### New V6 Documentation

**New CLI Documentation**:
- Updated README.md with V6.0 features
- Enhanced examples with V5-V6 features
- Updated troubleshooting section
- Performance metrics comparison table (V2-V5-V6)

---

## Configuration Changes

### Environment Variables (no changes)

All V5 environment variables remain unchanged in V6:

```bash
# Core Configuration
L4_PROFILE=balanced
L4_LLM_PROVIDER=openai
L4_LLM_MODEL=gpt-4
L4_LLM_API_KEY=your_api_key

# Optional: Cost Controls
L4_COST_BUDGET=100
L4_COST_ALERT_THRESHOLD=0.8

# Optional: Context Control
L4_START_CONTEXT_LEVEL=0
L4_MAX_TOKEN_BUDGET=4000

# Optional: Housekeeping
L4_AUTO_HOUSEKEEP=true
L4_HOUSEKEEP_INTERVAL=24

# Optional: Caching
L4_LLM_CACHE_ENABLED=true
L4_CACHE_TTL_HOURS=24
```

**Impact**: No configuration changes required. Your existing V5 configuration will work in V6.

### Configuration Profiles (unchanged)

All V5 configuration profiles remain unchanged:

```bash
l4-dev profile list              # List all profiles
l4-dev profile use balanced       # Switch to balanced profile
l4-dev profile diff balanced max  # Compare profiles
```

**Available Profiles**:
- `minimal` - For small projects, low budget
- `balanced` - Default for most projects
- `max` - For complex projects, high budget

---

## Upgrade Steps

### Prerequisites

1. **Backup Your Data**:
   ```bash
   # Backup important databases
   cp task.db task.db.backup
   cp activity.db activity.db.backup
   cp telemetry.db telemetry.db.backup
   cp sessions.db sessions.db.backup
   
   # Backup cache and checkpoints
   cp -r .l4_cache .l4_cache.backup
   cp -r checkpoints checkpoints.backup
   ```

2. **Check Current Version**:
   ```bash
   l4-dev --version
   # Expected: 5.0.0
   ```

3. **Clean Git Workspace**:
   ```bash
   git status
   # Ensure workspace is clean (no uncommitted changes)
   ```

### Step 1: Upgrade via pip

```bash
# Upgrade to V6
pip install --upgrade l4-dev

# Verify installation
l4-dev --version
# Expected: 6.0.0
```

### Step 2: Verify CLI Entry Point

```bash
# Test CLI help
l4-dev --help

# Expected output should show all V3, V4, V5 commands
```

### Step 3: Test Core Commands

```bash
# Test V3 commands
l4-dev status
l4-dev health

# Test V4 commands
l4-dev decisions
l4-dev progress

# Test V5 commands
l4-dev cost --report
l4-dev quality --report
```

### Step 4: Run Health Check

```bash
# Run comprehensive health check
l4-dev health --verbose

# Expected: All checks should pass
```

### Step 5: Run Test Suite

```bash
# Run unit tests
cd v5
pytest tests/unit/ -v

# Expected: All tests should pass (211+ tests passing)
```

### Step 6: Verify Housekeeping

```bash
# Test housekeeping (dry-run first)
l4-dev housekeep --dry-run

# If no issues, run automatic housekeeping
l4-dev housekeep --auto
```

### Step 7: Check Documentation

```bash
# View updated README
cat README.md

# Note: Updated to V6.0 with new features and examples
```

### Step 8: Verify Import Paths (if you have custom code)

If you have custom code that imports L4D modules:

```python
# Update import statements if needed
# V5: from l4_cli import main
# V6: from v5.l4_cli import main
```

---

## Rollback Steps

If you encounter issues after upgrading to V6, you can rollback to V5.

### Step 1: Uninstall V6

```bash
pip uninstall l4-dev
```

### Step 2: Reinstall V5

```bash
pip install l4-dev==5.0.0
```

### Step 3: Restore Backup Data

```bash
# Restore databases
cp task.db.backup task.db
cp activity.db.backup activity.db
cp telemetry.db.backup telemetry.db
cp sessions.db.backup sessions.db

# Restore cache and checkpoints
cp -r .l4_cache.backup .l4_cache
cp -r checkpoints.backup checkpoints
```

### Step 4: Verify Rollback

```bash
# Verify version
l4-dev --version
# Expected: 5.0.0

# Test CLI
l4-dev --help
l4-dev status
```

---

## Troubleshooting

### Issue: CLI Not Found After Upgrade

**Symptom**: `l4-dev: command not found`

**Solution**:
```bash
# Reinstall with explicit path
pip install --upgrade --force-reinstall l4-dev

# Check installation location
which l4-dev

# Ensure pip bin directory is in PATH
echo $PATH
```

### Issue: Import Errors in Custom Code

**Symptom**: `ModuleNotFoundError: No module named 'l4_cli'`

**Solution**:
```python
# Update import statements
# Old: from l4_cli import main
# New: from v5.l4_cli import main

# Or use package-relative imports
from .l4_cli import main
```

### Issue: Test Failures After Upgrade

**Symptom**: Tests fail after upgrading to V6

**Solution**:
```bash
# Run tests with verbose output to see detailed errors
pytest v5/tests/unit/ -v

# If tests reference deleted root-level files, update paths
# Example: update test_file_usage_minimal.py references
# to use v5/tests/unit/test_file_usage_tracker.py
```

### Issue: Housekeeping Errors

**Symptom**: Housekeeping commands fail or report errors

**Solution**:
```bash
# Run health check first
l4-dev health --verbose

# Run housekeeping with dry-run to preview
l4-dev housekeep --dry-run --verbose

# If errors persist, check logs
l4-dev logs --tail 50
```

### Issue: Missing Test Files

**Symptom**: Can't find test files that existed in V5

**Solution**:
```bash
# Root-level test files were moved to v5/tests/unit/
# Update your test runner or scripts
pytest v5/tests/unit/ -v

# List all test files
find v5/tests/unit/ -name "test_*.py"
```

### Issue: Documentation Links Broken

**Symptom**: Documentation links don't work after upgrade

**Solution**:
```bash
# Check README.md for updated links
cat README.md

# V5-V6 specific documentation
cat v5/docs/MIGRATION_V5_TO_V6.md
```

---

## Additional Resources

### Documentation

- **README.md**: Updated V6.0 documentation with new features
- **meta/prd.md**: Product requirements (unchanged)
- **meta/tech.md**: Technical architecture (unchanged)
- **v5/v6_tasks.md**: V6 task completion status
- **v5/docs/**: Comprehensive V5-V6 documentation

### CLI Help

```bash
# Get help on specific commands
l4-dev --help
l4-dev start --help
l4-dev housekeep --help
l4-dev cost --help
```

### Support

If you encounter issues not covered in this guide:

1. Check the troubleshooting section above
2. Run `l4-dev health --verbose` to diagnose issues
3. Review logs with `l4-dev logs`
4. Consult the documentation in `v5/docs/`

---

## Summary of Changes

| Component | V5 | V6 | Notes |
|-----------|----|----|-------|
| CLI Files | 2 files (duplicate) | 1 file (consolidated) | `l4_cli_v5_new.py` deleted |
| CLI Entry Point | Incorrect | Corrected | Points to `v5.l4_cli:main` |
| Test Structure | Root-level | Organized in `v5/tests/unit/` | 8 root-level files deleted |
| Utilities | Scattered | Centralized in `v5/utilities/` | New module structure |
| Documentation | V5.0 | V6.0 | Updated with new features |
| Dead Code Detection | Not implemented | Fully implemented | New housekeeping commands |
| Configuration | Same | Same | No breaking changes |

---

**Migration Guide Version**: 1.0  
**Last Updated**: 2026-01-27  
**Maintainer**: L4D Development Team