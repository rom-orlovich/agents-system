---
name: code-refactoring
description: Use when code has duplication, long functions, high complexity, placeholder functions, or needs maintainability improvements - systematic refactoring patterns to improve code structure without changing behavior
---

# Code Refactoring

## Overview

Systematic refactoring patterns to improve maintainability, reduce complexity, eliminate duplication, and remove technical debt while preserving behavior.

**Core principle:** Refactor safely with tests first, make incremental changes, verify behavior preserved.

**Violating the letter of this process is violating the spirit of refactoring.**

## When to Use

**Use when encountering:**

- Code duplication (DRY violations)
- Long functions (>50 lines, complex logic)
- High cyclomatic complexity (nested conditionals, multiple branches)
- Placeholder functions (`pass`, `raise NotImplementedError`, stubs)
- Magic numbers/strings (unexplained constants)
- Deep nesting (>3 levels)
- Large classes (>300 lines, multiple responsibilities)
- Repeated patterns that could be extracted
- Technical debt that blocks new features

**Don't refactor when:**

- Code works correctly and is rarely touched
- Refactoring would break critical functionality without tests
- Time pressure requires shipping features first (document debt, refactor later)

## The Iron Law

```
NO REFACTORING WITHOUT TESTS FIRST
```

If tests don't exist, write them before refactoring. If tests exist but don't cover the code, add coverage first.

## Safe Refactoring Workflow

### Phase 1: Identify Refactoring Target

1. **Detect Code Smells**
   - Long functions (>50 lines)
   - High complexity (cyclomatic complexity >10)
   - Duplication (similar code in 2+ places)
   - Placeholder functions
   - Magic numbers/strings
   - Deep nesting (>3 levels)

2. **Understand Current Behavior**
   - Read code carefully
   - Trace execution paths
   - Identify dependencies
   - Document what code does (not how)

3. **Assess Impact**
   - What code calls this?
   - What tests exist?
   - What would break if changed?
   - Is refactoring worth the risk?

### Phase 2: Write Tests (If Missing)

**REQUIRED:** If no tests exist for code being refactored:

1. Write tests that capture current behavior
2. Run tests to establish baseline
3. All tests must pass before refactoring
4. Tests should cover:
   - Happy path
   - Error cases
   - Edge cases
   - Boundary conditions

**If tests exist but coverage is low:**

- Add missing test cases
- Ensure all paths covered
- Verify tests pass

### Phase 3: Refactor Incrementally

**One change at a time:**

1. **Make smallest possible change**
   - Extract one method
   - Rename one variable
   - Extract one constant
   - One change per commit

2. **Run tests after each change**
   - All tests must pass
   - If tests fail, revert and try different approach
   - Don't proceed until green

3. **Commit frequently**
   - Each successful refactoring step
   - Clear commit message: "refactor: extract method X"
   - Makes rollback easy if needed

4. **Verify behavior unchanged**
   - Run full test suite
   - Check integration tests
   - Manual verification if needed

### Phase 4: Verify and Document

1. **Run all tests** - Must pass
2. **Check code quality** - Linter, type checker
3. **Document changes** - What was refactored and why
4. **Measure improvement** - Complexity reduced, duplication eliminated

## Code Smell Detection

### Long Functions

**Symptom:** Function >50 lines or does multiple things

**Detection:**

```python
# Count lines in function
# Check for multiple responsibilities
# Look for "and" in function name (e.g., "process_and_validate")
```

**Refactoring:** Extract Method

### High Complexity

**Symptom:** Cyclomatic complexity >10, deeply nested conditionals

**Detection:**

```python
# Count decision points (if, elif, for, while, except)
# Measure nesting depth
# Look for switch-like if/elif chains
```

**Refactoring:** Extract Method, Replace Conditional with Polymorphism, Simplify Conditionals

### Code Duplication

**Symptom:** Similar code appears in 2+ places

**Detection:**

```python
# Search for similar code blocks
# Look for copy-paste patterns
# Identify repeated logic
```

**Refactoring:** Extract Method, Extract Class, Pull Up Method

### Placeholder Functions

**Symptom:** Functions with `pass`, `raise NotImplementedError`, or stub implementations

**Detection:**

```python
def action_comment(...):
    pass  # Placeholder

def verify_signature(...):
    raise NotImplementedError  # Stub
```

**Refactoring:** Implement functionality or remove if unused (YAGNI)

### Magic Numbers/Strings

**Symptom:** Unexplained constants in code

**Detection:**

```python
if status == 200:  # What is 200?
if retry_count < 3:  # Why 3?
```

**Refactoring:** Extract Constant, Replace Magic Number with Named Constant

### Deep Nesting

**Symptom:** >3 levels of indentation

**Detection:**

```python
if condition1:
    if condition2:
        if condition3:
            if condition4:  # Too deep
                do_something()
```

**Refactoring:** Extract Method, Early Return, Guard Clauses

### Large Classes

**Symptom:** Class >300 lines, multiple responsibilities

**Detection:**

```python
# Count lines in class
# Check for multiple "and" in class name
# Look for methods that don't use self
```

**Refactoring:** Extract Class, Extract Subclass, Replace Inheritance with Delegation

## Refactoring Catalog

### Extract Method

**When:** Long function, duplicated code, complex logic

**Process:**

1. Identify code block to extract
2. Create new method with descriptive name
3. Move code to new method
4. Replace original with method call
5. Pass necessary parameters
6. Return result if needed
7. Run tests

**Example:**

```python
# Before
def process_order(order):
    # Validate
    if not order.items:
        raise ValueError("Order must have items")
    if order.total < 0:
        raise ValueError("Total must be positive")

    # Process payment
    charge = order.total * 1.1  # Tax
    payment.process(charge)

    # Send confirmation
    email.send(order.customer, "Order confirmed")

# After
def process_order(order):
    validate_order(order)
    process_payment(order)
    send_confirmation(order)

def validate_order(order):
    if not order.items:
        raise ValueError("Order must have items")
    if order.total < 0:
        raise ValueError("Total must be positive")

def process_payment(order):
    charge = order.total * 1.1
    payment.process(charge)

def send_confirmation(order):
    email.send(order.customer, "Order confirmed")
```

### Extract Class

**When:** Class has multiple responsibilities, large class, related data/behavior together

**Process:**

1. Identify cohesive group of data/behavior
2. Create new class
3. Move fields and methods to new class
4. Create instance in original class
5. Delegate calls to new class
6. Run tests

**Example:**

```python
# Before
class TaskWorker:
    def __init__(self):
        self.ws_hub = ws_hub
        self.running = False
        self.semaphore = asyncio.Semaphore(10)
        self.active_tasks = set()
        # ... 1000+ lines

# After
class TaskWorker:
    def __init__(self):
        self.ws_hub = ws_hub
        self.concurrency = ConcurrencyManager(max_tasks=10)
        self.task_processor = TaskProcessor(self.ws_hub)

class ConcurrencyManager:
    def __init__(self, max_tasks):
        self.semaphore = asyncio.Semaphore(max_tasks)
        self.active_tasks = set()

    async def acquire(self):
        return await self.semaphore.acquire()

    def release(self):
        self.semaphore.release()
```

### Eliminate Duplication

**When:** Same code appears in multiple places

**Process:**

1. Identify duplicated code
2. Find differences (parameters, context)
3. Extract common code to method/class
4. Parameterize differences
5. Replace all occurrences
6. Run tests

**Example:**

```python
# Before
def process_github_webhook(payload):
    signature = payload.get("signature", "")
    if signature.startswith("sha256="):
        signature = signature[7:]
    # ... verify

def process_jira_webhook(payload):
    signature = payload.get("signature", "")
    if signature.startswith("sha256="):
        signature = signature[7:]
    # ... verify

# After
def normalize_signature(signature: str) -> str:
    if signature.startswith("sha256="):
        return signature[7:]
    return signature

def process_github_webhook(payload):
    signature = normalize_signature(payload.get("signature", ""))
    # ... verify

def process_jira_webhook(payload):
    signature = normalize_signature(payload.get("signature", ""))
    # ... verify
```

### Replace Placeholder

**When:** Function has `pass`, `raise NotImplementedError`, or stub

**Process:**

1. Understand what function should do
2. Check if function is actually called (YAGNI check)
3. If unused: Remove function and calls
4. If used: Implement functionality
5. Write tests for implementation
6. Run tests

**Example:**

```python
# Before
async def action_comment(provider: str, comment: str):
    pass  # Placeholder

# After
async def action_comment(provider: str, comment: str):
    if provider == "github":
        await github_client.post_comment(comment)
    elif provider == "jira":
        await jira_client.post_comment(comment)
    elif provider == "slack":
        await slack_client.post_message(comment)
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

### Reduce Complexity

**When:** High cyclomatic complexity, deeply nested conditionals

**Process:**

1. Identify complex conditional logic
2. Extract conditions to methods with descriptive names
3. Use early returns/guard clauses
4. Replace nested ifs with flat structure
5. Consider polymorphism for type-based conditionals
6. Run tests

**Example:**

```python
# Before
def process_task(task):
    if task:
        if task.status == "pending":
            if task.priority == "high":
                if task.assigned_to:
                    execute_task(task)
                else:
                    assign_task(task)
            else:
                queue_task(task)
        else:
            log_skipped(task)

# After
def process_task(task):
    if not task:
        return

    if task.status != "pending":
        log_skipped(task)
        return

    if not task.assigned_to:
        assign_task(task)
        return

    if task.priority == "high":
        execute_task(task)
    else:
        queue_task(task)
```

### Extract Constant

**When:** Magic numbers/strings in code

**Process:**

1. Identify magic number/string
2. Create constant with descriptive name
3. Replace all occurrences
4. Add comment explaining value if needed
5. Run tests

**Example:**

```python
# Before
if status_code == 200:
    process_success()
elif status_code == 401:
    handle_unauthorized()
elif status_code == 404:
    handle_not_found()

# After
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404

if status_code == HTTP_OK:
    process_success()
elif status_code == HTTP_UNAUTHORIZED:
    handle_unauthorized()
elif status_code == HTTP_NOT_FOUND:
    handle_not_found()
```

### Consolidate Error Handling

**When:** Error handling duplicated, inconsistent error messages

**Process:**

1. Identify error handling patterns
2. Create centralized error handler
3. Define error codes/messages
4. Replace scattered error handling
5. Run tests

**Example:**

```python
# Before
if not user:
    raise ValueError("User not found")
if not order:
    raise ValueError("Order not found")
if not payment:
    raise ValueError("Payment not found")

# After
class ErrorCodes:
    USER_NOT_FOUND = "USER_NOT_FOUND"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"

def raise_not_found(resource: str, identifier: str):
    code = getattr(ErrorCodes, f"{resource.upper()}_NOT_FOUND")
    raise NotFoundError(code, f"{resource} not found: {identifier}")

if not user:
    raise_not_found("user", user_id)
```

## Red Flags - STOP and Reassess

- Refactoring without tests
- Multiple changes in one commit
- Tests failing after refactoring
- Changing behavior while refactoring
- Refactoring under time pressure without tests
- Large refactoring without incremental steps
- No way to verify behavior preserved

## Common Mistakes

| Mistake                  | Fix                                        |
| ------------------------ | ------------------------------------------ |
| Refactor without tests   | Write tests first, establish baseline      |
| Change behavior          | Refactor = same behavior, better structure |
| Too many changes at once | One change per commit, test after each     |
| Ignoring failing tests   | Fix tests or revert refactoring            |
| Not understanding code   | Read and trace execution first             |
| Breaking dependencies    | Map dependencies before refactoring        |

## Integration with TDD

**REQUIRED:** Use `testing` skill before refactoring:

1. If tests exist: Run them, ensure all pass
2. If tests missing: Write tests using TDD workflow
3. Refactor incrementally
4. Run tests after each change
5. All tests must pass before proceeding

**Refactoring is part of TDD REFACTOR phase** - improve code structure while keeping tests green.

## Real-World Impact

From refactoring sessions:

- Reduced `task_worker.py` from 1043 to 400 lines (extract classes)
- Eliminated 200+ lines of duplication (extract methods)
- Reduced complexity from 25 to 8 (extract methods, early returns)
- Removed 5 placeholder functions (implemented or removed)
- Improved testability (smaller functions, clearer dependencies)

## Quick Reference

| Smell           | Detection                     | Refactoring                           |
| --------------- | ----------------------------- | ------------------------------------- |
| Long function   | >50 lines                     | Extract Method                        |
| High complexity | >10 decision points           | Extract Method, Simplify Conditionals |
| Duplication     | Same code 2+ places           | Extract Method, Extract Class         |
| Placeholder     | `pass`, `NotImplementedError` | Implement or Remove                   |
| Magic numbers   | Unexplained constants         | Extract Constant                      |
| Deep nesting    | >3 levels                     | Extract Method, Early Return          |
| Large class     | >300 lines                    | Extract Class                         |

## The Bottom Line

**Refactoring improves code without changing behavior.**

Tests first. Incremental changes. Verify after each step. Preserve behavior always.
