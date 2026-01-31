---
name: code-refactoring
description: Systematic refactoring patterns to improve code structure without changing behavior. Use when code has duplication, long functions, high complexity, placeholder functions, or needs maintainability improvements.
---

# Code Refactoring

## Quick Reference

- **Templates**: See [templates.md](templates.md) for reporting refactoring results

## Core Principle

**NO REFACTORING WITHOUT TESTS FIRST**

Refactor safely: tests first, incremental changes, verify behavior preserved.

## When to Use

**Use when encountering:**

- Code duplication (DRY violations)
- Long functions (>50 lines)
- High complexity (cyclomatic complexity >10, nested conditionals)
- Placeholder functions (`pass`, `raise NotImplementedError`)
- Magic numbers/strings
- Deep nesting (>3 levels)
- Large classes (>300 lines, multiple responsibilities)

**Don't refactor when:**

- Code works correctly and is rarely touched
- Refactoring would break functionality without tests
- Time pressure requires shipping first (document debt, refactor later)

## Safe Refactoring Workflow

### Phase 1: Identify Target

1. **Detect Code Smells**

   - Long functions (>50 lines)
   - High complexity (>10 decision points)
   - Duplication (similar code 2+ places)
   - Placeholder functions
   - Magic numbers/strings
   - Deep nesting (>3 levels)

2. **Understand Current Behavior**

   - Read code carefully
   - Trace execution paths
   - Identify dependencies

3. **Assess Impact**
   - What code calls this?
   - What tests exist?
   - What would break?

### Phase 2: Write Tests (If Missing)

**REQUIRED:** If no tests exist:

1. Write tests capturing current behavior
2. Run tests to establish baseline
3. All tests must pass before refactoring
4. Cover: happy path, errors, edge cases, boundaries

### Phase 3: Refactor Incrementally

**One change at a time:**

1. Make smallest possible change (extract one method, rename one variable)
2. Run tests after each change (must pass)
3. Commit frequently with clear messages
4. Verify behavior unchanged

### Phase 4: Verify

1. Run all tests (must pass)
2. Check code quality (linter, type checker)
3. Document changes

## Refactoring Patterns

### Extract Method

**When:** Long function, duplicated code, complex logic

**Process:**

1. Identify code block to extract
2. Create new method with descriptive name
3. Move code, replace with method call
4. Run tests

### Extract Class

**When:** Class has multiple responsibilities, large class

**Process:**

1. Identify cohesive group of data/behavior
2. Create new class
3. Move fields and methods
4. Delegate calls
5. Run tests

### Eliminate Duplication

**When:** Same code appears in multiple places

**Process:**

1. Identify duplicated code
2. Extract common code to method/class
3. Parameterize differences
4. Replace all occurrences
5. Run tests

### Replace Placeholder

**When:** Function has `pass`, `raise NotImplementedError`

**Process:**

1. Check if function is called (YAGNI)
2. If unused: Remove
3. If used: Implement functionality
4. Write tests
5. Run tests

### Reduce Complexity

**When:** High cyclomatic complexity, deeply nested conditionals

**Process:**

1. Extract conditions to methods with descriptive names
2. Use early returns/guard clauses
3. Replace nested ifs with flat structure
4. Consider polymorphism for type-based conditionals
5. Run tests

### Extract Constant

**When:** Magic numbers/strings in code

**Process:**

1. Identify magic number/string
2. Create constant with descriptive name
3. Replace all occurrences
4. Run tests

## Code Smell Quick Reference

| Smell           | Detection                     | Refactoring                           |
| --------------- | ----------------------------- | ------------------------------------- |
| Long function   | >50 lines                     | Extract Method                        |
| High complexity | >10 decision points           | Extract Method, Simplify Conditionals |
| Duplication     | Same code 2+ places           | Extract Method, Extract Class         |
| Placeholder     | `pass`, `NotImplementedError` | Implement or Remove                   |
| Magic numbers   | Unexplained constants         | Extract Constant                      |
| Deep nesting    | >3 levels                     | Extract Method, Early Return          |
| Large class     | >300 lines                    | Extract Class                         |

## Red Flags - STOP and Reassess

- Refactoring without tests
- Multiple changes in one commit
- Tests failing after refactoring
- Changing behavior while refactoring
- Large refactoring without incremental steps

## Integration with TDD

**REQUIRED:** Use `testing` skill before refactoring:

1. If tests exist: Run them, ensure all pass
2. If tests missing: Write tests using TDD workflow
3. Refactor incrementally
4. Run tests after each change
5. All tests must pass before proceeding

**Refactoring is part of TDD REFACTOR phase** - improve code structure while keeping tests green.

## Common Mistakes

| Mistake                  | Fix                                        |
| ------------------------ | ------------------------------------------ |
| Refactor without tests   | Write tests first, establish baseline      |
| Change behavior          | Refactor = same behavior, better structure |
| Too many changes at once | One change per commit, test after each     |
| Ignoring failing tests   | Fix tests or revert refactoring            |

## The Bottom Line

**Refactoring improves code without changing behavior.**

Tests first. Incremental changes. Verify after each step. Preserve behavior always.
