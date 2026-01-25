# L4D Quick Start Guide

Welcome to L4D (Level 4 Development), your AI-powered autonomous development companion. This guide will help you get up and running in under 30 minutes.

---

## Table of Contents

1. [Installation](#1-installation)
2. [Initialize Project](#2-initialize-project)
3. [Configuration](#3-configuration)
4. [Your First Task](#4-your-first-task)
5. [Monitor Progress](#5-monitor-progress)
6. [View Results](#6-view-results)
7. [Common Workflows](#7-common-workflows)
8. [Troubleshooting](#8-troubleshooting)
9. [Next Steps](#9-next-steps)

---

## 1. Installation

### Prerequisites

Before installing L4D, ensure you have:

- **Python 3.8 or higher**: [Download Python](https://www.python.org/downloads/)
- **Git**: [Install Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- **pip**: Comes with Python installation

### Install L4D

```bash
# Install L4D via pip
pip install l4d

# Verify installation
l4-dev --version
```

**Expected Output:**
```
L4D v5.0.0
```

### Quick Installation (Using pipx)

For a cleaner installation in an isolated environment:

```bash
# Install pipx if not already installed
pip install pipx

# Install L4D via pipx
pipx install l4d
```

---

## 2. Initialize Project

### Create a New Project

```bash
# Navigate to your project directory
cd my_project

# Initialize L4D for your project
l4-dev init
```

**Expected Output:**
```
[INFO] Initializing L4D for project: my_project
[INFO] Detected project structure...
[INFO] Creating L4D configuration...
[SUCCESS] L4D initialized successfully!
[INFO] Next steps:
  1. Create product.md (product requirements)
  2. Create technical.md (technical specifications)
  3. Run: l4-dev start
```

### Project Structure

Your project should look like this after initialization:

```
my_project/
├── product.md              # Product requirements (YOU create this)
├── technical.md            # Technical specifications (YOU create this)
├── .l4_config.json        # L4D configuration (auto-generated)
├── .l4_cache/             # L4D cache directory (auto-created)
├── src/                    # Your source code
│   ├── __init__.py
│   ├── main.py
│   └── utils.py
└── tests/                  # Your tests
    ├── __init__.py
    └── test_main.py
```

---

## 3. Configuration

### Option 1: Use Configuration Wizard (Recommended for Beginners)

```bash
# Run the configuration wizard
l4-dev config wizard
```

**Expected Interactive Prompt:**
```
Welcome to L4D Configuration Wizard!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detected Project Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Project Size: Medium (234 files, 15,432 lines of code)
• Available RAM: 16 GB
• Available Disk Space: 50 GB
• Python Version: 3.11

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Enable the following features (recommended settings):

[✓] Enable LLM caching (saves 30-40% of API costs)
[✓] Enable progressive context (saves 30-40% of tokens)
[✓] Enable cost tracking (monitor API usage)
[✓] Enable housekeeping (automatic code cleanup)
[ ] Enable advanced features (requires more resources)

Press Enter to accept defaults, or type 'c' to customize:
```

**Press Enter** to accept defaults, or type `c` to customize.

### Option 2: Use Pre-configured Profile

L4D comes with three built-in profiles:

**Minimal Profile** (for small projects, low budget):
```bash
l4-dev profile use minimal
```

**Balanced Profile** (default, recommended for most projects):
```bash
l4-dev profile use balanced
```

**Max Profile** (for large projects, high budget):
```bash
l4-dev profile use max
```

### Option 3: Manual Configuration

Edit `.l4_config.json` directly:

```json
{
  "version": "5.0.0",
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7,
    "api_key": "your_api_key_here"
  },
  "cache": {
    "enabled": true,
    "max_size_mb": 100
  },
  "context": {
    "start_level": 0,
    "max_token_budget": 4000
  }
}
```

**Important:** Set your LLM API key:
```bash
# For OpenAI
export L4_LLM_API_KEY="sk-your-openai-api-key"

# For Anthropic (Claude)
export L4_LLM_API_KEY="sk-ant-your-anthropic-api-key"
```

---

## 4. Your First Task

### Step 1: Create Product Requirements

Create `product.md` with your product requirements:

```markdown
# Product Requirements

## User Authentication System

### Description
Implement a secure user authentication system with login, logout, and password reset functionality.

### User Stories
1. As a user, I want to log in with email and password
2. As a user, I want to log out securely
3. As a user, I want to reset my password if I forget it

### Requirements
- Secure password hashing (bcrypt)
- JWT token-based authentication
- Password reset with email verification
- Session management
```

### Step 2: Create Technical Specifications

Create `technical.md` with technical details:

```markdown
# Technical Specifications

## Technology Stack
- Language: Python 3.11
- Framework: FastAPI
- Database: PostgreSQL
- ORM: SQLAlchemy
- Authentication: JWT + bcrypt

## Architecture
```
src/
├── auth/
│   ├── __init__.py
│   ├── models.py      # User model
│   ├── schemas.py     # Pydantic schemas
│   └── routes.py      # Auth endpoints
├── database.py        # Database connection
└── main.py          # FastAPI app
```

## Dependencies
- fastapi
- uvicorn
- sqlalchemy
- psycopg2-binary
- pyjwt
- bcrypt
- python-multipart
```

### Step 3: Start Development

```bash
# Start L4D with a task
l4-dev start --task "Implement user authentication system"
```

**Expected Output:**
```
[INFO] Starting L4D v5.0.0...
[INFO] Loading configuration from .l4_config.json
[INFO] Task: Implement user authentication system
[INFO] Analyzing requirements from product.md
[INFO] Analyzing technical specifications from technical.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task Breakdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Created 5 subtasks:

  1. Set up database connection and models
  2. Implement user registration endpoint
  3. Implement login endpoint with JWT
  4. Implement password reset functionality
  5. Write comprehensive tests

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Starting Task 1/5: Set up database connection and models
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[INFO] Writing test: tests/test_database.py
[INFO] Implementing: src/database.py
[INFO] Running tests... 
  ✓ test_database_connection
  ✓ test_user_model_creation
  ✓ test_password_hashing
[SUCCESS] All tests passed!
[INFO] Committing: Set up database connection and models

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Starting Task 2/5: Implement user registration endpoint
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[INFO] Writing test: tests/test_auth_routes.py
[INFO] Implementing: src/auth/routes.py
[INFO] Running tests...
  ✓ test_register_user_success
  ✓ test_register_user_duplicate_email
  ✓ test_register_user_invalid_data
[SUCCESS] All tests passed!
[INFO] Committing: Implement user registration endpoint

... (continues for remaining tasks)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SUCCESS] All tasks completed successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary:
• Total Tasks: 5
• Completed: 5
• Failed: 0
• Time Elapsed: 12 minutes 34 seconds
• Total Tokens Used: 8,420
• Estimated Cost: $0.42

Git Commits:
  ✓ 5 commits created
```

### Using Interactive Mode

If you prefer step-by-step guidance:

```bash
l4-dev start --interactive
```

**Expected Interactive Prompt:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L4D Interactive Mode
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What would you like to do?

  [1] Implement a new feature
  [2] Fix a bug
  [3] Refactor code
  [4] Run tests
  [5] View documentation

Enter your choice [1-5]: 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Describe the feature you want to implement
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Type your feature description below:
> Add user authentication with login, logout, and password reset

[INFO] Analyzing feature description...
[INFO] Creating task breakdown...
[INFO] Ready to start implementation!

Press Enter to begin, or 'q' to quit:
```

---

## 5. Monitor Progress

### Real-time Progress

L4D provides real-time progress indicators during development:

```
[████████████░░░░░░░░░] 60% - Task 3/5: Implement login endpoint
  • Writing test: test_login_endpoint.py
  • Implementing: src/auth/routes.py
  • Running tests...
  • Estimated time remaining: 3 minutes
```

### Check Progress Status

```bash
# Check current progress
l4-dev progress
```

**Expected Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L4D Progress Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Session: session_20250125_123456
Started: 2025-01-25 12:34:56

Task Progress:
  ┌─────────────────────────────────────┬───────┬──────────┐
  │ Task                              │ Status │ Time     │
  ├─────────────────────────────────────┼───────┼──────────┤
  │ 1. Set up database connection     │ ✓ Done │ 2m 30s  │
  │ 2. Implement user registration    │ ✓ Done │ 4m 15s  │
  │ 3. Implement login endpoint      │ In     │ 3m 00s  │
  │ 4. Implement password reset      │ Queue  │ -        │
  │ 5. Write comprehensive tests      │ Queue  │ -        │
  └─────────────────────────────────────┴───────┴──────────┘

Overall Progress: 60% (3/5 tasks completed)

Resource Usage:
  • Tokens Used: 5,240 / 10,000 (52%)
  • Estimated Cost: $0.26 / $0.50 (52%)
  • Time Elapsed: 9m 45s
  • Estimated Time Remaining: 6m 15s
```

### View Detailed Logs

```bash
# View recent logs
l4-dev logs

# View logs for a specific operation
l4-dev logs --operation "Implement login endpoint"

# View error logs only
l4-dev logs --level ERROR
```

---

## 6. View Results

### Generate Report

```bash
# Generate comprehensive report
l4-dev report
```

**Expected Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L4D Development Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Session: session_20250125_123456
Date: 2025-01-25 12:34:56 - 12:47:30

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Tasks: 5
Completed: 5 (100%)
Failed: 0 (0%)
Success Rate: 100%

Tasks Completed:
  1. Set up database connection and models ✓
  2. Implement user registration endpoint ✓
  3. Implement login endpoint with JWT ✓
  4. Implement password reset functionality ✓
  5. Write comprehensive tests ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Code Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lines Added: 842
Lines Modified: 127
Files Created: 7
Files Modified: 3
Tests Written: 25
Test Coverage: 94%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cost Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Tokens Used: 8,420
Total Cost: $0.42
Average Cost per Task: $0.08

Cost Breakdown:
  • Planning: 1,200 tokens ($0.06)
  • Implementation: 5,800 tokens ($0.29)
  • Verification: 1,420 tokens ($0.07)

Cache Hit Rate: 35% (saved $0.15)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Quality Metrics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context Quality: 0.82 (Excellent)
Average Task Success Rate: 100%
First Attempt Success: 80%

Context Levels Used:
  • L0 (Immediate): 45%
  • L1 (Recent): 35%
  • L2 (Session): 20%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Git Activity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Commits: 5
Branch: main
Latest Commit: a1b2c3d Implement password reset functionality

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recommendations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Excellent session! All tasks completed successfully.
✓ High cache hit rate (35%) - good cost efficiency.
✓ Consider running housekeeping to clean up unused code.
✓ Next steps: Implement API documentation and user profile feature.
```

### View Cost Report

```bash
# View cost details
l4-dev cost --report
```

**Expected Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L4D Cost Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Period: 2025-01-01 to 2025-01-25

Total Cost: $12.67
Daily Average: $0.50
Weekly Average: $3.51

Cost Breakdown by Task Type:
  • Planning: $2.50 (19.7%)
  • Implementation: $8.00 (63.1%)
  • Verification: $2.17 (17.2%)

Cost Breakdown by Model:
  • GPT-4: $10.00 (78.9%)
  • GPT-3.5-turbo: $2.67 (21.1%)

Cache Savings:
  • Cache Hit Rate: 38%
  • Money Saved: $7.50
  • Effective Cost: $5.17 (after savings)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cost Trend
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Last 7 Days:
  • Day 1: $0.48
  • Day 2: $0.52
  • Day 3: $0.45
  • Day 4: $0.50
  • Day 5: $0.55
  • Day 6: $0.42
  • Day 7: $0.50

Trend: Stable (+2.3% vs last week)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Predicted Monthly Cost: $15.00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. Common Workflows

### Workflow 1: Simple Feature Implementation

```bash
# Implement a simple feature quickly
l4-dev workflow simple
```

**Example:**
```bash
$ l4-dev workflow simple
Enter feature description: Add password strength validator

[INFO] Analyzing feature...
[INFO] Creating minimal task breakdown...
[INFO] Starting implementation...
[SUCCESS] Feature implemented in 5m 20s!
```

**Use when:**
- Adding simple features (1-2 files)
- Bug fixes
- Small refactorings
- Adding utility functions

### Workflow 2: Complex Feature Implementation

```bash
# Implement a complex feature with detailed planning
l4-dev workflow complex
```

**Example:**
```bash
$ l4-dev workflow complex
Enter feature description: Implement payment processing system with Stripe integration

[INFO] Analyzing feature complexity...
[INFO] Complexity: HIGH
[INFO] Creating detailed task breakdown (15 subtasks)...
[INFO] Planning architecture...
[INFO] Implementing incrementally...
[SUCCESS] Feature implemented in 45m 12s!
```

**Use when:**
- Adding complex features (5+ files)
- New integrations
- Major refactoring
- Database migrations

### Workflow 3: Debug Failing Tests

```bash
# Debug failing tests automatically
l4-dev workflow debug
```

**Example:**
```bash
$ l4-dev workflow debug
Enter test file or pattern: tests/test_auth.py

[INFO] Running tests to identify failures...
  ✗ test_login_with_invalid_password
  ✗ test_password_reset_expired_token

[INFO] Analyzing failures...
[INFO] Identifying root causes...
[INFO] Fixing issues...
[SUCCESS] All tests passing!
```

**Use when:**
- Tests are failing
- Unexpected behavior
- Integration issues
- Regression bugs

### Workflow 4: Refactor Code

```bash
# Refactor code automatically
l4-dev workflow refactor
```

**Example:**
```bash
$ l4-dev workflow refactor
Enter refactor description: Improve database query performance in user module

[INFO] Analyzing code structure...
[INFO] Identifying optimization opportunities...
[INFO] Refactoring with preserved behavior...
[INFO] Running tests to verify...
[SUCCESS] Refactoring complete! Performance improved by 40%.
```

**Use when:**
- Improving code quality
- Performance optimization
- Reducing technical debt
- Applying design patterns

---

## 8. Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Git repository is not clean"

**Error:**
```
Error: Git repository is not clean
- Uncommitted changes in: src/main.py
- Suggestion: Run 'git commit' or 'git stash' before continuing
```

**Solution:**
```bash
# Commit your changes
git add .
git commit -m "Your commit message"

# Or stash temporarily
git stash

# Then run L4D again
l4-dev start
```

#### Issue 2: "LLM API key not found"

**Error:**
```
Error: LLM API key not found
- Set L4_LLM_API_KEY environment variable
- Or configure in .l4_config.json
```

**Solution:**
```bash
# Set API key temporarily
export L4_LLM_API_KEY="sk-your-api-key"

# Or add to your shell profile (~/.bashrc or ~/.zshrc)
echo 'export L4_LLM_API_KEY="sk-your-api-key"' >> ~/.bashrc
source ~/.bashrc

# Or configure in .l4_config.json
l4-dev config set llm.api_key "sk-your-api-key"
```

#### Issue 3: "Module not found" errors

**Error:**
```
Error: Module 'fastapi' not found
- Install missing dependencies: pip install fastapi
```

**Solution:**
```bash
# Install missing dependencies
pip install fastapi uvicorn sqlalchemy

# Or install from requirements.txt
pip install -r requirements.txt

# Or let L4D install automatically
l4-dev install-deps
```

#### Issue 4: Cache errors

**Error:**
```
Error: Cache corruption detected
- Clear cache with: l4-dev cache clear
```

**Solution:**
```bash
# Clear L4D cache
l4-dev cache clear

# Rebuild cache
l4-dev cache rebuild

# Verify cache
l4-dev cache status
```

#### Issue 5: Out of disk space

**Error:**
```
Warning: Low disk space (< 1GB available)
- Clean up old data with: l4-dev cleanup
```

**Solution:**
```bash
# Clean up old checkpoints, logs, and cache
l4-dev cleanup --dry-run  # Preview first
l4-dev cleanup --auto      # Execute cleanup

# Or manually clean cache
l4-dev cache clear

# Remove old checkpoints
l4-dev checkpoint cleanup
```

### Getting Help

If you encounter issues not covered here:

```bash
# Get detailed error information
l4-dev --verbose

# View logs for debugging
l4-dev logs --level DEBUG

# Check system health
l4-dev health-check

# Report an issue
l4-dev report-issue
```

### Community Support

- **Documentation**: https://github.com/nekroo-alt/growmind/tree/main/v4/docs
- **Issues**: https://github.com/nekroo-alt/growmind/issues
- **Discussions**: https://github.com/nekroo-alt/growmind/discussions

---

## 9. Next Steps

Congratulations! You've completed your first L4D development session. Here's what to explore next:

### 1. Explore Advanced Features

```bash
# Learn about housekeeping (automatic code cleanup)
l4-dev housekeep --help

# Learn about cost optimization
l4-dev cost --help

# Learn about quality tracking
l4-dev quality --help
```

### 2. Customize Your Workflow

```bash
# Explore different profiles
l4-dev profile list
l4-dev profile show balanced
l4-dev profile diff balanced max

# Customize configuration
l4-dev config --help

# Create custom profile
l4-dev profile create custom --inherits balanced
```

### 3. Integrate with Your Existing Workflow

```bash
# Use with CI/CD
l4-dev start --task "Run CI tests"

# Generate documentation
l4-dev docs generate

# Export data for analysis
l4-dev export --format json --output report.json
```

### 4. Learn More

Read the comprehensive documentation:

- **Beginner**: [BASIC_TASKS.md](BASIC_TASKS.md)
- **Intermediate**: [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md)
- **Expert**: [ARCHITECTURE.md](ARCHITECTURE.md)

### 5. Join the Community

- Star the repository: https://github.com/nekroo-alt/growmind
- Join discussions: https://github.com/nekroo-alt/growmind/discussions
- Report issues: https://github.com/nekroo-alt/growmind/issues

---

## Quick Reference

### Essential Commands

```bash
# Initialize project
l4-dev init

# Configure L4D
l4-dev config wizard

# Start development
l4-dev start
l4-dev start --interactive
l4-dev start --task "Your task description"

# Monitor progress
l4-dev progress
l4-dev logs

# View reports
l4-dev report
l4-dev cost --report
l4-dev quality --report

# Workflows
l4-dev workflow simple
l4-dev workflow complex
l4-dev workflow debug
l4-dev workflow refactor

# Housekeeping
l4-dev housekeep --dry-run
l4-dev housekeep --auto
l4-dev cleanup --auto
l4-dev deps --unused

# Profiles
l4-dev profile list
l4-dev profile show <profile>
l4-dev profile use <profile>
```

### Configuration Files

- `.l4_config.json` - Main configuration
- `product.md` - Product requirements
- `technical.md` - Technical specifications
- `.l4_cache/` - Cache directory

### Environment Variables

```bash
L4_LLM_API_KEY          # LLM API key
L4_LLM_PROVIDER        # LLM provider (openai, anthropic)
L4_LLM_MODEL           # LLM model (gpt-4, gpt-3.5-turbo, claude)
L4_CACHE_DIR           # Cache directory
L4_LOG_LEVEL           # Log level (DEBUG, INFO, WARNING, ERROR)
```

---

## Tips and Best Practices

### 1. Write Clear Task Descriptions

❌ Bad: "Fix auth"
✅ Good: "Fix login endpoint to return proper error messages when password is incorrect"

### 2. Use Interactive Mode for Complex Tasks

Interactive mode helps L4D understand your requirements better.

### 3. Monitor Costs Regularly

```bash
l4-dev cost --trend
```

This helps you stay within budget and identify cost drivers.

### 4. Enable Caching

Caching saves 30-40% of LLM API costs:

```bash
# In .l4_config.json
{
  "cache": {
    "enabled": true,
    "max_size_mb": 100
  }
}
```

### 5. Run Housekeeping Periodically

```bash
l4-dev housekeep --auto
```

This keeps your codebase clean and removes dead code.

### 6. Use Progressive Context

Progressive context saves 30-40% of tokens:

```bash
# In .l4_config.json
{
  "context": {
    "start_level": 0,
    "progressive": true
  }
}
```

### 7. Write Tests First

L4D follows TDD (Test-Driven Development). Let L4D write tests first, then implement code.

### 8. Review Generated Code

Always review and test the code generated by L4D. It's your responsibility to ensure quality.

---

## Version Information

- **L4D Version**: 5.0.0
- **Last Updated**: 2025-01-25
- **Documentation Version**: 1.0.0

---

**Happy coding with L4D! 🚀**

For more information, visit https://github.com/nekroo-alt/growmind