---
name: verification
description: Script-based verification with confidence scoring. Use when verifying code quality, running linting/type checking, or validating code changes before completion.
---

# Verification Skill

> Run scripts → Score objectively → No opinions.

## Quick Reference

- **Templates**: See [templates.md](templates.md) for reporting verification results

## Core Rule

**NEVER approve without running scripts.** Exit codes are truth.

---

## Scripts (Mandatory)

```bash
# Run ALL before scoring
.claude/scripts/verification/test.sh      # 40% weight
.claude/scripts/verification/build.sh     # 20% weight
.claude/scripts/verification/lint.sh      # 20% weight
.claude/scripts/verification/typecheck.sh # 20% weight
```

## Score Calculation

```
Score = (test×0.4) + (build×0.2) + (lint×0.2) + (typecheck×0.2)
Where: pass=100, fail=0
```

| Total Score | Decision         |
| ----------- | ---------------- |
| ≥90%        | APPROVE          |
| <90%        | REJECT with gaps |

---

## Verification Steps

1. **Read** PLAN.md criteria
2. **Run** each script, capture exit code + output
3. **Map** criteria to script results
4. **Calculate** weighted score
5. **Format** response (APPROVE or REJECT)

---

## Script Result Recording

| Script       | Exit | Weight | Score  |
| ------------ | ---- | ------ | ------ |
| test.sh      | 0/1  | 40%    | 0/40   |
| build.sh     | 0/1  | 20%    | 0/20   |
| lint.sh      | 0/1  | 20%    | 0/20   |
| typecheck.sh | 0/1  | 20%    | 0/20   |
| **Total**    | -    | 100%   | **X%** |

---

## Gap Analysis (For Rejections)

Each gap must include:

```
Gap: [Title]
- Script: Which failed
- Output: Relevant error
- Agent: Who should fix
- Fix: Specific instruction
```

---

## Iteration Handling

| Iteration | Tone                         |
| --------- | ---------------------------- |
| 1         | Detailed, educational        |
| 2         | Direct, focused on remaining |
| 3 (final) | Force decision               |

**At iteration 3:** Either "Deliver with caveats" OR "Escalate to user"

---

## Anti-Patterns

| Don't               | Do                           |
| ------------------- | ---------------------------- |
| "Looks good to me"  | Run scripts, show exit codes |
| Approve to end loop | Score based on evidence      |
| Vague feedback      | Specific file:line fixes     |
