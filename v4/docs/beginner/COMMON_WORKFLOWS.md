# L4D Common Workflows Guide

This guide covers common development workflows you'll use with L4D. Each workflow includes step-by-step instructions and examples.

## Table of Contents

1. [Simple Feature Implementation](#1-simple-feature-implementation)
2. [Complex Feature with Planning](#2-complex-feature-with-planning)
3. [Debug Failing Tests](#3-debug-failing-tests)
4. [Code Refactoring](#4-code-refactoring)
5. [Test-Driven Development](#5-test-driven-development)
6. [Documentation Updates](#6-documentation-updates)
7. [Housekeeping and Cleanup](#7-housekeeping-and-cleanup)

---

## 1. Simple Feature Implementation

### When to Use

Use this workflow for:
- Adding a single function or class
- Small feature additions (< 30 lines of code)
- Simple bug fixes
- Adding basic error handling

### Workflow Steps

#### Step 1: Describe the Feature

```bash
l4-dev workflow simple
```

You'll be prompted:

```
> Describe the feature: Add a function to calculate the factorial of a number
```

#### Step 2: L4D Breaks Down Task

L4D will:
1. Analyze the feature requirements
2. Create test cases
3. Implement the function
4. Run tests
5. Commit changes

### Example: Adding Factorial Function

**Input:**
```
Add a function to calculate the factorial of a number
```

**What L4D Does:**

1. **Writes Test** (`tests/test_math.py`):
   ```python
   def test_factorial():
       assert factorial(0) == 1
       assert factorial(1) == 1
       assert factorial(5) == 120
       assert factorial(10) == 3628800
   ```

2. **Implements Function** (`math.py`):
   ```python
   def factorial(n):
       if n < 0:
           raise ValueError("Factorial is not defined for negative numbers")
       if n == 0:
           return 1
       result = 1
       for i in range(1, n + 1):
           result *= i
       return result
   ```

3. **Runs Tests**: Verifies all tests pass
4. **Commits**: "Add factorial function to math.py"

### Expected Output

```
[INFO] Starting simple feature workflow...
[INFO] Feature: Add a function to calculate the factorial of a number
[INFO] Analyzing requirements...
[INFO] Writing test: tests/test_math.py
[INFO] Test: test_factorial
[INFO] Implementing: math.py
[INFO] Function: factorial(n)
[INFO] Running tests... PASSED
[INFO] Committing: Add factorial function
[SUCCESS] Feature implemented!
```

### Tips

- **Be Specific**: Describe exactly what you need
- **Include Edge Cases**: Mention edge cases if important (e.g., "handle negative numbers")
- **Keep it Simple**: This workflow works best for features under 30 lines

---

## 2. Complex Feature with Planning

### When to Use

Use this workflow for:
- Large features (> 30 lines of code)
- Multi-file changes
- Features requiring architectural changes
- Complex business logic

### Workflow Steps

#### Step 1: Describe the Feature

```bash
l4-dev workflow complex
```

You'll be prompted:

```
> Describe the feature: Implement user authentication with JWT tokens
```

#### Step 2: L4D Plans and Breaks Down

L4D will:
1. Analyze requirements thoroughly
2. Create detailed task breakdown
3. Implement each subtask sequentially
4. Test and commit each subtask
5. Complete the full feature

### Example: JWT Authentication

**Input:**
```
Implement user authentication with JWT tokens
```

**What L4D Does:**

**Task Breakdown:**
1. Create user model with password hashing
2. Implement JWT token generation
3. Implement JWT token verification
4. Add login endpoint
5. Add protected route decorator
6. Write comprehensive tests

**Implementation:**

**Subtask 1: User Model**
```python
# models/user.py
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    def __init__(self, username, password):
        self.username = username
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
```

**Subtask 2: JWT Generation**
```python
# auth/jwt.py
import jwt
from datetime import datetime, timedelta

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

**Subtask 3-6**: Continue with verification, login, routes, tests

### Expected Output

```
[INFO] Starting complex feature workflow...
[INFO] Feature: Implement user authentication with JWT tokens
[INFO] Analyzing requirements...
[INFO] Creating task breakdown...
[INFO] Created 6 subtasks:
  1. Create user model with password hashing
  2. Implement JWT token generation
  3. Implement JWT token verification
  4. Add login endpoint
  5. Add protected route decorator
  6. Write comprehensive tests

[INFO] Starting subtask 1/6: Create user model with password hashing
[INFO] Writing test: tests/test_user_model.py
[INFO] Implementing: models/user.py
[INFO] Running tests... PASSED
[INFO] Committing: Create user model with password hashing

[INFO] Starting subtask 2/6: Implement JWT token generation
[INFO] Writing test: tests/test_jwt.py
[INFO] Implementing: auth/jwt.py
[INFO] Running tests... PASSED
[INFO] Committing: Implement JWT token generation

... (continues for all subtasks)

[SUCCESS] Complex feature implemented!
```

### Tips

- **Provide Context**: Add context for complex features
- **Review Breakdown**: L4D shows you the breakdown before implementing
- **Monitor Progress**: Use `l4-dev progress` to track progress

---

## 3. Debug Failing Tests

### When to Use

Use this workflow when:
- Tests are failing
- You don't know why tests are failing
- You need to identify and fix bugs

### Workflow Steps

#### Step 1: Identify Failing Tests

```bash
python -m pytest tests/ -v
```

Output:
```
FAILED tests/test_math.py::test_calculate_average - AssertionError: expected 2.0, got 0.0
```

#### Step 2: Start Debug Workflow

```bash
l4-dev workflow debug
```

You'll be prompted:

```
> Which test is failing? test_calculate_average
> Which file has the bug? math.py
```

#### Step 3: L4D Debugs and Fixes

L4D will:
1. Analyze the failing test
2. Examine the code
3. Identify the bug
4. Fix the bug
5. Verify the fix
6. Commit the fix

### Example: Debugging Average Calculation

**Failing Test:**
```python
def test_calculate_average():
    result = calculate_average([1, 2, 3])
    assert result == 2.0  # FAILS: got 0.0
```

**Buggy Code:**
```python
def calculate_average(numbers):
    if not numbers:
        return 0.0
    # BUG: Should sum(numbers) / len(numbers)
    return 0.0
```

**What L4D Does:**

1. **Analyzes Test Failure**: Understands what's expected vs actual
2. **Examines Code**: Finds the bug in `calculate_average()`
3. **Writes Test**: Adds test to confirm fix:
   ```python
   def test_calculate_average():
       assert calculate_average([1, 2, 3]) == 2.0
       assert calculate_average([10, 20]) == 15.0
   ```
4. **Fixes Bug**:
   ```python
   def calculate_average(numbers):
       if not numbers:
           return 0.0
       return sum(numbers) / len(numbers)  # FIXED
   ```
5. **Runs Tests**: Verifies fix works
6. **Commits**: "Fix calculate_average bug"

### Expected Output

```
[INFO] Starting debug workflow...
[INFO] Failing test: test_calculate_average
[INFO] Analyzing test failure...
[INFO] Expected: 2.0, Actual: 0.0
[INFO] Examining code: math.py
[INFO] Found bug: calculate_average() returns 0.0 instead of calculating average
[INFO] Writing test: tests/test_math.py
[INFO] Test: test_calculate_average
[INFO] Fixing bug: math.py
[INFO] Function: calculate_average(numbers)
[INFO] Running tests... PASSED
[INFO] Committing: Fix calculate_average bug
[SUCCESS] Bug fixed!
```

### Tips

- **Provide Context**: If the bug is complex, provide additional context
- **Run Tests First**: Always run tests to identify failures before starting debug workflow
- **Review Fix**: Review the fix L4D provides

---

## 4. Code Refactoring

### When to Use

Use this workflow when:
- Code has duplicate logic
- Code is hard to read
- Code violates DRY (Don't Repeat Yourself) principle
- You want to improve code quality

### Workflow Steps

#### Step 1: Identify Code to Refactor

Find code that needs refactoring. Example:

```python
def process_user(user):
    name = user.get('name', '').strip()
    if not name:
        raise ValueError('Name required')
    
    email = user.get('email', '').strip()
    if not email:
        raise ValueError('Email required')
    
    phone = user.get('phone', '').strip()
    if not phone:
        raise ValueError('Phone required')
```

#### Step 2: Start Refactor Workflow

```bash
l4-dev workflow refactor
```

You'll be prompted:

```
> Describe refactoring: Extract duplicate validation logic from process_user function
> Which file to refactor? user.py
```

#### Step 3: L4D Refactors Code

L4D will:
1. Analyze the code
2. Identify duplicate patterns
3. Extract common logic
4. Update code to use extracted function
5. Write tests
6. Verify refactoring doesn't break functionality
7. Commit changes

### Example: Extracting Validation Logic

**Before:**
```python
def process_user(user):
    name = user.get('name', '').strip()
    if not name:
        raise ValueError('Name required')
    
    email = user.get('email', '').strip()
    if not email:
        raise ValueError('Email required')
    
    phone = user.get('phone', '').strip()
    if not phone:
        raise ValueError('Phone required')
```

**What L4D Does:**

1. **Analyzes Code**: Identifies duplicate validation pattern
2. **Extracts Function**:
   ```python
   def validate_required_field(user, field_name):
       value = user.get(field_name, '').strip()
       if not value:
           raise ValueError(f'{field_name.capitalize()} required')
       return value
   ```
3. **Refactors Code**:
   ```python
   def process_user(user):
       name = validate_required_field(user, 'name')
       email = validate_required_field(user, 'email')
       phone = validate_required_field(user, 'phone')
   ```
4. **Writes Test**:
   ```python
   def test_validate_required_field():
       user = {'name': 'John', 'email': 'john@example.com'}
       assert validate_required_field(user, 'name') == 'John'
       
       with pytest.raises(ValueError):
           validate_required_field(user, 'phone')
   ```
5. **Runs Tests**: Verifies refactoring works
6. **Commits**: "Refactor user validation to extract common logic"

**After:**
```python
def validate_required_field(user, field_name):
    value = user.get(field_name, '').strip()
    if not value:
        raise ValueError(f'{field_name.capitalize()} required')
    return value

def process_user(user):
    name = validate_required_field(user, 'name')
    email = validate_required_field(user, 'email')
    phone = validate_required_field(user, 'phone')
```

### Expected Output

```
[INFO] Starting refactor workflow...
[INFO] Refactoring: Extract duplicate validation logic from process_user function
[INFO] Analyzing code: user.py
[INFO] Found duplicate validation pattern (3 occurrences)
[INFO] Extracting function: validate_required_field(user, field_name)
[INFO] Writing test: tests/test_user.py
[INFO] Test: test_validate_required_field
[INFO] Refactoring: user.py
[INFO] Updated process_user() to use extracted function
[INFO] Running tests... PASSED
[INFO] Committing: Refactor user validation to extract common logic
[SUCCESS] Refactoring complete!
```

### Tips

- **Describe Clearly**: Be specific about what you want to refactor
- **Review Changes**: Always review refactored code
- **Run Tests**: Verify refactoring doesn't break anything

---

## 5. Test-Driven Development (TDD)

### When to Use

Use this workflow when:
- You want to follow TDD methodology
- You're implementing new features
- You want to ensure code quality

### TDD Cycle

L4D follows the Red-Green-Refactor cycle:

1. **Red**: Write a failing test
2. **Green**: Write minimal code to pass the test
3. **Refactor**: Improve code quality while maintaining tests

### Workflow Steps

#### Step 1: Start TDD Workflow

```bash
l4-dev start --task "Implement feature using TDD" --tdd
```

#### Step 2: L4D Follows TDD Cycle

L4D will:
1. Write a failing test (Red)
2. Write minimal code to pass (Green)
3. Refactor code if needed (Refactor)
4. Repeat for each feature

### Example: TDD for String Reversal

**Step 1: Red - Write Failing Test**
```python
def test_reverse_string():
    assert reverse_string("hello") == "olleh"  # FAILS: function doesn't exist
```

**Step 2: Green - Implement Function**
```python
def reverse_string(s):
    return s[::-1]
```

**Step 3: Refactor - Improve Code**
```python
# Already simple, no refactoring needed
def reverse_string(s):
    return s[::-1]
```

**What L4D Does:**

1. **Writes Failing Test**: `test_reverse_string()`
2. **Implements Function**: `reverse_string(s)`
3. **Runs Tests**: Verifies implementation
4. **Checks for Refactoring**: Determines if refactoring needed
5. **Commits**: "Implement reverse_string using TDD"

### Expected Output

```
[INFO] Starting TDD workflow...
[INFO] Feature: Implement feature using TDD
[INFO] Step 1/3: Red - Write failing test
[INFO] Writing test: tests/test_string.py
[INFO] Test: test_reverse_string
[INFO] Running tests... FAILED (as expected)

[INFO] Step 2/3: Green - Implement to pass test
[INFO] Implementing: string.py
[INFO] Function: reverse_string(s)
[INFO] Running tests... PASSED

[INFO] Step 3/3: Refactor - Improve code quality
[INFO] Checking for refactoring opportunities...
[INFO] Code is already clean, no refactoring needed

[INFO] Committing: Implement reverse_string using TDD
[SUCCESS] TDD cycle complete!
```

### Tips

- **Start with Tests**: Always write tests first
- **Keep it Simple**: Write minimal code to pass tests
- **Refactor Regularly**: Improve code quality continuously

---

## 6. Documentation Updates

### When to Use

Use this workflow when:
- You've added new features
- You've changed API interfaces
- You need to update README or docs
- You want to add code documentation

### Workflow Steps

#### Step 1: Identify Documentation to Update

Determine what needs updating:
- README.md
- API documentation
- Code docstrings
- User guides

#### Step 2: Start Documentation Workflow

```bash
l4-dev start --task "Update documentation for new feature"
```

#### Step 3: L4D Updates Documentation

L4D will:
1. Analyze code changes
2. Update relevant documentation
3. Add docstrings if needed
4. Verify documentation accuracy
5. Commit changes

### Example: Updating README

**New Function:**
```python
def calculate_average(numbers):
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
```

**What L4D Does:**

1. **Analyzes Code**: Examines `calculate_average()` function
2. **Updates README.md**:
   ```markdown
   ## Utils Module
   
   The `utils` module provides utility functions:
   
   - `calculate_average(numbers)`: Calculate average of a list
     - Returns 0.0 for empty lists
     - Example: `calculate_average([1, 2, 3])` returns `2.0`
   ```
3. **Adds Docstring**:
   ```python
   def calculate_average(numbers):
       """
       Calculate the average of a list of numbers.
       
       Args:
           numbers (list): List of numbers to average
           
       Returns:
           float: Average of numbers, or 0.0 if list is empty
           
       Examples:
           >>> calculate_average([1, 2, 3])
           2.0
           >>> calculate_average([])
           0.0
       """
       if not numbers:
           return 0.0
       return sum(numbers) / len(numbers)
   ```
4. **Verifies Documentation**: Checks accuracy
5. **Commits**: "Update documentation for calculate_average function"

### Expected Output

```
[INFO] Starting documentation workflow...
[INFO] Feature: Update documentation for new feature
[INFO] Analyzing code changes...
[INFO] Found new function: calculate_average()
[INFO] Updating documentation: README.md
[INFO] Adding docstring: utils.py
[INFO] Verifying documentation accuracy...
[INFO] Committing: Update documentation for calculate_average function
[SUCCESS] Documentation updated!
```

### Tips

- **Be Specific**: Tell L4D which documentation to update
- **Review Changes**: Review documentation updates
- **Keep Documentation Current**: Update docs regularly

---

## 7. Housekeeping and Cleanup

### When to Use

Use this workflow regularly to:
- Remove dead code
- Clean up unused dependencies
- Remove old checkpoints and logs
- Maintain codebase health

### Workflow Steps

#### Step 1: Preview Cleanup

```bash
l4-dev housekeep --dry-run
```

This shows what will be cleaned up without making changes.

#### Step 2: Run Cleanup

```bash
l4-dev housekeep --auto
```

This automatically cleans up identified issues.

#### Step 3: Clean Up Dependencies

```bash
l4-dev deps --cleanup
```

This removes unused dependencies.

### Example: Housekeeping

**What L4D Does:**

1. **Dead Code Detection**:
   - Identifies unused functions
   - Identifies unused classes
   - Identifies unused variables
   - Identifies unused files

2. **Dependency Cleanup**:
   - Identifies unused dependencies
   - Shows safe-to-remove packages

3. **Data Cleanup**:
   - Removes old checkpoints
   - Rotates log files
   - Archives old telemetry

**Expected Output:**

```
[INFO] Starting housekeeping workflow...
[INFO] Analyzing codebase...
[INFO] Dead code detection:
  - Found 3 unused functions
  - Found 1 unused class
  - Found 5 unused variables
  - Found 2 unused files

[INFO] Dependency analysis:
  - Found 2 unused dependencies
    - requests (not imported)
    - beautifulsoup4 (not imported)

[INFO] Data cleanup:
  - Found 5 old checkpoints (> 24 hours)
  - Found 3 oversized log files (> 10MB)

Preview:
  - Remove 3 unused functions
  - Remove 1 unused class
  - Remove 5 unused variables
  - Remove 2 unused files
  - Remove 2 unused dependencies
  - Remove 5 old checkpoints
  - Rotate 3 log files

Estimated savings: 450 KB code, 150 MB data

Run 'l4-dev housekeep --auto' to apply cleanup
```

**Apply Cleanup:**

```bash
l4-dev housekeep --auto
```

```
[INFO] Applying cleanup...
[INFO] Creating backup...
[INFO] Removing dead code...
[INFO] Removing unused dependencies...
[INFO] Cleaning up data...
[INFO] Running tests... PASSED
[INFO] Cleanup successful!
[INFO] Committing: Housekeeping - remove dead code and cleanup data
[SUCCESS] Housekeeping complete!
```

### Tips

- **Preview First**: Always use `--dry-run` to preview changes
- **Backup**: L4D creates backup before cleanup
- **Run Tests**: Tests run after cleanup to verify nothing broke
- **Schedule Regularly**: Run housekeeping weekly

---

## Workflow Comparison

| Workflow | Use Case | Complexity | Time |
|-----------|-----------|------------|-------|
| **Simple Feature** | Small additions | Low | 1-2 min |
| **Complex Feature** | Large features | High | 10-30 min |
| **Debug** | Fixing bugs | Medium | 2-5 min |
| **Refactor** | Code improvements | Medium | 5-10 min |
| **TDD** | Test-driven development | Medium | 2-5 min |
| **Documentation** | Updating docs | Low | 1-3 min |
| **Housekeeping** | Maintenance | Low | 2-5 min |

---

## Best Practices

### 1. Choose the Right Workflow

- **Simple Feature**: For small, straightforward changes
- **Complex Feature**: For large, multi-file features
- **Debug**: When tests are failing
- **Refactor**: To improve code quality
- **TDD**: When you want test-driven development
- **Documentation**: To keep docs current
- **Housekeeping**: Regularly maintain codebase

### 2. Be Specific in Descriptions

Good descriptions:
- ✅ "Add a function to validate email addresses according to RFC 5322"
- ✅ "Fix bug where divide function crashes on zero input"
- ✅ "Extract duplicate validation logic from user processing"

Bad descriptions:
- ❌ "Add validation"
- ❌ "Fix bug"
- ❌ "Refactor code"

### 3. Monitor Progress

```bash
l4-dev progress
```

### 4. Review Changes

Always review changes before committing:

```bash
git diff
```

### 5. Run Tests

```bash
python -m pytest tests/ -v
```

---

## Next Steps

- [ ] Try the simple feature workflow
- [ ] Practice the debug workflow
- [ ] Use TDD for a new feature
- [ ] Refactor some duplicate code
- [ ] Update documentation
- [ ] Run housekeeping

Once comfortable with workflows, explore:
- [Advanced Features Guide](../intermediate/ADVANCED_FEATURES.md)
- [Best Practices Guide](../intermediate/BEST_PRACTICES.md)
- [Configuration Guide](../intermediate/CONFIGURATION.md)