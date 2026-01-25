# L4D Best Practices Guide

This guide covers best practices for using L4D effectively.

## Table of Contents

1. [Task Description Best Practices](#1-task-description-best-practices)
2. [Development Workflow Best Practices](#2-development-workflow-best-practices)
3. [Configuration Best Practices](#3-configuration-best-practices)
4. [Cost Optimization Best Practices](#4-cost-optimization-best-practices)
5. [Testing Best Practices](#5-testing-best-practices)
6. [Git Workflow Best Practices](#6-git-workflow-best-practices)
7. [Performance Best Practices](#7-performance-best-practices)

---

## 1. Task Description Best Practices

### Be Specific and Clear

**Good**:
```bash
l4-dev start --task "Add a function to validate email addresses according to RFC 5322, handling edge cases like invalid domains and whitespace"
```

**Bad**:
```bash
l4-dev start --task "Add validation"
```

### Include Context When Needed

**Good**:
```bash
l4-dev start --task "Refactor user authentication to use JWT tokens" \
  --context "Currently using session-based auth. Need to migrate for scalability. See technical.md for requirements."
```

**Bad**:
```bash
l4-dev start --task "Refactor authentication"
```

### Break Down Complex Tasks

**Good**:
```bash
# Instead of one complex task:
# l4-dev start --task "Implement complete authentication system"

# Break into smaller tasks:
l4-dev start --task "Create user model with password hashing"
l4-dev start --task "Implement JWT token generation"
l4-dev start --task "Implement JWT token verification"
```

**Bad**:
```bash
l4-dev start --task "Implement complete authentication system"
```

---

## 2. Development Workflow Best Practices

### Follow Test-Driven Development (TDD)

Always follow the Red-Green-Refactor cycle:

1. **Red**: Write a failing test
2. **Green**: Write minimal code to pass
3. **Refactor**: Improve code quality

```bash
l4-dev start --task "Your task" --tdd
```

### Review Generated Code

Always review code L4D generates:

```bash
# 1. Start task
l4-dev start --task "Your task"

# 2. Review changes
git diff

# 3. If needed, make manual adjustments
vim file.py

# 4. Commit
git add .
git commit -m "Manual adjustments"
```

### Run Tests After Each Task

```bash
l4-dev start --task "Your task"
python -m pytest tests/ -v
```

### Use Appropriate Workflows

```bash
# Simple features
l4-dev workflow simple

# Complex features
l4-dev workflow complex

# Debugging
l4-dev workflow debug

# Refactoring
l4-dev workflow refactor
```

---

## 3. Configuration Best Practices

### Use Appropriate Profiles

```bash
# Small projects, low budget
l4-dev profile use minimal

# Most projects (default)
l4-dev profile use balanced

# Large projects, high budget
l4-dev profile use max
```

### Enable Caching

Caching provides significant cost savings:

```bash
l4-dev config set cache.enabled true
l4-dev config set cache.ttl_hours 24
l4-dev config set cache.max_size_mb 100
```

**Expected Savings**: 30-40% reduction in LLM costs

### Set Realistic Token Budgets

```bash
# For simple tasks
l4-dev config set context.max_token_budget 2000

# For medium tasks
l4-dev config set context.max_token_budget 4000

# For complex tasks
l4-dev config set context.max_token_budget 8000
```

### Configure Cost Budgets

```bash
# Set monthly budget
l4-dev config set cost.budget 100

# Set alert threshold
l4-dev config set cost.alert_threshold 0.8
```

---

## 4. Cost Optimization Best Practices

### Enable All Cost Optimization Features

```bash
# LLM caching
l4-dev config set cache.enabled true

# Local decisions
l4-dev config set custom.local_decisions true

# Adaptive budgeting
l4-dev config set custom.adaptive_budgeting true
```

**Expected Total Savings**: 40-50% reduction in LLM costs

### Monitor Costs Regularly

```bash
# Weekly cost review
l4-dev cost --report

# Track trends
l4-dev cost --trend

# Predict future costs
l4-dev cost --predict
```

### Use Cheaper Models When Appropriate

```bash
# For prototyping
l4-dev config set llm.model "gpt-3.5-turbo"

# For production
l4-dev config set llm.model "gpt-4"
```

### Start with Minimal Context

```bash
l4-dev config set context.start_level 0
l4-dev config set context.progressive true
```

---

## 5. Testing Best Practices

### Write Comprehensive Tests

```bash
# L4D writes comprehensive tests automatically
l4-dev start --task "Add function with tests"
```

### Test Edge Cases

**Good task description**:
```bash
l4-dev start --task "Add email validation function - test edge cases: empty string, null input, very long email, invalid domains"
```

### Maintain Test Coverage

```bash
# After each task, check coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

### Run Tests Regularly

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_module.py -v

# Run specific test
python -m pytest tests/test_module.py::test_function -v
```

---

## 6. Git Workflow Best Practices

### Keep Workspace Clean

L4D requires a clean workspace before starting:

```bash
# Check status
git status

# Commit changes
git add .
git commit -m "WIP"

# Or stash
git stash
```

### Review Commits

```bash
# Review recent commits
git log --oneline -10

# Review specific commit
git show <commit-hash>
```

### Use Descriptive Commit Messages

L4D generates descriptive commits automatically:

```
Add calculate_average function to math.py
Fix division by zero bug in math.py
Refactor user validation to extract common logic
```

### Use Feature Branches

```bash
# Create feature branch
git checkout -b feature/authentication

# Work on feature
l4-dev start --task "Implement authentication"

# Merge back to main
git checkout main
git merge feature/authentication
```

---

## 7. Performance Best Practices

### Enable Adaptive Reasoning

```bash
l4-dev config set custom.adaptive_reasoning true
```

**Benefit**: +20% improvement in task success rate

### Enable Trap Detection

```bash
l4-dev config set custom.trap_detection true
```

**Benefit**: 95% trap detection accuracy

### Enable Meta-Cognition

```bash
l4-dev config set custom.meta_cognition true
```

**Benefit**: -70% reduction in repeated mistakes

### Enable Progressive Context

```bash
l4-dev config set context.progressive true
l4-dev config set context.start_level 0
```

**Benefit**: -40% reduction in token usage

---

## Common Anti-Patterns

### Anti-Pattern 1: Vague Task Descriptions

**Bad**:
```bash
l4-dev start --task "Fix it"
```

**Good**:
```bash
l4-dev start --task "Fix division by zero bug in math.py line 45"
```

### Anti-Pattern 2: Disabling Caching

**Bad**:
```bash
l4-dev config set cache.enabled false
```

**Good**:
```bash
l4-dev config set cache.enabled true
```

### Anti-Pattern 3: Skipping Code Review

**Bad**:
```bash
l4-dev start --task "Add feature"
# Don't review code
```

**Good**:
```bash
l4-dev start --task "Add feature"
git diff
# Review and adjust if needed
```

### Anti-Pattern 4: Ignoring Cost Monitoring

**Bad**:
```bash
# Never check costs
```

**Good**:
```bash
# Check costs weekly
l4-dev cost --report
```

### Anti-Pattern 5: Not Running Tests

**Bad**:
```bash
l4-dev start --task "Add feature"
# Don't run tests
```

**Good**:
```bash
l4-dev start --task "Add feature"
python -m pytest tests/ -v
```

---

## Best Practices Checklist

### Before Starting a Task

- [ ] Git workspace is clean
- [ ] Task description is specific and clear
- [ ] Context is provided if needed
- [ ] Appropriate profile is selected
- [ ] Cost budget is set

### During Task Execution

- [ ] Using appropriate workflow
- [ ] Monitoring progress
- [ ] Checking logs if issues occur

### After Task Completion

- [ ] Reviewed generated code
- [ ] Ran tests
- [ ] Checked git diff
- [ ] Verified functionality

### Regularly

- [ ] Reviewing cost reports
- [ ] Running housekeeping
- [ ] Checking for dead code
- [ ] Monitoring context quality

---

## Optimization Strategies

### For Small Projects

```bash
l4-dev profile use minimal
l4-dev config set context.max_token_budget 2000
l4-dev config set llm.model "gpt-3.5-turbo"
```

**Benefits**: Low cost, fast execution

### For Medium Projects

```bash
l4-dev profile use balanced
l4-dev config set context.max_token_budget 4000
l4-dev config set llm.model "gpt-4"
```

**Benefits**: Good balance of cost and quality

### For Large Projects

```bash
l4-dev profile use max
l4-dev config set context.max_token_budget 8000
l4-dev config set llm.model "gpt-4"
```

**Benefits**: High quality, handles complexity

---

## Performance Monitoring

### Track Key Metrics

```bash
# Success rate
l4-dev progress --detailed

# Cost tracking
l4-dev cost --report

# Quality metrics
l4-dev quality --report

# Performance
l4-dev progress --detailed
```

### Set Up Alerts

```bash
# Cost alerts
l4-dev config set cost.budget 100
l4-dev config set cost.alert_threshold 0.8

# Quality alerts
l4-dev config set custom.quality_threshold 0.7
```

---

## Common Issues and Solutions

### Issue: Tasks taking too long

**Solution**:
```bash
l4-dev config set context.start_level 0
l4-dev config set cache.enabled true
```

### Issue: Costs too high

**Solution**:
```bash
l4-dev config set cache.enabled true
l4-dev config set custom.local_decisions true
l4-dev config set llm.model "gpt-3.5-turbo"
```

### Issue: Low success rate

**Solution**:
```bash
l4-dev config set custom.adaptive_reasoning true
l4-dev config set custom.trap_detection true
```

---

## Additional Resources

- [Quick Start Guide](../beginner/QUICKSTART.md)
- [Basic Tasks Guide](../beginner/BASIC_TASKS.md)
- [Common Workflows](../beginner/COMMON_WORKFLOWS.md)
- [Advanced Features Guide](ADVANCED_FEATURES.md)
- [Configuration Guide](CONFIGURATION.md)
- [Optimization Guide](OPTIMIZATION.md)