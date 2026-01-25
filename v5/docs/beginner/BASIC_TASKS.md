# L4D Basic Tasks Guide

This guide covers common tasks you'll perform with L4D. Each task includes step-by-step instructions and examples.

## Table of Contents

1. [Adding a New Function](#1-adding-a-new-function)
2. [Fixing a Bug](#2-fixing-a-bug)
3. [Writing Tests](#3-writing-tests)
4. [Refactoring Code](#4-refactoring-code)
5. [Updating Documentation](#5-updating-documentation)
6. [Adding Error Handling](#6-adding-error-handling)

---

## 1. Adding a New Function

### Scenario

You need to add a new function to calculate the average of a list of numbers.

### Step 1: Create Task Description

```bash
l4-dev start --task "Add a function that calculates the average of a list of numbers"
```

### What L4D Does

1. **Analyzes Requirements**: Understands what function you need
2. **Writes Test First**: Creates `test_utils.py`:
   ```python
   def test_calculate_average():
       assert calculate_average([1, 2, 3]) == 2.0
       assert calculate_average([1, 2, 3, 4, 5]) == 3.0
       assert calculate_average([10, 20]) == 15.0
   ```

3. **Implements Function**: Creates `utils.py`:
   ```python
   def calculate_average(numbers):
       if not numbers:
           return 0.0
       return sum(numbers) / len(numbers)
   ```

4. **Runs Tests**: Verifies implementation works correctly
5. **Commits Changes**: Automatically commits with descriptive message

### Expected Output

```
[INFO] Task: Add a function that calculates the average of a list of numbers
[INFO] Analyzing requirements...
[INFO] Writing test: tests/test_utils.py
[INFO] Test: test_calculate_average
[INFO] Implementing: utils.py
[INFO] Function: calculate_average(numbers)
[INFO] Running tests... PASSED
[INFO] Committing: Add calculate_average function
[SUCCESS] Task completed!
```

### Verification

Run tests manually to verify:

```bash
python -m pytest tests/test_utils.py -v
```

---

## 2. Fixing a Bug

### Scenario

Your application crashes when dividing by zero.

### Step 1: Identify Bug

First, identify the bug by running tests:

```bash
python -m pytest tests/ -v
```

Output:
```
FAILED tests/test_math.py::test_divide - ZeroDivisionError: division by zero
```

### Step 2: Ask L4D to Fix

```bash
l4-dev start --task "Fix division by zero bug in math.py"
```

### What L4D Does

1. **Analyzes Bug**: Examines test failure and code
2. **Writes Failing Test**: Confirms bug exists:
   ```python
   def test_divide_by_zero():
       with pytest.raises(ZeroDivisionError):
           divide(10, 0)
   ```

3. **Fixes Bug**: Adds error handling:
   ```python
   def divide(a, b):
       if b == 0:
           raise ValueError("Cannot divide by zero")
       return a / b
   ```

4. **Runs Tests**: Verifies fix works
5. **Commits Changes**: Commits bug fix

### Expected Output

```
[INFO] Task: Fix division by zero bug in math.py
[INFO] Analyzing bug...
[INFO] Writing test: tests/test_math.py
[INFO] Test: test_divide_by_zero
[INFO] Implementing fix: math.py
[INFO] Running tests... PASSED
[INFO] Committing: Fix division by zero error
[SUCCESS] Bug fixed!
```

### Interactive Bug Fixing

Use interactive mode for more complex bugs:

```bash
l4-dev start --interactive
> What would you like to do?
> [2] Fix a bug
> Describe the bug: Application crashes when dividing by zero
> Which file has the bug? math.py
```

---

## 3. Writing Tests

### Scenario

You have existing code without tests and need comprehensive test coverage.

### Step 1: Add Tests for Existing Code

```bash
l4-dev start --task "Add tests for utils.py functions"
```

### What L4D Does

1. **Analyzes Code**: Examines all functions in `utils.py`
2. **Writes Tests**: Creates comprehensive tests:
   ```python
   # tests/test_utils.py
   
   def test_calculate_average():
       assert calculate_average([1, 2, 3]) == 2.0
       assert calculate_average([10, 20]) == 15.0
       assert calculate_average([]) == 0.0
   
   def test_calculate_sum():
       assert calculate_sum([1, 2, 3]) == 6
       assert calculate_sum([10, 20, 30]) == 60
       assert calculate_sum([]) == 0
   ```

3. **Runs Tests**: Verifies all tests pass
4. **Commits Changes**: Commits new tests

### Expected Output

```
[INFO] Task: Add tests for utils.py functions
[INFO] Analyzing utils.py...
[INFO] Found 5 functions
[INFO] Writing tests: tests/test_utils.py
[INFO] Writing test: test_calculate_average
[INFO] Writing test: test_calculate_sum
[INFO] Writing test: test_calculate_max
[INFO] Writing test: test_calculate_min
[INFO] Writing test: test_is_palindrome
[INFO] Running tests... PASSED (5/5)
[INFO] Committing: Add tests for utils.py
[SUCCESS] Tests added!
```

### Custom Test Requirements

Specify specific test requirements:

```bash
l4-dev start --task "Add edge case tests for email validation function - test empty string, null input, very long email"
```

---

## 4. Refactoring Code

### Scenario

You have duplicate code that should be extracted into a function.

### Step 1: Identify Code to Refactor

Current code (before):
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

### Step 2: Ask L4D to Refactor

```bash
l4-dev start --task "Refactor user validation code to extract common logic"
```

### What L4D Does

1. **Analyzes Code**: Identifies duplicate patterns
2. **Writes Test**: Creates test for new function:
   ```python
   def test_validate_required_field():
       user = {'name': 'John', 'email': 'john@example.com'}
       assert validate_required_field(user, 'name') == 'John'
       
       with pytest.raises(ValueError):
           validate_required_field(user, 'phone')
   ```

3. **Refactors Code**: Extracts common logic:
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

4. **Runs Tests**: Verifies refactoring doesn't break functionality
5. **Commits Changes**: Commits refactored code

### Expected Output

```
[INFO] Task: Refactor user validation code to extract common logic
[INFO] Analyzing code...
[INFO] Found duplicate validation logic
[INFO] Writing test: tests/test_user.py
[INFO] Test: test_validate_required_field
[INFO] Refactoring: user.py
[INFO] Extracted function: validate_required_field()
[INFO] Running tests... PASSED
[INFO] Committing: Refactor user validation logic
[SUCCESS] Refactoring complete!
```

### Refactoring with Workflow

Use the refactor workflow for comprehensive refactoring:

```bash
l4-dev workflow refactor
```

---

## 5. Updating Documentation

### Scenario

You've added new features and need to update documentation.

### Step 1: Update README

```bash
l4-dev start --task "Update README.md with new calculate_average function"
```

### What L4D Does

1. **Analyzes Code**: Examines new function
2. **Updates Documentation**: Adds to README.md:
   ```markdown
   ## Utils Module
   
   The `utils` module provides utility functions:
   
   - `calculate_average(numbers)`: Calculate the average of a list
     - Returns 0.0 for empty lists
     - Example: `calculate_average([1, 2, 3])` returns `2.0`
   ```

3. **Verifies Documentation**: Checks accuracy and completeness
4. **Commits Changes**: Commits documentation update

### Step 2: Add Code Documentation

```bash
l4-dev start --task "Add docstrings to all functions in utils.py"
```

Result:
```python
def calculate_average(numbers):
    """
    Calculate the average of a list of numbers.
    
    Args:
        numbers (list): List of numbers to average
        
    Returns:
        float: Average of the numbers, or 0.0 if list is empty
        
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

---

## 6. Adding Error Handling

### Scenario

Your function doesn't handle invalid input properly.

### Step 1: Add Error Handling

```bash
l4-dev start --task "Add error handling to calculate_average function - handle None, non-list input, non-numeric values"
```

### What L4D Does

1. **Analyzes Current Implementation**: Examines existing code
2. **Writes Tests**: Adds error handling tests:
   ```python
   def test_calculate_average_errors():
       with pytest.raises(TypeError):
           calculate_average(None)
       
       with pytest.raises(TypeError):
           calculate_average("not a list")
       
       with pytest.raises(TypeError):
           calculate_average([1, 2, "three"])
   ```

3. **Adds Error Handling**:
   ```python
   def calculate_average(numbers):
       if not isinstance(numbers, list):
           raise TypeError("Input must be a list")
       
       if not numbers:
           return 0.0
       
       if not all(isinstance(n, (int, float)) for n in numbers):
           raise TypeError("All elements must be numbers")
       
       return sum(numbers) / len(numbers)
   ```

4. **Runs Tests**: Verifies error handling works
5. **Commits Changes**: Commits error handling

### Expected Output

```
[INFO] Task: Add error handling to calculate_average function
[INFO] Analyzing current implementation...
[INFO] Writing tests: tests/test_utils.py
[INFO] Test: test_calculate_average_errors
[INFO] Adding error handling: utils.py
[INFO] Running tests... PASSED
[INFO] Committing: Add error handling to calculate_average
[SUCCESS] Error handling added!
```

---

## Tips for Successful Tasks

### 1. Be Specific in Task Descriptions

Good task descriptions:
- ✅ "Add a function to validate email addresses according to RFC 5322"
- ✅ "Fix bug where divide function crashes on zero"
- ✅ "Add tests for calculate_average function including edge cases"

Bad task descriptions:
- ❌ "Add validation function"
- ❌ "Fix the bug"
- ❌ "Add some tests"

### 2. Provide Context When Needed

For complex tasks, provide additional context:

```bash
l4-dev start --task "Refactor user authentication system to use JWT tokens" \
  --context "Currently using session-based auth. Need to migrate to JWT for scalability. See technical.md for requirements."
```

### 3. Use Interactive Mode for Learning

Interactive mode helps you understand what L4D is doing:

```bash
l4-dev start --interactive
```

### 4. Review Generated Code

Always review code L4D generates before committing:

```bash
# Preview changes without committing
l4-dev start --task "Your task" --dry-run

# Review changes
git diff

# If satisfied, run task again
l4-dev start --task "Your task"
```

### 5. Test After Each Task

Run tests to verify changes:

```bash
python -m pytest tests/ -v
```

---

## Common Task Patterns

### Adding New Features

```bash
l4-dev start --task "Add feature description"
```

**Pattern**: Write test → Implement → Test → Commit

### Fixing Bugs

```bash
l4-dev start --task "Fix bug description in file.py"
```

**Pattern**: Analyze → Write failing test → Fix → Test → Commit

### Adding Tests

```bash
l4-dev start --task "Add tests for module.py"
```

**Pattern**: Analyze → Write tests → Test → Commit

### Refactoring

```bash
l4-dev start --task "Refactor code description"
```

**Pattern**: Analyze → Write test → Refactor → Test → Commit

### Adding Error Handling

```bash
l4-dev start --task "Add error handling to function"
```

**Pattern**: Analyze → Write error tests → Add handling → Test → Commit

---

## Next Steps

- [ ] Try adding a simple function
- [ ] Practice fixing a bug
- [ ] Write tests for existing code
- [ ] Refactor some duplicate code
- [ ] Add documentation to your functions

Once comfortable with basic tasks, explore:
- [Advanced Features Guide](../intermediate/ADVANCED_FEATURES.md)
- [Best Practices Guide](../intermediate/BEST_PRACTICES.md)
- [Common Workflows](COMMON_WORKFLOWS.md)