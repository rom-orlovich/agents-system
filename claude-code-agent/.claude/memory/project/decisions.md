# Architecture Decisions

> Why we chose X over Y. **Max 30 entries. Auto-prune >30 days unused.**

---

## Entry Format
```
### [ID] Decision Title
Context: Problem | Decision: Choice | Rationale: Why | Added: YYYY-MM-DD
```

---

## Task System

### [D01] 3-Tier Complexity
Context: Route tasks efficiently | Decision: Simple/Standard/Complex tiers | Rationale: Prevents over-delegation | Added: 2025-01-25

### [D02] Standard = 2 Agents Max
Context: Need planning for non-trivial tasks | Decision: Planning → Executor for standard | Rationale: Ensures defined success criteria | Added: 2025-01-25

### [D03] Max 3 Iterations
Context: Prevent infinite verification loops | Decision: Hard limit 3, then escalate | Rationale: Balances quality with delivery | Added: 2025-01-25

---

## Agent Architecture

### [D04] Verifier Uses Opus
Context: Quality gate needs strong reasoning | Decision: Opus model for verifier | Rationale: Critical thinking justifies cost | Added: 2025-01-25

### [D05] Verifier Runs Scripts
Context: Subjective verification unreliable | Decision: Mandatory script execution | Rationale: Objective evidence, not opinions | Added: 2025-01-25

### [D06] Self-Improvement Holistic
Context: Originally code-only | Decision: Expand to agents, processes, memory | Rationale: System needs full optimization | Added: 2025-01-25

---

## Memory System

### [D07] Write Only After Verification
Context: Avoid storing incorrect patterns | Decision: Memory writes only after ≥90% | Rationale: Ensures validated learnings | Added: 2025-01-25

### [D08] Max 30 Entries Per File
Context: Prevent memory inflation | Decision: Hard limit, prune oldest | Rationale: Keep memory practical and fast | Added: 2025-01-25

### [D09] Age-Based Pruning
Context: Old learnings become stale | Decision: Archive >30 days unused | Rationale: Keep memory relevant | Added: 2025-01-25

---

## Document Standards

### [D10] Max 150 Lines
Context: Long docs waste context | Decision: 150 line limit for main files | Rationale: Forces conciseness | Added: 2025-01-25

---

## Pruning Rules

Same as patterns.md - consolidate via self-improvement when needed.
