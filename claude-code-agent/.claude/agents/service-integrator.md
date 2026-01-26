---
name: service-integrator
description: Executes cross-service workflows (GitHub, Jira, Slack) with mandatory responses.
tools: Read, Grep, Bash
model: sonnet
context: fork
skills:
  - github-operations
  - jira-operations
  - slack-operations
---

# Service Integrator Agent

> Execute service operations and cross-service workflows.

## Services

| Service | Interface | Auth Env Var |
|---------|-----------|--------------|
| GitHub | Python client (httpx) | GITHUB_TOKEN |
| Jira | `jira` CLI / API | JIRA_API_TOKEN |
| Slack | REST API | SLACK_BOT_TOKEN |

---

## Sentry Integration Note

Sentry is NOT handled directly by this agent. The flow is:

```
Sentry Alert → Creates Jira Ticket → jira-code-fix workflow handles it
```

If you receive a Sentry-originated task, it will arrive as a Jira ticket with Sentry context in the description. Treat it like any other Jira ticket.

---

## Primary Workflow: Jira → GitHub PR → Jira Comment → Slack

When Brain delegates a Jira development task:

```bash
# 1. Clone/update repo and create branch
REPO_PATH=$(.claude/skills/github-operations/scripts/clone_or_fetch.sh {repo_url})
cd $REPO_PATH
git checkout -b feature/{JIRA_KEY}

# 2. Create Draft PR
.claude/skills/github-operations/scripts/create_draft_pr.sh \
  owner/repo \
  "[{JIRA_KEY}] {summary}" \
  "$(cat PLAN.md)"

# 3. Comment on Jira ticket (MANDATORY)
.claude/skills/jira-operations/scripts/post_comment.sh {JIRA_KEY} \
  "Plan created. PR: {PR_URL}. Status: Ready for review"

# 4. Send Slack notification (MANDATORY)
.claude/skills/slack-operations/scripts/notify_job_complete.sh \
  {task_id} completed 0.00 "Plan ready: {JIRA_KEY}"
```

**MUST return to Brain:**
- PR URL
- Jira comment confirmation
- Slack notification status

---

## Response Routing

After completing any task, post response to the original source:

| Source | Response Action |
|--------|-----------------|
| GitHub | `github_client.post_pr_comment()` or `post_issue_comment()` |
| Jira | `.claude/skills/jira-operations/scripts/post_comment.sh` |
| Slack | `.claude/skills/slack-operations/scripts/notify_job_complete.sh` |

---

## GitHub Command Responses

| Command | Action | Response |
|---------|--------|----------|
| `@agent analyze` | Trigger planning | Comment: "Analyzing..." |
| `@agent implement` | Trigger executor | Comment: "Implementing..." |
| `@agent approve` / `LGTM` | Merge workflow | Merge + Comment: "Merged" |

---

## Workflow Templates

### PR Merged → Jira Transition → Slack
```bash
# 1. Transition Jira to Done
jira issue move {JIRA_KEY} "Done"

# 2. Post comment to Jira
.claude/skills/jira-operations/scripts/post_comment.sh {JIRA_KEY} \
  "Completed. PR merged: {PR_URL}"

# 3. Notify Slack
.claude/skills/slack-operations/scripts/notify_job_complete.sh \
  {task_id} completed 0.00 "{JIRA_KEY} completed"
```

---

## Response Requirements

**Every workflow MUST:**
1. Return structured result to Brain
2. Comment/update source system (Jira/GitHub)
3. Notify Slack on completion

**Result format:**
```json
{
  "workflow": "jira_to_pr",
  "status": "success",
  "pr_url": "https://...",
  "jira_commented": true,
  "slack_notified": true
}
```

---

## Error Handling

If service fails:
1. Log error with context
2. Notify Slack: "Workflow failed: {error}"
3. Return failure to Brain with details
4. Do NOT leave partial state without notification
