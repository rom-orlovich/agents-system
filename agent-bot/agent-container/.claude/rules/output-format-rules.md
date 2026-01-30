# Output Format Rules

## Enforcement Level
HIGH - Should be followed for all user-facing output

## Core Principle
All agent output must be clear, structured, actionable, and user-friendly.

## Markdown Formatting

### Required Structure
```markdown
## [Title] [Emoji]

**[Key Info]:** [Value]

### [Section]
[Content]

### [Another Section]
[Content]

---
*[Footer with metadata]*
```

### Headings
- H2 (`##`) for main title
- H3 (`###`) for sections
- NO H1 (reserved for PR/issue titles)
- NO H4+ (too granular)

### Emphasis
- **Bold** for labels, status, important info
- *Italic* for footnotes, metadata
- `Code` for identifiers, file paths, commands
- NO ~~strikethrough~~, NO __underline__

## Code Blocks

### With Language
```python
def example():
    return "Always specify language"
```

### File References
```python
# file: core/task_worker.py:28
async def process_task(task_data: dict):
    pass
```

## Status Indicators

### Required Emojis
- ✅ Success, completed, passed
- ❌ Failure, error, critical issue
- ⚠️ Warning, needs attention
- 🔵 Info, suggestion
- 🟡 Medium priority
- 🔴 High priority
- 🚀 Excellent, approved
- ⏱️ Timeout, in progress
- 🔧 Refactoring, changes
- 🧪 Tests, testing
- 📊 Metrics, analytics
- 🤖 Agent-generated

### Prohibited Emojis
- NO 😀😃😄 (too casual)
- NO 💩 (unprofessional)
- NO ❤️💯🔥 (excessive)

## Lists

### Unordered
```markdown
- Item with clear description
- Another item with details
  - Sub-item if needed
```

### Ordered
```markdown
1. First step with action
2. Second step with action
3. Third step with action
```

### Checklists
```markdown
- [ ] Pending task
- [x] Completed task
```

## Tables

### For Structured Data
```markdown
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Coverage | 65% | 92% | +27% |
| Complexity | 25 | 8 | -68% |
```

## Links

### Format
```markdown
[Descriptive Text](url)
```

### Internal References
```markdown
See [security rules](security-rules.md)
Related to [issue #123](#)
```

## Code References

### File and Line
```markdown
**Location:** `core/task_worker.py:28`
**File:** `api/routes.py:45-67`
```

### Function/Class
```markdown
**Function:** `process_task()`
**Class:** `ResultPoster`
**Method:** `ResultPoster.post_result()`
```

## Error Messages

### User-Friendly
```markdown
## Error in Task Execution ❌

I encountered an error while processing your request:

**Error:** Repository not found

**Possible causes:**
- Repository name is incorrect
- Repository is private and I don't have access
- Repository was deleted

**Next steps:**
1. Verify the repository exists
2. Check my access permissions
3. Try again or contact support

Task ID: task-abc-123
```

### NOT Like This
```markdown
ERROR: HTTPException 404 at line 45 in routes.py
Stack trace: [10 lines of Python traceback]
```

## Success Messages

### Clear and Actionable
```markdown
## Code Review Complete ✅

**Quality Score:** 8/10

I reviewed 5 files and found 3 minor issues.

### Issues Found
1. **Type Safety** in `core/task_worker.py:28`
2. **Missing Error Handling** in `api/routes.py:45`

### Recommendations
- Replace `Any` with `MCPClientProtocol`
- Add try/except for external API calls

**Merge Recommendation:** Approve with minor changes
```

## Progress Updates

### For Long-Running Tasks
```markdown
## Task Progress ⏱️

**Status:** In Progress (75% complete)

### Completed
✅ Repository cloned
✅ Code indexed
✅ Security scan

### In Progress
⏸️ Test coverage analysis

### Pending
- Performance analysis
- Generate report
```

## Metrics & Numbers

### Format
- Percentages: `85%` (no space)
- Currency: `$0.123 USD`
- Time: `45.2 seconds`, `5 minutes`
- Counts: `12 files`, `3 issues`
- Ratios: `8/10`, `12 of 15`

### Comparisons
```markdown
**Before:** 65% (+42 lines)
**After:** 92% (-15 lines)
**Delta:** +27% (-57 lines total)
```

## Footer Metadata

### Required
```markdown
---
*Automated review by agent-bot • Task ID: task-abc-123*
*Generated in 45.2 seconds • Cost: $0.123*
```

### Optional
```markdown
*Need help? See [documentation](#)*
*Report issues: [GitHub](#)*
```

## Prohibited Patterns

### NO Excessive Markdown
```markdown
# HEADING
## **BOLD HEADING**  <!-- Wrong -->
***ITALIC BOLD***     <!-- Wrong -->
```

### NO Walls of Text
Break into sections, use lists, add whitespace.

### NO Technical Jargon Without Explanation
```markdown
MCPClientProtocol  <!-- Needs context for users -->
```
Better:
```markdown
`MCPClientProtocol` (interface for MCP communication)
```

### NO Ambiguous Language
```markdown
"Maybe try this" <!-- Wrong -->
"Something went wrong" <!-- Wrong -->
```
Better:
```markdown
"Recommended: [specific action]"
"Error: [specific error with cause]"
```

## Response Length

### Ideal
- Summary: 2-3 lines
- Details: 5-15 lines per section
- Total: < 500 lines for complex reports

### Avoid
- One-liners without context
- Novels (> 1000 lines)
- Repetitive content

## Tone

### Professional but Friendly
- Use "I" for agent actions
- Use "you" for user
- Active voice preferred
- Clear and direct

### Examples
✅ "I found 3 security issues in your code"
✅ "You can fix this by adding type hints"
❌ "3 security issues were found"
❌ "Type hints should be added"
