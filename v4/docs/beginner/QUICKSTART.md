# L4D Quick Start Guide

Welcome to L4D (L4 Self-Evolving Development Platform)! This guide will help you get started with L4D in 30 minutes or less.

## Table of Contents

1. [Installation](#1-installation)
2. [Initialize Your Project](#2-initialize-your-project)
3. [Configure L4D](#3-configure-l4d)
4. [Your First Task](#4-your-first-task)
5. [Monitor Progress](#5-monitor-progress)
6. [View Results](#6-view-results)
7. [Next Steps](#7-next-steps)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Installation

### Prerequisites

Before installing L4D, ensure you have:

- Python 3.8 or higher
- Git installed and configured
- An LLM API key (OpenAI, Anthropic, or Google Gemini)

### Install L4D

```bash
pip install l4d
```

Or install from source:

```bash
git clone https://github.com/your-org/l4d.git
cd l4d
pip install -e .
```

### Verify Installation

```bash
l4-dev --version
```

You should see: `L4D v5.0.0`

---

## 2. Initialize Your Project

Navigate to your project directory:

```bash
cd /path/to/your/project
```

### Run the Initialization Wizard

```bash
l4-dev init
```

The wizard will guide you through:

1. **Project Detection**: L4D will automatically detect your project size
2. **Configuration**: Choose a profile (minimal, balanced, or max)
3. **LLM Setup**: Provide your LLM API key and select a model
4. **Documentation**: Create `product.md` and `technical.md` (if needed)

### Example Wizard Output

```
$ l4-dev init

Welcome to L4D Setup!

[✓] Detected project: Medium (234 files, 15,432 lines)
[✓] Available resources: 16GB RAM, 50GB disk space

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

[✓] Configuration saved to .l4_config.json
[✓] Ready to start development!
```

---

## 3. Configure L4D

### Smart Defaults

L4D automatically configures optimal settings based on your project:

- **Cache enabled** (recommended for most projects)
- **Adaptive reasoning enabled** (improves decision quality)
- **Trap detection enabled** (prevents infinite loops)
- **Progressive context** (starts with minimal, expands as needed)

### Configuration Profiles

Choose a profile based on your needs:

```bash
# Minimal profile - for small projects, low budget
l4-dev profile use minimal

# Balanced profile - default, works for most projects
l4-dev profile use balanced

# Max profile - for complex projects, high budget
l4-dev profile use max
```

### Manual Configuration (Optional)

If you need to customize settings:

```bash
l4-dev config wizard
```

Or edit `.l4_config.json` directly:

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7
  },
  "cache": {
    "enabled": true,
    "max_size_mb": 100
  },
  "custom": {
    "adaptive_reasoning": true,
    "progress_tracking": true,
    "trap_detection": true
  }
}
```

---

## 4. Your First Task

### Interactive Mode (Recommended for Beginners)

```bash
l4-dev start --interactive
```

You'll see:

```
> What would you like to do?
> [1] Implement a new feature
> [2] Fix a bug
> [3] Refactor code
> [4] Run tests
> Selection: 1
> Describe the feature: Add user login feature

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

### Direct Task Command

```bash
l4-dev start --task "Add user authentication"
```

L4D will:

1. Break down the task into subtasks
2. Follow TDD (Test-Driven Development) process
3. Write tests first, then implement code
4. Run tests to verify
5. Commit changes automatically

### Example Project Structure

Before using L4D, ensure your project has:

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

---

## 5. Monitor Progress

### Real-time Progress

L4D shows real-time progress as it works:

```
[INFO] Task: Add user authentication
[████████░░░░░░░░░░░░] 40% (2/5 subtasks)
[INFO] Current: Implementing user login function
[INFO] Estimated time remaining: 3 minutes
```

### Progress Dashboard

View a detailed progress dashboard:

```bash
l4-dev progress
```

Output:

```
Session Progress
================
Tasks Completed: 3
Tasks Remaining: 2
Total Time: 12m 34s
Estimated Remaining: 8m 21s

Current Task: Implement password hashing
Status: In Progress
Progress: [███████░░░░░░░░] 65%
```

### Detailed Progress Report

```bash
l4-dev progress --detailed
```

---

## 6. View Results

### Session Report

After tasks complete, view a session report:

```bash
l4-dev session report
```

Output:

```
Session Report (2025-01-25 11:30:15)
=====================================
Tasks Completed: 5
Total Time: 21m 45s
LLM Calls: 47
Tokens Used: 12,345
Cost: $0.89

Success Rate: 100%
Tests Passed: 15/15
Commits: 5
```

### Cost Report

View cost tracking:

```bash
l4-dev cost --report
```

Output:

```
Cost Report (2025-01-01 to 2025-01-25)
========================================
Total Cost: $15.67
Cost per Task: $2.34 (avg)
Tasks Completed: 7
Cache Hit Rate: 35% (saved $5.48)
Predicted Monthly Cost: $18.50

Cost by Task:
- Add user authentication: $3.45
- Fix login bug: $1.23
- Refactor database: $5.67
...
```

### Quality Report

View context quality metrics:

```bash
l4-dev quality --report
```

Output:

```
Context Quality Report
=====================
Average Quality: 0.78 (out of 1.0)
Completeness: 0.85
Relevance: 0.76
Freshness: 0.72
Conciseness: 0.68
Diversity: 0.82

Tasks with quality > 0.75: 92% success rate
Tasks with quality < 0.50: 45% success rate
```

---

## 7. Next Steps

### Common Workflows

**Simple Feature Implementation**
```bash
l4-dev workflow simple
```

**Complex Feature with Planning**
```bash
l4-dev workflow complex
```

**Debug Failing Tests**
```bash
l4-dev workflow debug
```

**Refactor Code**
```bash
l4-dev workflow refactor
```

### Housekeeping

Keep your codebase clean:

```bash
# Preview dead code cleanup
l4-dev housekeep --dry-run

# Automatic safe deletion
l4-dev housekeep --auto

# Show unused dependencies
l4-dev deps --unused

# Remove unused dependencies
l4-dev deps --cleanup
```

### Advanced Features

Once you're comfortable with basic tasks, explore:

- **Adaptive Reasoning**: L4D learns from its decisions
- **Trap Detection**: Automatically detects and recovers from loops
- **Progressive Context**: Starts with minimal context, expands as needed
- **Cost Optimization**: LLM caching, local decisions, adaptive budgets

See the [Advanced Features Guide](../intermediate/ADVANCED_FEATURES.md) for details.

---

## 8. Troubleshooting

### Common Issues

#### Issue: "Git repository is not clean"

**Problem**: L4D requires a clean git workspace before starting.

**Solution**:
```bash
# Commit or stash your changes
git commit -m "WIP"  # or
git stash

# Then run L4D again
l4-dev start --task "Your task"
```

#### Issue: "LLM API key not found"

**Problem**: L4D cannot find your API key.

**Solution**:
```bash
# Set API key as environment variable
export OPENAI_API_KEY="your-key-here"

# Or configure via wizard
l4-dev config wizard

# Then run L4D again
l4-dev start --task "Your task"
```

#### Issue: "Task failed after multiple attempts"

**Problem**: L4D encountered an error it couldn't recover from.

**Solution**:
1. Check the logs: `l4-dev log --last`
2. Review the error message
3. Fix any issues manually
4. Try again with more context: `l4-dev start --task "Your task" --profile max`

#### Issue: "Running out of tokens"

**Problem**: Task complexity exceeds token budget.

**Solution**:
```bash
# Increase token budget
l4-dev config set max_token_budget 8000

# Or use max profile
l4-dev profile use max

# Then run L4D again
l4-dev start --task "Your task"
```

### Getting Help

If you encounter issues not covered here:

1. **Check the logs**: `l4-dev log --last`
2. **View detailed error**: `l4-dev log --error`
3. **Review documentation**: [Advanced Features](../intermediate/ADVANCED_FEATURES.md)
4. **Report issues**: [GitHub Issues](https://github.com/your-org/l4d/issues)

### Useful Debug Commands

```bash
# View recent logs
l4-dev log --last

# View error logs
l4-dev log --error

# View logs for a specific operation
l4-dev log --operation "task_breakdown"

# Export logs for analysis
l4-dev log --export logs.json
```

---

## Tips and Best Practices

### 1. Start with Small Tasks

Begin with small, well-defined tasks:
- ✅ "Add a function to add two numbers"
- ❌ "Implement complete authentication system"

### 2. Write Clear Task Descriptions

Provide detailed task descriptions:
```
Good: "Add a function that validates email addresses according to RFC 5322"
Bad: "Fix email validation"
```

### 3. Use Interactive Mode for Learning

Interactive mode provides guidance and explanations:
```bash
l4-dev start --interactive
```

### 4. Monitor Costs Regularly

Track costs to stay within budget:
```bash
l4-dev cost --report
l4-dev cost --trend
```

### 5. Run Housekeeping Periodically

Keep your codebase clean:
```bash
# Weekly housekeeping
l4-dev housekeep --auto
l4-dev cleanup --auto
```

### 6. Use Appropriate Profiles

Match profile to project needs:
- **Small projects**: `minimal` profile
- **Medium projects**: `balanced` profile (default)
- **Large projects**: `max` profile

### 7. Leverage Caching

LLM caching saves 30-40% on costs:
```bash
# Ensure caching is enabled (default)
l4-dev config show cache.enabled
```

### 8. Check Progress Regularly

Monitor progress to catch issues early:
```bash
l4-dev progress
```

---

## Glossary

- **TDD**: Test-Driven Development - write tests first, then implement code
- **LLM**: Large Language Model - AI that understands and generates text
- **Progressive Context**: Starting with minimal context, expanding as needed
- **Trap**: A situation where L4D gets stuck (loop, dead end, circular reasoning)
- **Token**: Unit of text LLM processes (approximately 4 characters)
- **Subtask**: A smaller task that L4D breaks a larger task into

---

## Additional Resources

- [Advanced Features Guide](../intermediate/ADVANCED_FEATURES.md)
- [Best Practices Guide](../intermediate/BEST_PRACTICES.md)
- [API Reference](../reference/API.md)
- [Configuration Guide](../intermediate/CONFIGURATION.md)
- [Community Forum](https://forum.l4d.dev)
- [GitHub Repository](https://github.com/your-org/l4d)

---

**Congratulations!** 🎉 You've completed the Quick Start Guide. You're now ready to use L4D to accelerate your development workflow!

For more advanced usage, see the [Intermediate Documentation](../intermediate/).