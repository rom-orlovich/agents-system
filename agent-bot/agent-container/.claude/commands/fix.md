# Fix Command

## Syntax
`@agent fix <issue>`

## Description
Fix a bug or error in the codebase.

## Parameters
- `issue`: Description of the bug or error to fix

## Behavior
1. Reproduce and understand the issue
2. Write a failing test that captures the bug
3. Fix the bug
4. Ensure all tests pass
5. Verify the fix resolves the issue

## Examples
- `@agent fix authentication error`
- `@agent fix type errors in models.py`
- `@agent fix failing tests`

## Agent Assignment
Routes to: **coding** agent with **testing** and **coding** skills

## Requirements
- Must write test that reproduces bug first
- Must fix bug without breaking existing functionality
- Must follow all code quality rules
