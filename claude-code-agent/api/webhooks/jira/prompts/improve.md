# Improve Code for Jira Ticket

Improvement requested for Jira ticket {{issue.key}}.

**User Request:** {{_user_content}}

**Original Comment:**
{{comment.body}}

## Parse External Sources

If the user request mentions external sources (e.g., "by github/confluence code from xyz"), extract:
- Source type: github, confluence, or other
- Source reference: repository path, page URL, or identifier
- Code location: file path, function name, or section

Examples:
- "@agent improve jira ticket by github code from owner/repo path/to/file.py"
- "@agent improve jira ticket by confluence code from space:page:section"

## Steps

1. Parse user request to identify external source references if present
2. If external source specified:
   - Fetch code/content from GitHub (using github-operations skill) or Confluence
   - Analyze the external code/content
   - Understand how it relates to the Jira ticket
3. Analyze what needs improvement in the current codebase
4. Implement improvements based on external reference if provided
5. Post summary back to Jira with source references:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} improvement_summary.md

Include in summary:
- External sources referenced (if any)
- Improvements made
- Files modified
