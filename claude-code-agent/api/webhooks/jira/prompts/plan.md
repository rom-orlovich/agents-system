# Create Plan for Jira Ticket

Create a detailed plan to resolve this Jira ticket:

{{issue.key}}: {{issue.fields.summary}}

{{issue.fields.description}}

Project: {{issue.fields.project.name}}

**User Request:** {{_user_content}}

**Full Comment:**
{{comment.body}}

1. Create plan addressing the user request.
2. Save to file (e.g., plan.md).
3. Post plan back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} plan.md
