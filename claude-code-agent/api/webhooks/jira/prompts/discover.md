# Discover Code for Jira Ticket

Discover code and provide insights for Jira ticket {{issue.key}}.

**User Request:** {{_user_content}}

**Original Comment:**
{{comment.body}}

## Parse Discovery Sources

Extract source information from user request:
- Source type: github, confluence, or codebase
- Source reference: repository path, page URL, file path, or search terms
- What to discover: functions, classes, patterns, relationships

Examples:
- "@agent discover from github owner/repo path/to/file.py"
- "@agent discover from confluence space:page"
- "@agent discover authentication flow"

## Steps

1. Parse user request to identify discovery sources
2. Use discovery skill to search codebase or fetch from external sources:
   - If GitHub: Use github-operations skill to fetch code
   - If Confluence: Fetch content from Confluence
   - If codebase: Use discovery skill to search locally
3. Analyze discovered code/content:
   - Understand functionality and relationships
   - Identify patterns and dependencies
   - Extract key insights
4. Format findings with code snippets, file paths, and explanations
5. Post results back to Jira ticket:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} discovery_results.md

Include in results:
- Source references (GitHub URLs, Confluence links, file paths)
- Key findings and insights
- Code snippets with explanations
- Related files and dependencies
