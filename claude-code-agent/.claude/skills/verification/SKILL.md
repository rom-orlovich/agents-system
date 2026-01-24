---
name: verification
description: Multi-stage verification and confidence assessment. Evaluates task results against completion criteria and determines if further improvement is needed.
---

# Verification Skill

> Quality control and confidence assessment for agentic workflows.

## Core Principles

1. **Criteria-Based Review:** Every assessment must be mapped to the original "Completion Criteria".
2. **Confidence Scoring:** Assign a numeric score (0-100%) based on evidence.
3. **Actionable Gaps:** If confidence is < 90%, identify exactly what is missing or incorrect.
4. **Iterative Loop:** Feedback must be specific enough for the `brain` to guide sub-agents effectively.

## Confidence Assessment Rubric

| Component | Weight | Check |
|-----------|--------|-------|
| **Completeness** | 40% | Are all requirements met? |
| **Correctness** | 30% | Is the code/result bug-free and functional? |
| **Consistency** | 20% | Does it follow project patterns and styles? |
| **Documentation** | 10% | Is the change properly explained/documented? |

## Feedback Protocol

When a result is rejected, format the feedback as:
1. **Confidence Score:** X%
2. **Identified Gaps:** List specific missing or failing items.
3. **Improvement Instructions:** Clear, actionable steps for the `brain` to re-delegate.
