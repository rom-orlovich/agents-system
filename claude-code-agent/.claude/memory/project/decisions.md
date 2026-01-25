# Architecture Decisions

> Record of significant decisions and their rationale. Learn from past reasoning.

---

## Task Classification

### Decision: 3-Tier Complexity System
- **Context:** Need to route tasks efficiently without over-engineering simple requests
- **Decision:**
  - Tier 1 (Simple): Brain handles directly
  - Tier 2 (Standard): Single agent delegation
  - Tier 3 (Complex): Multi-agent with verification loop
- **Rationale:** Prevents over-delegation overhead for simple tasks while ensuring quality for complex ones

### Decision: Max 3 Iterations for Verification Loop
- **Context:** Risk of infinite loops in verification-rejection cycles
- **Decision:** Hard limit of 3 iterations, then escalate or deliver with caveats
- **Rationale:** Balances quality improvement with practical delivery needs

---

## Agent Architecture

### Decision: Verifier Uses Opus Model
- **Context:** Verifier needs strong critical thinking for quality assessment
- **Decision:** Use opus instead of sonnet for verifier agent
- **Rationale:** Higher reasoning capability justifies cost for quality gate role

### Decision: Self-Improvement Beyond Code
- **Context:** Originally scoped only to code refactoring
- **Decision:** Expand to agents, processes, and memory management
- **Rationale:** System improvement requires holistic optimization

---

## Memory Management

### Decision: Write Only After Verification
- **Context:** Need to store learnings but avoid storing incorrect patterns
- **Decision:** Only write to memory after verifier approves (≥90% confidence)
- **Rationale:** Ensures memory contains validated, high-quality learnings

---

*Last updated: System initialization*
