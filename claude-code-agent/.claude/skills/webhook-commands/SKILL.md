---
name: webhook-commands
description: Command patterns for webhook-triggered tasks (GitHub, Jira, Slack, Sentry).
---

# Webhook Commands Skill

> Parse commands from webhooks → Route to correct agent → Respond to source.

## GitHub PR/Issue Comment Commands

| Command | Aliases | Action | Route To |
|---------|---------|--------|----------|
| `@agent analyze` | `/analyze` | Analyze issue/PR | planning |
| `@agent implement` | `/implement` | Implement changes | executor |
| `@agent approve` | `/approve`, `LGTM` | Merge PR | service-integrator |
| `@agent help` | `/help` | List commands | Brain (direct) |

### Command Recognition
```python
COMMANDS = {
    "analyze": ["@agent analyze", "/analyze"],
    "implement": ["@agent implement", "/implement"],
    "approve": ["@agent approve", "/approve", "lgtm"],
}

def parse_command(comment_body: str) -> str | None:
    body = comment_body.lower().strip()
    for cmd, aliases in COMMANDS.items():
        if any(alias in body for alias in aliases):
            return cmd
    return None
```

### Immediate Response (Required)
```bash
# Add 👀 reaction to show processing
gh api repos/{owner}/{repo}/issues/comments/{id}/reactions \
  -f content="eyes"
```

---

## Jira Webhook Triggers

| Trigger | Condition | Route To |
|---------|-----------|----------|
| Issue created | Label = `AI-Fix` | planning |
| Issue updated | Label added = `AI-Fix` | planning |
| Issue assigned | Assignee = `ai-agent` | planning |

### Label Check
```python
def should_process_jira(payload: dict) -> bool:
    labels = payload.get("issue", {}).get("fields", {}).get("labels", [])
    return "AI-Fix" in labels
```

### Required Response
After processing, MUST comment on Jira ticket:
```bash
jira issue comment {JIRA_KEY} \
  "Analysis complete. PR: {PR_URL}"
```

---

## Sentry Alert Triggers

| Alert Type | Action |
|------------|--------|
| `issue.created` | Create analysis task |
| `issue.resolved` | Close related Jira |
| `metric_alert.triggered` | Notify Slack |

---

## Slack Command Triggers

| Command | Action |
|---------|--------|
| `/agent status` | Report system status |
| `/agent analyze {url}` | Analyze GitHub/Jira link |
| Mention `@agent` | Parse and route |

---

## Response Protocol

**Every webhook-triggered task MUST:**

1. **Acknowledge immediately** (reaction, ephemeral message)
2. **Process asynchronously** (queue task)
3. **Report back to source** (comment, update)
4. **Notify Slack** (completion or failure)

---

## Error Responses

```bash
# GitHub: Comment on failure
gh pr comment {PR_NUMBER} --body "❌ Error: {message}"

# Jira: Comment on failure
jira issue comment {JIRA_KEY} "❌ Processing failed: {message}"

# Slack: Always notify
curl -X POST "$SLACK_WEBHOOK_URL" \
  -d '{"text": "⚠️ Webhook task failed: {error}"}'
```
