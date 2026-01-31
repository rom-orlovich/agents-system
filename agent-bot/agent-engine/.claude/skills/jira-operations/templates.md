# Jira Response Templates

Templates for posting responses back to Jira after completing tasks.

## Comment Templates

### Analysis Complete

```markdown
## ✅ Analysis Complete

**Summary:** {brief_summary}

### Findings

{findings_list}

### Root Cause

{root_cause}

### Recommendations

{recommendations}

### Next Steps

{next_steps}

---

_Automated analysis by Claude Agent_
```

**MCP Tool:**

```json
{
  "tool": "jira:add_jira_comment",
  "arguments": {
    "issue_key": "{issue_key}",
    "body": "{formatted_markdown}"
  }
}
```

### Implementation Complete

```markdown
## ✅ Implementation Complete

**Summary:** {summary}

### Changes Made

{changes_list}

### Files Modified

{files_list}

### Testing

{testing_notes}

### Deployment Notes

{deployment_notes}

---

_Automated implementation by Claude Agent_
```

### Bug Fix Complete

```markdown
## ✅ Bug Fix Complete

**Issue:** {issue_key}

### Summary

Fixed {bug_description}

### Root Cause

{root_cause}

### Solution

{solution_description}

### Changes

- {change_1}
- {change_2}

### Testing

- [x] Unit tests passing
- [x] Integration tests passing
- [x] Manual testing completed

### Related PR

{pr_link}

---

_Automated fix by Claude Agent_
```

### Code Review Complete

```markdown
## ✅ Code Review Complete

**Summary:** {summary}

### Review Findings

{findings_list}

### Suggestions

{suggestions_list}

### Approval Status

{approval_status}

### Next Steps

{next_steps}

---

_Automated review by Claude Agent_
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

## Status Update Template

### Status Change Notification

```markdown
## Status Update

**Previous Status:** {old_status}
**New Status:** {new_status}

### Reason

{reason}

### Next Actions

{next_actions}

---

_Automated update by Claude Agent_
```

## Best Practices

1. **Always include issue key** in response
2. **Use markdown** - MCP automatically converts to ADF
3. **Include structured sections** - Headers, lists, code blocks
4. **Link to related resources** - GitHub PRs, Sentry issues, etc.
5. **Mark as automated** - Always include "_Automated by Claude Agent_"
6. **Use appropriate emoji** - ✅ for success, ❌ for errors
7. **Keep comments structured** - Use headers, lists, code blocks
8. **Include actionable next steps** - What should happen next?

## Markdown to ADF Conversion

**Note:** MCP server automatically converts markdown to ADF format. Use standard markdown:

- `# Header` → Heading 1
- `## Subheader` → Heading 2
- `- List item` → Bullet list
- `` `code` `` → Inline code
- `**bold**` → Bold text
- `*italic*` → Italic text

No manual conversion needed - just use markdown in the `body` parameter.
