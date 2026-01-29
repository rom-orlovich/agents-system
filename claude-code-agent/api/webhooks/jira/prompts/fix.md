# Implement Fix for Jira Ticket

Implement a fix for this Jira ticket:

{{issue.key}}: {{issue.fields.summary}}

{{issue.fields.description}}

Project: {{issue.fields.project.name}}

**User Request:** {{_user_content}}

**Full Comment:**
{{comment.body}}

1. Implement fix addressing the user request.
2. Save summary to file.
3. Post summary back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} summary.md
