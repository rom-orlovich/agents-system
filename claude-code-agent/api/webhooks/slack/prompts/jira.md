# Query Jira from Slack

Query Jira ticket information from Slack.

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Extract ticket key(s) from the user's message (e.g., PROJ-123, TASK-456).
2. Use jira-operations skill to fetch ticket details:
   - Status, assignee, summary, description
   - Comments, attachments, linked issues
   - Sprint/board information if available
3. Format response with ticket information.
4. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} jira_query.md {{event.ts}}
