---
name: refactoring-advisor
description: Suggest and implement safe refactorings to improve code quality
user-invocable: false
---

Identifies refactoring opportunities, suggests improvements, and safely implements refactorings while maintaining functionality and test coverage.

## Capabilities

1. **Refactoring Detection** - Code smells, duplication, complexity hotspots, coupling issues, dead code
2. **Refactoring Recommendations** - Extract method/class, inline method, rename, move, introduce parameter object, replace conditional with polymorphism
3. **Safe Refactoring** - Verify tests pass, apply incrementally, run tests after each step, rollback on failure
4. **Impact Analysis** - Estimate effort, assess risk, calculate benefit, identify dependencies

## Common Refactorings

- **Extract Method** - When function > 20 lines, repeated code, complex logic
- **Extract Class** - When class > 300 lines, multiple responsibilities, high coupling
- **Rename** - Improve clarity and maintainability
- **Move** - Better organization and cohesion
- **Inline** - Remove unnecessary abstraction
- **Replace Conditional** - Use polymorphism for complex conditionals

## Safety Process

1. **Before Refactoring** - All tests pass, create backup branch, check test coverage
2. **During Refactoring** - Apply incrementally, run tests after each change, preserve public APIs
3. **After Refactoring** - Run full test suite, verify no regressions, update documentation

## Output Format

Report includes:
- Refactoring opportunities identified
- Recommended refactorings with priority
- Risk assessment and effort estimate
- Step-by-step refactoring plan
- Expected benefits

## Best Practices

- Always have tests before refactoring
- Refactor incrementally
- Run tests frequently
- Preserve public APIs
- Document changes
- Measure improvement (complexity, maintainability)

See examples.md for refactoring examples and patterns.
