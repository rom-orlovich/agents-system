# Discover Code from Slack

Discover code and provide insights from Slack.

**User Request:** {{_user_content}}

**Full Message:**
{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Parse the user's query to understand what code they want to discover:
   - Function/class names
   - File paths or patterns
   - Feature/functionality descriptions
   - Code relationships or dependencies
2. Use discovery skill to search and analyze codebase:
   - Find relevant files and functions
   - Understand code flow and relationships
   - Extract code snippets and examples
   - Identify dependencies and usage patterns
3. Format insights with code snippets, file paths, and explanations.
4. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} code_discovery.md {{event.ts}}
