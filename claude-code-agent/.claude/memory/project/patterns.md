# Successful Patterns

> Read at complex task start. **Max 30 entries. Auto-prune >30 days unused.**

---

## Entry Format
```
### [ID] Pattern Name
Context: When to use | Evidence: Why it works | Added: YYYY-MM-DD
```

---

## Code Patterns

### [C01] Async All I/O
Context: DB, HTTP, file operations | Evidence: Non-blocking, better throughput | Added: 2025-01-25

### [C02] TDD Workflow
Context: Any code implementation | Evidence: Catches bugs early, cleaner design | Added: 2025-01-25

### [C03] Pydantic Validation
Context: API inputs, config, domain models | Evidence: Type safety, auto-validation | Added: 2025-01-25

### [C04] Error Wrap External Calls
Context: Service integrations | Evidence: Graceful degradation | Added: 2025-01-25

---

## Agent Patterns

### [A01] Always Provide Context
Context: Delegation to sub-agents | Evidence: Prevents misunderstanding | Added: 2025-01-25

### [A02] Include Iteration Count
Context: Verification loop | Evidence: Enables escalation logic | Added: 2025-01-25

### [A03] Re-instruct Only Failures
Context: After verification rejection | Evidence: Preserves working parts | Added: 2025-01-25

---

## Workflow Patterns

### [W01] Post Status to Source
Context: Cross-service workflows | Evidence: Maintains traceability | Added: 2025-01-25

### [W02] Slack Notify Async Ops
Context: Long-running tasks | Evidence: Keeps stakeholders informed | Added: 2025-01-25

---

## Pruning Rules

| Trigger | Action |
|---------|--------|
| Entry >30 days unused | Archive to memory/archive/ |
| Entry unused >10 tasks | Flag for review |
| Count >30 | Remove oldest |
| Similar entries exist | Consolidate (self-improvement) |
