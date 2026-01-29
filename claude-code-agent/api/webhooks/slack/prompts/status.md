# Check Task Status from Slack

User is checking task status from Slack.

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Check for any running or recent tasks.
2. Provide status update.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} status.md {{event.ts}}
