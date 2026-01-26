---
name: jira-code-plan
description: Handle Jira ticket assignee change to AI Agent. Analyze issue and post implementation plan to Jira.
tools: Read, Write, Edit, Grep, Bash, Glob
model: opus
context: inherit
skills:
  - discovery
  - jira-operations
  - slack-operations
  - github-operations
---

# Jira Code Plan Agent

> When assigned a Jira ticket, analyze and create implementation plan

## Trigger

- Jira webhook: assignee changed to "AI Agent"
- Jira webhook: issue created with AI Agent assignee
- Commands: `@agent plan`, `@agent analyze`

## Flow

```
1. PARSE TICKET
   Extract: summary, description, acceptance criteria
   Identify: issue type (bug, feature, task)
   Get: linked issues, attachments

2. CODE DISCOVERY
   Invoke: discovery skill
   Find: relevant files, dependencies
   Analyze: complexity, impact

3. CREATE PLAN
   Generate: step-by-step implementation plan
   Estimate: complexity (S/M/L/XL)
   Identify: risks, dependencies

4. POST PLAN TO JIRA
   Use: jira-operations skill
   Target: ticket comment with plan

5. NOTIFY VIA SLACK (optional)
   Use: slack-operations skill
   Post: plan summary with approval buttons
```

## Response Posting

**CRITICAL:** After analysis, ALWAYS post plan to Jira ticket.

```bash
# Post plan as Jira comment
.claude/skills/jira-operations/scripts/post_comment.sh \
    "{issue_key}" \
    "{plan_content}"
```

Or via Python:

```python
from api.webhooks.jira import post_jira_comment

await post_jira_comment(
    payload={"issue": {"key": "{issue_key}"}},
    message="{plan_content}"
)
```

## Plan Format

```markdown
## Implementation Plan

### Summary
{brief_overview}

### Analysis
- **Issue Type:** {bug/feature/task}
- **Complexity:** {S/M/L/XL}
- **Estimated Changes:** {file_count} files

### Relevant Code
{file_paths_with_descriptions}

### Steps
1. {step_1}
2. {step_2}
3. ...

### Risks & Dependencies
{risks_list}

### Acceptance Criteria
{criteria_from_ticket}

---
*Plan created by AI Agent*
*Reply with "@agent approve" to proceed with implementation*
```

## Metadata Access

```python
metadata = json.loads(task.source_metadata)
payload = metadata.get("payload", {})
issue = payload.get("issue", {})
issue_key = issue.get("key")
fields = issue.get("fields", {})
summary = fields.get("summary")
description = fields.get("description")
```

## Slack Notification (Optional)

If SLACK_NOTIFICATION_CHANNEL is configured:

```bash
.claude/skills/slack-operations/scripts/notify_approval_needed.sh \
    "{issue_key}" \
    "{plan_summary}" \
    "{pr_url_if_exists}"
```

## Approval Flow

After posting plan:
1. Wait for `@agent approve` in Jira comment
2. Or approval via Slack button
3. On approval: trigger `executor` agent
4. Timeout 24h: escalate

## Completion

- Plan posted to Jira
- Slack notification sent (if configured)
- Task status: waiting_approval
