# L4D Troubleshooting Guide

This guide helps you resolve common issues when using L4D.

## Table of Contents

1. [Installation Issues](#1-installation-issues)
2. [Configuration Issues](#2-configuration-issues)
3. [Task Execution Issues](#3-task-execution-issues)
4. [LLM API Issues](#4-llm-api-issues)
5. [Git Integration Issues](#5-git-integration-issues)
6. [Performance Issues](#6-performance-issues)
7. [Getting Help](#7-getting-help)

---

## 1. Installation Issues

### Issue: "pip install fails"

**Problem**: Installation fails with dependency errors.

**Solutions**:

```bash
# Solution 1: Upgrade pip
pip install --upgrade pip

# Solution 2: Install in virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install l4d

# Solution 3: Install from source
git clone https://github.com/your-org/l4d.git
cd l4d
pip install -e .
```

**If still fails**:

```bash
# Check Python version
python --version  # Must be 3.8 or higher

# Check pip version
pip --version  # Must be 20.0 or higher

# Try with specific version
pip install l4d==5.0.0
```

---

### Issue: "l4-dev command not found"

**Problem**: Command is not recognized after installation.

**Solutions**:

```bash
# Solution 1: Check installation location
which l4-dev  # On Windows: where l4-dev

# Solution 2: Reinstall
pip uninstall l4d
pip install l4d

# Solution 3: Check Python path
echo $PATH  # On Windows: echo %PATH%

# Solution 4: Install with --user (if you don't have sudo)
pip install --user l4d
# Add ~/.local/bin to PATH (Linux/Mac)
export PATH="$PATH:$HOME/.local/bin"
```

---

### Issue: "Permission denied during installation"

**Problem**: Installation fails due to permissions.

**Solutions**:

```bash
# Solution 1: Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install l4d

# Solution 2: Use --user flag
pip install --user l4d

# Solution 3: Use sudo (not recommended)
sudo pip install l4d
```

---

## 2. Configuration Issues

### Issue: "Configuration file not found"

**Problem**: L4D cannot find `.l4_config.json`.

**Solutions**:

```bash
# Solution 1: Initialize project
l4-dev init

# Solution 2: Create config manually
cat > .l4_config.json << EOF
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7
  }
}
EOF

# Solution 3: Check current directory
pwd  # Ensure you're in project root
ls -la .l4_config.json  # Verify file exists
```

---

### Issue: "Invalid configuration"

**Problem**: Configuration validation fails.

**Solutions**:

```bash
# Solution 1: Validate configuration
l4-dev config validate

# Solution 2: Check JSON syntax
python -m json.tool .l4_config.json

# Solution 3: Reset to defaults
l4-dev config reset

# Solution 4: Use configuration wizard
l4-dev config wizard
```

**Common Configuration Errors**:

```json
// ERROR: Missing required fields
{
  "llm": {
    "model": "gpt-4"
  }
}

// CORRECT
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7
  }
}
```

---

### Issue: "Profile not found"

**Problem**: Attempted to use non-existent profile.

**Solutions**:

```bash
# Solution 1: List available profiles
l4-dev profile list

# Solution 2: Use built-in profile
l4-dev profile use minimal
l4-dev profile use balanced
l4-dev profile use max

# Solution 3: Create custom profile
l4-dev profile create myprofile
```

---

## 3. Task Execution Issues

### Issue: "Git repository is not clean"

**Problem**: L4D requires a clean git workspace before starting.

**Solutions**:

```bash
# Solution 1: Check git status
git status

# Solution 2: Commit changes
git add .
git commit -m "WIP"

# Solution 3: Stash changes
git stash

# Solution 4: Create .gitignore for temporary files
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
git add .gitignore
git commit -m "Add gitignore"
```

**Why is this required?**
L4D commits automatically after each task. A clean workspace ensures L4D's commits are clear and traceable.

---

### Issue: "Task failed after multiple attempts"

**Problem**: L4D encountered an error it couldn't recover from.

**Solutions**:

```bash
# Solution 1: Check logs
l4-dev log --last

# Solution 2: View error details
l4-dev log --error

# Solution 3: Retry with more context
l4-dev start --task "Your task" --profile max

# Solution 4: Provide more context
l4-dev start --task "Your task" \
  --context "Additional context about the task"

# Solution 5: Use interactive mode
l4-dev start --interactive
```

**Common causes**:
- Task description too vague
- Missing dependencies
- Complex task requiring more tokens
- LLM API errors

---

### Issue: "Tests failed after task completion"

**Problem**: Task completed but tests are failing.

**Solutions**:

```bash
# Solution 1: Run tests manually
python -m pytest tests/ -v

# Solution 2: Check specific failing test
python -m pytest tests/test_module.py::test_function -v

# Solution 3: View test output
python -m pytest tests/ -v --tb=short

# Solution 4: Fix manually and retry
# Edit code to fix tests
python -m pytest tests/ -v  # Verify fix
git add .
git commit -m "Fix test failures"
```

---

## 4. LLM API Issues

### Issue: "LLM API key not found"

**Problem**: L4D cannot find your LLM API key.

**Solutions**:

```bash
# Solution 1: Set environment variable
export OPENAI_API_KEY="your-key-here"  # OpenAI
export ANTHROPIC_API_KEY="your-key-here"  # Anthropic
export GEMINI_API_KEY="your-key-here"  # Google Gemini

# Solution 2: Add to .env file
echo "OPENAI_API_KEY=your-key-here" >> .env
echo ".env" >> .gitignore

# Solution 3: Set in config
l4-dev config set llm.api_key "your-key-here"

# Solution 4: Use configuration wizard
l4-dev config wizard
```

**Security Tip**: Never commit API keys to git. Always use environment variables or `.env` files (add to `.gitignore`).

---

### Issue: "LLM API rate limit exceeded"

**Problem**: Too many API requests in short time.

**Solutions**:

```bash
# Solution 1: Wait and retry
# Wait a few minutes and try again

# Solution 2: Reduce concurrent requests
l4-dev config set llm.max_concurrent_requests 1

# Solution 3: Use cheaper model
l4-dev config set llm.model "gpt-3.5-turbo"

# Solution 4: Enable caching (reduces API calls)
l4-dev config set cache.enabled true
```

---

### Issue: "LLM API connection timeout"

**Problem**: Requests to LLM API are timing out.

**Solutions**:

```bash
# Solution 1: Increase timeout
l4-dev config set llm.timeout 60

# Solution 2: Check network connection
ping api.openai.com

# Solution 3: Use different provider
l4-dev config set llm.provider "anthropic"

# Solution 4: Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

---

### Issue: "LLM API quota exceeded"

**Problem**: You've exceeded your API quota or budget.

**Solutions**:

```bash
# Solution 1: Check usage
l4-dev cost --report

# Solution 2: Set cost budget
l4-dev config set cost.budget 100

# Solution 3: Use cheaper model
l4-dev config set llm.model "gpt-3.5-turbo"

# Solution 4: Enable caching
l4-dev config set cache.enabled true

# Solution 5: Add payment method (if applicable)
# Visit your LLM provider's dashboard
```

---

## 5. Git Integration Issues

### Issue: "Git hooks interfering with L4D"

**Problem**: Pre-commit hooks prevent L4D from committing.

**Solutions**:

```bash
# Solution 1: Check git hooks
ls -la .git/hooks/

# Solution 2: Temporarily disable hooks
mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled

# Solution 3: Run hooks manually after L4D
l4-dev start --task "Your task"
# After task completes:
.git/hooks/pre-commit

# Solution 4: Configure L4D to skip hooks
l4-dev config set git.skip_hooks true
```

---

### Issue: "Git merge conflicts"

**Problem**: L4D's commits conflict with your changes.

**Solutions**:

```bash
# Solution 1: Resolve conflicts manually
git status
git diff --name-only --diff-filter=U
# Edit conflicting files
git add .
git commit -m "Resolve merge conflicts"

# Solution 2: Use git's merge tool
git mergetool

# Solution 3: Rebase your changes
git rebase main

# Solution 4: Reset and start fresh
git reset --hard HEAD
l4-dev start --task "Your task"
```

---

### Issue: "Git commit fails"

**Problem**: L4D cannot commit changes.

**Solutions**:

```bash
# Solution 1: Check git status
git status

# Solution 2: Check git config
git config user.name
git config user.email

# Solution 3: Configure git if needed
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Solution 4: Check for large files
git rev-list --objects --all |
git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
awk '/^blob/ {print substr($0,6)}' |
sort -nk2 -k2n |
tail -n 10

# Solution 5: Disable auto-commit (manual commits)
l4-dev config set git.auto_commit false
```

---

## 6. Performance Issues

### Issue: "Slow task execution"

**Problem**: Tasks take longer than expected.

**Solutions**:

```bash
# Solution 1: Check what's slowing down
l4-dev progress --detailed

# Solution 2: Enable caching
l4-dev config set cache.enabled true

# Solution 3: Use faster LLM model
l4-dev config set llm.model "gpt-3.5-turbo"

# Solution 4: Reduce context loading
l4-dev config set context.start_level 0

# Solution 5: Check system resources
top  # Check CPU/Memory usage
df -h  # Check disk space
```

---

### Issue: "Running out of tokens"

**Problem**: Task complexity exceeds token budget.

**Solutions**:

```bash
# Solution 1: Increase token budget
l4-dev config set context.max_token_budget 8000

# Solution 2: Use max profile
l4-dev profile use max

# Solution 3: Enable context compression
l4-dev config set context.compression_enabled true

# Solution 4: Break task into smaller subtasks
# Instead of: "Implement complete authentication system"
# Use: "Implement user model"
# Then: "Implement login endpoint"
```

---

### Issue: "High memory usage"

**Problem**: L4D uses too much memory.

**Solutions**:

```bash
# Solution 1: Reduce cache size
l4-dev config set cache.max_size_mb 50

# Solution 2: Disable telemetry
l4-dev config set telemetry.enabled false

# Solution 3: Reduce context levels
l4-dev config set context.start_level 0

# Solution 4: Check for memory leaks
# Monitor memory usage over time
ps aux | grep l4-dev

# Solution 5: Restart L4D periodically
# If running as daemon, restart every few hours
```

---

### Issue: "Disk space running low"

**Problem**: Checkpoints, logs, or cache using too much disk space.

**Solutions**:

```bash
# Solution 1: Run cleanup
l4-dev housekeep --auto
l4-dev cleanup --auto

# Solution 2: Check disk usage
du -sh .l4_cache/
du -sh checkpoints/
du -sh logs/

# Solution 3: Reduce checkpoint retention
l4-dev config set checkpoint.max_count 5

# Solution 4: Reduce log retention
l4-dev config set log.backup_count 3

# Solution 5: Clear cache
l4-dev cache clear
```

---

## 7. Getting Help

### Check Logs First

Always check logs before seeking help:

```bash
# View recent logs
l4-dev log --last

# View error logs
l4-dev log --error

# View logs for specific operation
l4-dev log --operation "task_breakdown"

# Export logs for analysis
l4-dev log --export logs.json
```

### Useful Debug Commands

```bash
# Show configuration
l4-dev config show

# Show profiles
l4-dev profile list

# Show session info
l4-dev session list

# Show cost report
l4-dev cost --report

# Show quality report
l4-dev quality --report

# Show health status
l4-dev health check
```

### Common Debugging Workflow

```bash
# 1. Check logs
l4-dev log --last

# 2. Identify error
l4-dev log --error

# 3. Check configuration
l4-dev config validate

# 4. Check git status
git status

# 5. Run tests
python -m pytest tests/ -v

# 6. Retry with more information
l4-dev start --task "Your task" \
  --context "Additional context" \
  --profile max
```

### When to Ask for Help

Ask for help when:
- You've tried all troubleshooting steps
- Error messages are unclear
- You need help understanding an error
- You suspect a bug in L4D

### Where to Get Help

1. **Documentation**: Check [Advanced Features Guide](../intermediate/ADVANCED_FEATURES.md)
2. **Community Forum**: [https://forum.l4d.dev](https://forum.l4d.dev)
3. **GitHub Issues**: [https://github.com/your-org/l4d/issues](https://github.com/your-org/l4d/issues)
4. **Discord/Slack**: Join the community chat

### Reporting Bugs

When reporting bugs, include:

```bash
# 1. L4D version
l4-dev --version

# 2. Configuration (redact sensitive info)
l4-dev config show

# 3. Logs
l4-dev log --last

# 4. Error message
# Copy and paste the full error

# 5. Steps to reproduce
# Describe exactly what you did

# 6. Expected vs actual behavior
# What did you expect? What happened instead?
```

**Example Bug Report**:

```
**L4D Version**: 5.0.0
**Python Version**: 3.10.0
**OS**: macOS 14.0

**Error**:
```
[ERROR] Task failed: FileNotFoundError
[ERROR] File not found: /path/to/file.py
```

**Steps to Reproduce**:
1. `l4-dev start --task "Add function"`
2. Task completes successfully
3. Try to run function
4. FileNotFoundError

**Expected Behavior**: Function should be created and accessible

**Actual Behavior**: FileNotFoundError occurs

**Logs**:
[Attach log output]
```

---

## Quick Reference

### Common Commands

```bash
# Initialization
l4-dev init                           # Initialize project
l4-dev config wizard                    # Run configuration wizard

# Tasks
l4-dev start --task "Task"            # Start task
l4-dev workflow simple                  # Simple feature workflow
l4-dev workflow complex                 # Complex feature workflow
l4-dev workflow debug                   # Debug workflow

# Monitoring
l4-dev progress                         # Show progress
l4-dev cost --report                   # Show cost report
l4-dev quality --report                 # Show quality report

# Logs
l4-dev log --last                       # View recent logs
l4-dev log --error                      # View error logs

# Housekeeping
l4-dev housekeep --dry-run              # Preview cleanup
l4-dev housekeep --auto                # Run cleanup
l4-dev deps --unused                    # Show unused deps
```

### Configuration Files

```
.l4_config.json           # Main configuration
.env                      # Environment variables
.gitignore                # Git ignore rules
product.md                # Product requirements
technical.md              # Technical specifications
```

### Useful Aliases

Add these to your `.bashrc` or `.zshrc`:

```bash
# Quick task
alias l4t='l4-dev start --task'

# Quick progress
alias l4p='l4-dev progress'

# Quick logs
alias l4l='l4-dev log --last'

# Quick config
alias l4c='l4-dev config show'
```

---

## Glossary

- **Cache**: Stored results to speed up future operations
- **Context**: Information about code, files, and project state
- **LLM**: Large Language Model - AI that processes text
- **Profile**: Pre-defined configuration settings
- **Token**: Unit of text LLM processes (~4 characters)
- **Trap**: Situation where L4D gets stuck (loop, dead end)
- **TDD**: Test-Driven Development - write tests first

---

## Additional Resources

- [Quick Start Guide](QUICKSTART.md)
- [Basic Tasks Guide](BASIC_TASKS.md)
- [Common Workflows](COMMON_WORKFLOWS.md)
- [Advanced Features Guide](../intermediate/ADVANCED_FEATURES.md)
- [Best Practices Guide](../intermediate/BEST_PRACTICES.md)
- [Configuration Guide](../intermediate/CONFIGURATION.md)
- [API Reference](../reference/API.md)

---

**Still stuck?** Don't hesitate to ask for help in the community forums!