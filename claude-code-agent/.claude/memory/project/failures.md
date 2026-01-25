# Failure Learnings

> What didn't work and why. Read before re-delegation to avoid repeating mistakes.

---

## Common Pitfalls

### Infinite Verification Loop
- **What happened:** Verification kept rejecting without progress
- **Root cause:** Gap analysis too vague for agents to act on
- **Lesson:** Verifier must provide specific, actionable instructions

### Over-Delegation
- **What happened:** Simple questions routed through full agent flow
- **Root cause:** No complexity classification before delegation
- **Lesson:** Always classify task tier before delegating

### Context Loss in Re-delegation
- **What happened:** Re-delegated agent didn't have previous work context
- **Root cause:** Brain didn't preserve working parts when re-instructing
- **Lesson:** Always include "Previous work" context in re-delegation

---

## Anti-Patterns

### Restarting from Scratch
- On verification failure, don't restart entire implementation
- Only re-work the failing criteria
- Preserve validated portions

### Approval to Avoid Conflict
- Verifier approving to end loop despite gaps
- Leads to low-quality deliveries
- Must score honestly based on evidence

---

*Last updated: System initialization*
