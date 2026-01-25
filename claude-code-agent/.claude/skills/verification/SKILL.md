---
name: verification
description: Multi-stage verification with confidence scoring, critical thinking, and actionable feedback for the Brain.
---

# Verification Skill

> Quality control and confidence assessment for complex multi-agent workflows.

---

## Core Principles

1. **Evidence-Based:** Every score must be backed by specific evidence
2. **Criteria-Mapped:** Assessment maps to PLAN.md completion criteria
3. **Actionable Gaps:** Rejections include specific fixes for specific agents
4. **Iteration-Aware:** Feedback urgency scales with iteration count

---

## Confidence Scoring Rubric

| Component | Weight | 100% | 75% | 50% | 25% |
|-----------|--------|------|-----|-----|-----|
| **Completeness** | 40% | All criteria met | Minor gaps | Several gaps | Major missing |
| **Correctness** | 30% | Tests pass, no bugs | Minor issues | Some bugs | Broken |
| **Consistency** | 20% | Follows all patterns | Minor deviations | Inconsistent | Violates patterns |
| **Documentation** | 10% | Clear, complete | Adequate | Sparse | Missing |

### Score Calculation
```
Score = (Completeness × 0.4) + (Correctness × 0.3) + (Consistency × 0.2) + (Documentation × 0.1)
```

### Threshold
- **≥ 90%:** APPROVE
- **< 90%:** REJECT with gap analysis

---

## Critical Thinking Questions

Before scoring, systematically ask:

| Category | Question |
|----------|----------|
| **Function** | Does it actually work? Did you test it? |
| **Edge Cases** | What happens with null/empty/extreme inputs? |
| **Requirements** | Does it match what the user asked for? |
| **Completeness** | Check each PLAN.md criterion — any missing? |
| **Regression** | Could this break existing functionality? |
| **Security** | Any injection, XSS, auth bypass risks? |
| **Finish** | Any TODOs, placeholders, or incomplete logic? |

---

## Verification Procedure

### Step 1: Gather Inputs
```
- Original user request
- PLAN.md with completion criteria
- Agent outputs (code, docs, tests)
- Current iteration number
```

### Step 2: Validate Each Criterion
For each criterion in PLAN.md:
```
Criterion: [description]
├── Status: MET / PARTIAL / NOT MET
├── Evidence: [what proves the status]
└── Notes: [concerns or observations]
```

### Step 3: Run Tests (if applicable)
```bash
# Unit tests
pytest tests/unit/ -v --tb=short

# Check for regressions
pytest tests/ -x --lf

# Build verification
make build 2>&1 | tail -20

# Type check
mypy src/ --strict
```

### Step 4: Score Components
Calculate each component score:
```
Completeness: X/100
Correctness:  X/100
Consistency:  X/100
Documentation: X/100
─────────────────────
Weighted Total: X%
```

### Step 5: Formulate Response
Based on score, use appropriate template.

---

## Gap Analysis Format

When rejecting, structure gaps clearly:

```
## Gap Analysis

### Gap 1: {Title}
- **Problem:** What is wrong or missing
- **Impact:** Why it matters for the user
- **Evidence:** How you discovered it
- **Agent:** Which sub-agent should fix
- **Fix:** Specific actionable instruction

### Gap 2: {Title}
...
```

---

## Iteration-Adjusted Feedback

| Iteration | Tone | Detail Level | Focus |
|-----------|------|--------------|-------|
| 1 | Educational | High | Explain gaps thoroughly |
| 2 | Direct | Medium | Focus on remaining gaps |
| 3 (Final) | Decisive | Summary | Force decision |

### Iteration 3 Guidance
```
If still rejecting at iteration 3:

"Brain, this is iteration 3 of 3. Confidence remains at X%.

Unresolved gaps:
1. [gap]
2. [gap]

Recommended action:
[ ] Deliver with documented limitations:
    - [limitation 1]
    - [limitation 2]

[ ] Escalate to user for decision:
    - Explain tradeoffs
    - Let user choose acceptable quality level

Do NOT loop back. End the verification cycle."
```

---

## Test Verification Checklist

```
[ ] Unit tests exist and pass
[ ] Edge cases covered (null, empty, max)
[ ] Error cases handled
[ ] Integration tests pass (if applicable)
[ ] No regression in existing tests
[ ] Test coverage adequate for changes
```

---

## Code Review Checklist

```
[ ] Logic correct and complete
[ ] No hardcoded values that should be config
[ ] Error handling present where needed
[ ] No security vulnerabilities (injection, XSS)
[ ] Follows project code style
[ ] No TODOs or placeholder code
[ ] Performance acceptable
```

---

## Anti-Patterns

| Avoid | Instead |
|-------|---------|
| Vague gaps ("needs improvement") | Specific gaps with exact fixes |
| Scoring on effort | Score on results only |
| Approving to end loop | Honest scoring every time |
| Same feedback repeatedly | Escalate if gap persists |
| Ignoring iteration count | Adjust urgency per iteration |

---

## Integration with Memory

After APPROVE:
- Brain should write successful patterns to `.claude/memory/project/patterns.md`
- Any lessons learned to appropriate memory file

After REJECT:
- Brain should read `.claude/memory/project/failures.md` before re-delegating
- Look for similar past failures to avoid repeating
