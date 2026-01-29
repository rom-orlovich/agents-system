# Analyze Slack Request

Analyze this Slack message:

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Perform analysis.
2. Save to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} analysis.md {{event.ts}}
