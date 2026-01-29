# Test-Driven Development Rule

## Enforcement Level
HIGH - Required for all business logic

## Rule
Write tests before writing implementation code.

## Process
1. **RED**: Write a failing test
2. **GREEN**: Write minimal code to pass the test
3. **REFACTOR**: Improve code while keeping tests green

## Requirements
1. Every feature must have tests written first
2. Tests must be independent and repeatable
3. Tests must be clear and descriptive
4. Aim for high code coverage (>80%)
5. Tests should run fast

## Benefits
- Ensures code is testable
- Prevents regressions
- Documents expected behavior
- Increases confidence in changes

## Enforcement
Pull requests without tests for new features should be rejected.
