# Slack Agent Help

User asked for help in Slack.

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Generate help message with available commands.
2. Save to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} help.md {{event.ts}}
