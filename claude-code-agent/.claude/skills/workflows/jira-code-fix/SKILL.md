---
name: jira-code-fix
description: Workflow for fixing code from Jira tickets. Includes discovery, planning, approval, and TDD execution.
---

# Jira Code Fix Workflow

> Jira ticket (AI-Fix label) → Code fix → PR

## Trigger
- Jira ticket with `AI-Fix` label assigned
- GitHub `@agent fix` command referencing Jira

## Flow

```
1. DISCOVERY
   Invoke: discovery skill
   Output: relevant_files, dependencies, complexity

2. PLANNING
   Invoke: planning agent
   Output: PLAN.md, Draft PR, Slack notification

3. APPROVAL GATE
   Wait for: @agent approve / Slack button
   Timeout: 24h → escalate

4. EXECUTION
   Invoke: executor agent (after approval)
   Output: TDD implementation, PR updated

5. VERIFICATION
   Invoke: verifier agent (max 3 iterations)
   Output: score ≥90% → complete

6. LEARNING
   Invoke: self-improvement agent
   Output: memory updated
```

## Slack Notification Template

```
📋 Plan Ready: {title}
🎫 Ticket: {ticket_id}

📖 Background: {background}
✅ Done: {what_done}
💡 Insights: {insights}
📁 Files: {files}

[View PR] [Approve] [Reject]
```

## Completion Criteria
- All tests pass
- PR ready for review (not draft)
- Jira ticket commented with PR link
