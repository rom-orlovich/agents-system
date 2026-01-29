# Execute Slack Request

Execute this request from Slack:

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Execute request.
2. Save result/summary to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} result.md {{event.ts}}
