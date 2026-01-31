# Verification Response Templates

Templates for reporting verification results with confidence scoring.

## Verification Complete Template

### Approval (Score ≥90%)

```markdown
## ✅ Verification Complete - APPROVED

**Confidence Score:** {score}%

### Script Results

| Script       | Status  | Weight | Score        |
| ------------ | ------- | ------ | ------------ |
| test.sh      | ✅ Pass | 40%    | 40           |
| build.sh     | ✅ Pass | 20%    | 20           |
| lint.sh      | ✅ Pass | 20%    | 20           |
| typecheck.sh | ✅ Pass | 20%    | 20           |
| **Total**    | -       | 100%   | **{score}%** |

### Summary

All verification scripts passed. Code meets quality standards.

### Next Steps

Ready for merge/deployment.

---

_Automated verification by Claude Agent_
```

### Rejection (Score <90%)

```markdown
## ❌ Verification Complete - REJECTED

**Confidence Score:** {score}%

### Script Results

| Script       | Status             | Weight | Score             |
| ------------ | ------------------ | ------ | ----------------- |
| test.sh      | {test_status}      | 40%    | {test_score}      |
| build.sh     | {build_status}     | 20%    | {build_score}     |
| lint.sh      | {lint_status}      | 20%    | {lint_score}      |
| typecheck.sh | {typecheck_status} | 20%    | {typecheck_score} |
| **Total**    | -                  | 100%   | **{score}%**      |

### Gaps Identified

{gaps_list}

### Next Steps

{next_steps}

---

_Automated verification by Claude Agent_
```

## Gap Analysis Template

### Gap Details

````markdown
### Gap: {gap_title}

**Script:** {script_name}
**Exit Code:** {exit_code}

**Output:**

```bash
{script_output}
```
````

**Agent:** {agent_name}
**Fix:** {fix_instruction}

````

## Iteration Templates

### First Iteration

```markdown
## 🔄 Verification - Iteration 1

**Score:** {score}%

### Detailed Feedback
{detailed_feedback}

### Educational Notes
{educational_notes}

### Next Steps
{next_steps}
````

### Second Iteration

```markdown
## 🔄 Verification - Iteration 2

**Score:** {score}%

### Remaining Issues

{remaining_issues}

### Focus Areas

{focus_areas}

### Next Steps

{next_steps}
```

### Final Iteration

```markdown
## 🔄 Verification - Final Iteration

**Score:** {score}%

### Status

{status_decision}

### Options

{options_list}

### Recommendation

{recommendation}
```

## Error Response Template

### Verification Failed

```markdown
## ❌ Verification Failed

**Error:** {error_message}

### Details

{error_details}

### Scripts Run

{scripts_run_list}

### Troubleshooting

{troubleshooting_steps}
```

## Best Practices

1. **Show score calculation** - Weighted breakdown
2. **List all script results** - Exit codes and outputs
3. **Provide specific gaps** - File:line fixes
4. **Include script output** - Actual error messages
5. **Use tables** - For score breakdown
6. **Structure by iteration** - Clear progression
7. **Be objective** - Based on exit codes only
