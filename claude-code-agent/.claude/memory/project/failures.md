# Failure Learnings

> Read before re-delegation. **Max 30 entries. Auto-prune >30 days unused.**

---

## Entry Format
```
### [ID] Failure Title
What: Problem | Why: Root cause | Lesson: What to do instead | Added: YYYY-MM-DD
```

---

## Delegation Failures

### [F01] Over-Delegation
What: Simple questions routed through full agent flow | Why: No complexity classification | Lesson: Always classify tier first | Added: 2025-01-25

### [F02] Context Loss in Re-delegation
What: Re-delegated agent didn't have previous work | Why: Brain didn't preserve context | Lesson: Always include "Previous work" in re-delegation | Added: 2025-01-25

### [F03] Restart from Scratch
What: Entire implementation restarted after rejection | Why: Didn't target specific gaps | Lesson: Only re-work failing criteria | Added: 2025-01-25

---

## Verification Failures

### [F04] Approval to Avoid Conflict
What: Verifier approved despite gaps | Why: Subjective assessment | Lesson: Run scripts, score based on exit codes | Added: 2025-01-25

### [F05] Vague Gap Feedback
What: "Needs improvement" feedback loop | Why: Non-specific instructions | Lesson: Provide file paths, line numbers, exact fixes | Added: 2025-01-25

### [F06] Infinite Loop
What: Verification kept rejecting without progress | Why: Same gap recurring, no escalation | Lesson: If gap persists 2x, escalate immediately | Added: 2025-01-25

---

## Memory Failures

### [F07] Memory Inflation
What: Memory files grew too large | Why: No size limits | Lesson: Enforce max 30 entries, prune aggressively | Added: 2025-01-25

### [F08] Storing Bad Patterns
What: Invalid patterns in memory | Why: Written before verification | Lesson: Only write after ≥90% confidence | Added: 2025-01-25

---

## Workflow Failures

### [F09] Missing Response to Source
What: Jira/GitHub left without update | Why: Workflow didn't mandate response | Lesson: ALWAYS post back to source system | Added: 2025-01-25

### [F10] Silent Failures
What: Workflow failed without notification | Why: No error handling for notifications | Lesson: Always notify Slack on failure | Added: 2025-01-25

---

## Pruning Rules

Same as patterns.md.
