# Analyze Command

## Syntax
`@agent analyze <target>`

## Description
Perform analysis on code, issues, or pull requests.

## Parameters
- `target`: What to analyze (issue, PR, codebase, error, etc.)

## Behavior
1. Gather context about the target
2. Analyze using appropriate agent (planning or coding)
3. Provide structured analysis with findings
4. Suggest actionable next steps

## Examples
- `@agent analyze this issue`
- `@agent analyze PR #123`
- `@agent analyze error in logs`

## Agent Assignment
Routes to: **planning** agent with **analysis** skill
