---
name: jira-ticket-enrichment
description: Improves Jira ticket quality by researching relevant code and adding context.
---

# Jira Ticket Enrichment Workflow

> Analyze code → Improve ticket description → Add technical details

## Trigger
- Jira ticket with `needs-details` label
- Slack command: `/agent enrich JIRA-123`
- GitHub `@agent analyze` on related code

## Flow

```
1. TICKET ANALYSIS
   Read: Jira ticket description, comments
   Identify: missing technical context

2. CODE RESEARCH
   Invoke: discovery skill
   Find: related files, functions, tests
   Analyze: code patterns, dependencies

3. CONTEXT GENERATION
   Generate:
   - Technical background
   - Affected components
   - Related files list
   - Suggested acceptance criteria
   - Risk assessment

4. TICKET UPDATE
   Invoke: jira-operations skill
   Add: structured comment with findings
   Update: ticket labels (remove needs-details)
```

## Output Format (Jira Comment)

```markdown
## Technical Analysis

### Affected Components
- `src/auth/login.py` - Main auth logic
- `src/utils/token.py` - Token handling

### Root Cause (if bug)
Based on code analysis: [explanation]

### Suggested Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Related Code
- Similar pattern in: [files]
- Tests to update: [test files]

### Risk Level: Low/Medium/High
[Justification]
```

## No Approval Required
This is read-only analysis - no code changes.
