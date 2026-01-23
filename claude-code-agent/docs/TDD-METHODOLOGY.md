# Test-Driven Development (TDD) Methodology Guide

## Overview

Test-Driven Development (TDD) is a software development methodology where you write tests **before** writing the implementation code. This approach ensures that your code is testable, well-designed, and meets the requirements.

## TDD Lifecycle: Red-Green-Refactor

The TDD process follows a simple three-step cycle that repeats for each feature or requirement:

```
┌─────────────────────────────────────────────────────────┐
│                   1. RED PHASE                          │
│  Write test → Run test → Expect FAILURE                │
│  (Tests don't pass because code doesn't exist yet)     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                   2. GREEN PHASE                        │
│  Write minimal code → Run test → Expect SUCCESS         │
│  (Just enough code to make tests pass)                  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                   3. REFACTOR PHASE                     │
│  Improve code → Run test → Still SUCCESS                │
│  (Clean up code while keeping tests green)              │
└─────────────────────────────────────────────────────────┘
                        ↓
              Move to next feature/test
```

### Phase 1: RED - Write Failing Tests

**Goal:** Define what you want the code to do

1. **Write a test** that describes the desired behavior
2. **Run the test** - it should **FAIL** (because the code doesn't exist yet)
3. **Verify the failure** - this confirms your test is actually testing something

**Why RED?**
- Red is the color most test runners use to indicate failures
- Seeing red tests confirms you're testing real requirements
- If tests pass immediately, they might not be testing anything meaningful

**Example:**
```python
# tests/test_flow_tracking.py
def test_generate_flow_id_from_external_id():
    """Test that flow_id is generated from external_id"""
    external_id = "JIRA-123"
    flow_id = generate_flow_id(external_id)
    assert flow_id is not None
    assert flow_id.startswith("flow-")
    assert "JIRA-123" in flow_id
```

Run: `pytest tests/test_flow_tracking.py::test_generate_flow_id_from_external_id -v`
**Expected:** ❌ FAIL (function doesn't exist yet)

### Phase 2: GREEN - Make Tests Pass

**Goal:** Write the minimum code needed to make tests pass

1. **Write minimal implementation** - just enough to satisfy the test
2. **Run the test** - it should **PASS**
3. **Don't over-engineer** - resist the urge to add extra features

**Why GREEN?**
- Green indicates passing tests
- Focus on making tests pass, not perfect code
- You can improve code quality in the refactor phase

**Example:**
```python
# core/flow_tracking.py
def generate_flow_id(external_id: str) -> str:
    """Generate flow_id from external_id"""
    return f"flow-{external_id}"
```

Run: `pytest tests/test_flow_tracking.py::test_generate_flow_id_from_external_id -v`
**Expected:** ✅ PASS

### Phase 3: REFACTOR - Improve Code Quality

**Goal:** Clean up code while keeping tests green

1. **Improve code structure** - better naming, remove duplication, optimize
2. **Run tests** - they should **still PASS**
3. **Iterate** - refactor until code is clean and maintainable

**Why REFACTOR?**
- Tests give you confidence to refactor safely
- Code quality improves without breaking functionality
- Technical debt is reduced incrementally

**Example:**
```python
# core/flow_tracking.py (refactored)
import hashlib

def generate_flow_id(external_id: str) -> str:
    """
    Generate stable flow_id from external_id.
    
    Uses hash to ensure consistent flow_id for same external_id
    while keeping IDs readable and unique.
    """
    # Create stable hash from external_id
    hash_part = hashlib.md5(external_id.encode()).hexdigest()[:8]
    return f"flow-{external_id}-{hash_part}"
```

Run: `pytest tests/test_flow_tracking.py::test_generate_flow_id_from_external_id -v`
**Expected:** ✅ PASS (still green after refactoring)

## How to Create TDD Todos Correctly

When creating todos for TDD work, each todo should include the **complete lifecycle** so it's clear what needs to be done.

### ❌ Bad Todo (Incomplete)

```
- Write tests for flow tracking
```

**Problems:**
- Doesn't mention running tests
- Doesn't mention implementation
- Doesn't mention refactoring
- Unclear what "flow tracking" means

### ✅ Good Todo (Complete TDD Lifecycle)

```
- TDD Lifecycle for flow tracking: 
  [RED] Write tests/test_flow_tracking.py → Run pytest (expect failures) → 
  [GREEN] Implement generate_flow_id() → Run pytest (expect passes) → 
  [REFACTOR] Improve code → Run pytest (still passes)
```

**Why it's good:**
- ✅ Includes all three phases (RED, GREEN, REFACTOR)
- ✅ Specifies test file name
- ✅ Specifies function to implement
- ✅ Includes pytest commands
- ✅ Clear expectations (failures → passes → still passes)

### Template for TDD Todos

Use this template when creating TDD todos:

```
TDD Lifecycle for [feature name]: 
[RED] Write [test_file_path] → Run pytest [test_file_path] (expect failures) → 
[GREEN] Implement [function_name]() → Run pytest [test_file_path] (expect passes) → 
[REFACTOR] Improve code → Run pytest [test_file_path] (still passes)
```

### Example Todos

**Example 1: Flow Tracking**
```
TDD Lifecycle for flow tracking: 
[RED] Write tests/test_flow_tracking.py → Run pytest tests/test_flow_tracking.py -v (expect failures) → 
[GREEN] Implement generate_flow_id() → Run pytest tests/test_flow_tracking.py -v (expect passes) → 
[REFACTOR] Improve code → Run pytest tests/test_flow_tracking.py -v (still passes)
```

**Example 2: Conversation Inheritance**
```
TDD Lifecycle for conversation inheritance: 
[RED] Write tests/test_conversation_inheritance.py → Run pytest tests/test_conversation_inheritance.py -v (expect failures) → 
[GREEN] Implement should_start_new_conversation() → Run pytest tests/test_conversation_inheritance.py -v (expect passes) → 
[REFACTOR] Improve code → Run pytest tests/test_conversation_inheritance.py -v (still passes)
```

**Example 3: API Endpoint**
```
TDD Lifecycle for metrics API: 
[RED] Write tests/test_metrics_api.py → Run pytest tests/test_metrics_api.py -v (expect failures) → 
[GREEN] Implement GET /conversations/{id}/metrics endpoint → Run pytest tests/test_metrics_api.py -v (expect passes) → 
[REFACTOR] Improve code → Run pytest tests/test_metrics_api.py -v (still passes)
```

## TDD Best Practices

### 1. Write Tests First

- **Always** write tests before implementation
- Tests define the contract/requirements
- Tests serve as documentation

### 2. One Test at a Time

- Focus on one failing test
- Make it pass
- Refactor
- Move to next test

### 3. Keep Tests Simple

- Test one thing per test
- Use descriptive test names
- Follow AAA pattern: Arrange → Act → Assert

### 4. Run Tests Frequently

- Run tests after every small change
- Use `pytest -v` for verbose output
- Use `pytest --watch` if available for auto-running

### 5. Don't Skip Refactoring

- Refactoring is part of TDD, not optional
- Clean code is easier to maintain
- Tests give you confidence to refactor safely

### 6. Test Behavior, Not Implementation

- Test **WHAT** the code does, not **HOW** it does it
- Focus on requirements and user-facing behavior
- Avoid testing internal implementation details

## Common TDD Mistakes

### ❌ Mistake 1: Writing All Tests at Once

**Bad:**
```python
# Writing 10 tests before implementing anything
def test_feature_1(): ...
def test_feature_2(): ...
def test_feature_3(): ...
# ... 7 more tests
```

**Good:**
```python
# Write one test, implement, refactor, then next test
def test_feature_1(): ...
# Implement feature_1
# Refactor
# Then write test_feature_2
```

### ❌ Mistake 2: Skipping the RED Phase

**Bad:** Writing tests that immediately pass (tests might not be testing anything)

**Good:** Ensure tests fail first, then make them pass

### ❌ Mistake 3: Skipping Refactoring

**Bad:** Making tests pass and moving on without cleaning up code

**Good:** Always refactor after making tests pass

### ❌ Mistake 4: Testing Implementation Details

**Bad:**
```python
def test_uses_hashlib():
    assert "hashlib" in inspect.getsource(generate_flow_id)
```

**Good:**
```python
def test_generates_stable_flow_id():
    id1 = generate_flow_id("JIRA-123")
    id2 = generate_flow_id("JIRA-123")
    assert id1 == id2  # Same input = same output
```

## TDD Workflow Checklist

When working on a feature with TDD, use this checklist:

- [ ] **RED Phase:**
  - [ ] Write test file with descriptive name
  - [ ] Write test that describes desired behavior
  - [ ] Run test → Verify it FAILS
  - [ ] Commit: "Add failing test for [feature]"

- [ ] **GREEN Phase:**
  - [ ] Write minimal implementation
  - [ ] Run test → Verify it PASSES
  - [ ] Commit: "Implement [feature] - tests passing"

- [ ] **REFACTOR Phase:**
  - [ ] Improve code quality (naming, structure, performance)
  - [ ] Run test → Verify it STILL PASSES
  - [ ] Commit: "Refactor [feature] - tests still passing"

- [ ] **Next Feature:**
  - [ ] Move to next test/feature
  - [ ] Repeat cycle

## Benefits of TDD

1. **Better Design:** Writing tests first forces you to think about the API/interface
2. **Confidence:** Tests give you confidence to refactor and change code
3. **Documentation:** Tests serve as executable documentation
4. **Fewer Bugs:** Catching bugs early is cheaper than fixing them later
5. **Faster Development:** Less time debugging, more time building features
6. **Regression Prevention:** Tests catch bugs when refactoring

## When to Use TDD

**Use TDD for:**
- ✅ New features
- ✅ Bug fixes (write test that reproduces bug first)
- ✅ Refactoring (ensure tests exist before refactoring)
- ✅ Complex logic
- ✅ Critical business logic

**TDD might be overkill for:**
- ❌ Simple one-off scripts
- ❌ Exploratory/prototype code
- ❌ Code that's hard to test (consider refactoring first)

## Summary

TDD is a powerful methodology that improves code quality and developer confidence. The key is following the **Red-Green-Refactor** cycle:

1. **RED:** Write failing test
2. **GREEN:** Make test pass with minimal code
3. **REFACTOR:** Improve code while keeping tests green

When creating todos, always include the complete lifecycle so it's clear what needs to be done at each step.

---

**Remember:** TDD is a discipline, not a religion. Use it where it adds value, and don't be dogmatic about it. The goal is better code, not perfect TDD adherence.
