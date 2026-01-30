# No Comments Rule

## Enforcement Level
HIGH - Should be followed in all business logic

## Rule
Code must be self-explanatory without comments.

## Rationale
Comments become outdated and misleading. Self-explanatory code is always up-to-date.

## Requirements
1. Use descriptive variable and function names
2. Keep functions small and focused
3. Use explicit types
4. Organize code logically
5. Extract complex logic into named functions

## Examples

### ❌ WRONG
```python
# Calculate total cost
t = sum(c)
```

### ✅ CORRECT
```python
total_cost_usd = sum(task_costs)
```

## Exceptions
- API documentation (docstrings for public APIs)
- Complex algorithms requiring mathematical explanation
- Regulatory compliance requirements

## Enforcement
Code review should question any comments and suggest refactoring for clarity instead.
