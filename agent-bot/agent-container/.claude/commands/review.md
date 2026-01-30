# Review Command

## Trigger Patterns
- @agent review
- @agent review this PR
- @agent please review
- Label: agent-review

## Parameters
- --focus security: Security-focused review
- --focus performance: Performance-focused review
- --strict: Apply stricter standards

## Behavior
1. Fetch PR diff
2. Activate code-review-agent
3. Post review comment to PR

## Output
Review comment with:
- Summary with status emoji
- Specific issues with line refs
- Improvement suggestions
