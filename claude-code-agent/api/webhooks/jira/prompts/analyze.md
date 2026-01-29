# Analyze Jira Ticket

Analyze this Jira ticket:

Key: {{issue.key}}
Summary: {{issue.fields.summary}}
Description: {{issue.fields.description}}

Project: {{issue.fields.project.name}}

**User Request:** {{_user_content}}

**Full Comment:**
{{comment.body}}

1. Perform analysis addressing the user request.
2. Save to file (e.g., analysis.md).
3. If analysis indicates code changes are needed OR if user requests implementation:
   - Create a Draft PR with the analysis/plan
   - Use github-operations skill to create PR:
     .claude/skills/github-operations/scripts/create_draft_pr.sh owner/repo "[{{issue.key}}] Analysis" "$(cat analysis.md)"
   - Extract PR URL from output
   - Post analysis back to Jira with PR link:
     python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} analysis.md
   - Include PR URL in the Jira comment
4. If no code changes needed (test error, documentation only, etc.):
   - Post analysis back to Jira:
     python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} analysis.md
   - Clearly state "No PR created - no code changes required"

Always create a PR if:
- Code changes are needed
- User explicitly requests implementation
- Analysis identifies bugs or improvements requiring code changes

Do NOT create PR if:
- Analysis confirms it's a test error (no production bug)
- Only documentation updates needed
- Issue is already resolved
- User only requested analysis, not implementation
