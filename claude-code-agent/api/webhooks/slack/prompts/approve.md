# Process Slack Approval

Approval received from Slack.

**User Comment:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Process the approval.
2. Proceed with the pending action if applicable.
3. Post confirmation back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} confirmation.md {{event.ts}}
