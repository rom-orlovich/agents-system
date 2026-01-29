# Process Jira Approval

Approval received for Jira ticket {{issue.key}}.

**User Comment:** {{_user_content}}

**Original Comment:**
{{comment.body}}

1. Process the approval
2. Proceed with execution if all approvals received
3. Post confirmation back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} confirmation.md
