# GitHub Response Templates

Templates for posting responses back to GitHub after completing tasks.

## Issue Comment Template

### Task Complete

```markdown
## ✅ Task Complete

**Summary:** {brief_summary}

### Findings

{findings_list}

### Changes Made

{changes_list}

### Next Steps

{next_steps}

---

_Automated response by Claude Agent_
```

**MCP Tool:**

```json
{
  "tool": "github:add_issue_comment",
  "arguments": {
    "owner": "{owner}",
    "repo": "{repo}",
    "issue_number": {issue_number},
    "body": "{formatted_markdown}"
  }
}
```

### Analysis Complete

```markdown
## ✅ Analysis Complete

**Issue:** #{issue_number}

### Summary

{summary}

### Findings

{findings_list}

### Recommendations

{recommendations}

### Files Analyzed

{files_list}

---

_Automated analysis by Claude Agent_
```

### Bug Fix Complete

```markdown
## ✅ Bug Fix Complete

**Issue:** #{issue_number}
**Branch:** `{branch_name}`

### Summary

Fixed {bug_description}

### Changes

- {change_1}
- {change_2}

### Testing

- [x] Tests passing
- [x] Manual testing completed

### PR Created

See PR #{pr_number} for review.

---

_Automated fix by Claude Agent_
```

## PR Comment Template

### Code Review Complete

```markdown
## ✅ Code Review Complete

**PR:** #{pr_number}

### Summary

{review_summary}

### Findings

{findings_list}

### Suggestions

{suggestions_list}

### Approval Status

{approval_status}

---

_Automated review by Claude Agent_
```

### PR Ready for Review

```markdown
## ✅ PR Ready for Review

**PR:** #{pr_number}

### Summary

{summary}

### Changes

{changes_list}

### Testing

{testing_notes}

### Checklist

- [x] Code follows project conventions
- [x] Tests included/updated
- [x] Documentation updated
- [x] No breaking changes

---

_Automated by Claude Agent_
```

## Error Response Template

### Task Failed

```markdown
## ❌ Task Failed

**Error:** {error_message}

### Details

{error_details}

### Troubleshooting

{troubleshooting_steps}

### Next Steps

{next_steps}

---

_Automated response by Claude Agent_
```

## Best Practices

1. **Always include issue/PR number** in response
2. **Use clear structure** - Headers, lists, code blocks
3. **Include actionable next steps** - What should happen next?
4. **Mark as automated** - Always include "_Automated by Claude Agent_"
5. **Use appropriate emoji** - ✅ for success, ❌ for errors, ⚠️ for warnings
6. **Keep it concise** - Focus on key findings and actions
7. **Link to related resources** - PRs, commits, files
