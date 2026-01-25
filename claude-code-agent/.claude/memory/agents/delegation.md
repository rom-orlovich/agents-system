# Agent Delegation Learnings

> What works in agent orchestration. **Max 30 entries.**

---

## Delegation Patterns

### [A01] Always Provide Context
Include original request, relevant files, task_id | Added: 2025-01-25

### [A02] Include Iteration Count
Pass iteration number to verifier for urgency escalation | Added: 2025-01-25

### [A03] Re-instruct Only Failures
Don't restart from scratch - target specific gaps | Added: 2025-01-25

### [A04] Parallel When Possible
Independent sub-tasks should run in background | Added: 2025-01-25

---

## Failures to Avoid

### [A05] Over-Delegation
Simple questions don't need agent chain | Added: 2025-01-25

### [A06] Context Loss
Always preserve previous work in re-delegation | Added: 2025-01-25

### [A07] Vague Gap Feedback
Provide file:line:fix, not "needs improvement" | Added: 2025-01-25
