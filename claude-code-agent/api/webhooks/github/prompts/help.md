# GitHub Agent Help

User asked for help on GitHub issue #{{issue.number}} in {{repository.full_name}}.

**User's Question:** {{_user_content}}

Generate a helpful response listing available commands and how to use them.

Available commands:
- @agent analyze - Analyze an issue or PR
- @agent plan - Create an implementation plan
- @agent fix - Implement a fix (requires approval)
- @agent review - Review a pull request
- @agent approve - Approve a plan or PR
- @agent reject - Request changes
- @agent improve - Improve/refactor code (requires approval)
- @agent help - Show this help message

Post response using:
python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} help.md
