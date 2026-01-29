# Jira Agent Help

User asked for help on Jira ticket {{issue.key}}.

**User's Question:** {{_user_content}}

Generate a helpful response listing available commands and how to use them.

Available commands:
- @agent analyze - Analyze a Jira ticket
- @agent plan - Create an implementation plan
- @agent fix - Implement a fix (requires approval)
- @agent approve - Approve a plan
- @agent reject - Request changes
- @agent improve - Improve/refactor code (requires approval)
- @agent discover - Discover code insights from GitHub/Confluence
- @agent help - Show this help message

Post response using:
python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} help.md
