# Address Jira Change Request

Changes requested for Jira ticket {{issue.key}}.

**User Feedback:** {{_user_content}}

**Original Comment:**
{{comment.body}}

1. Analyze the feedback
2. Revise the plan/implementation
3. Post updated plan back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} revised_plan.md
