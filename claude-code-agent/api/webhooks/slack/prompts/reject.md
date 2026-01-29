# Process Slack Rejection

Rejection/cancellation received from Slack.

**User Comment:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Process the rejection.
2. Cancel any pending actions.
3. Post confirmation back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} cancelled.md {{event.ts}}
