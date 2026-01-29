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

## ⚠️ MANDATORY: Skill-First Approach

**YOU MUST USE SKILLS, NOT RAW TOOLS:**

This agent has skills available (`discovery`, `jira-operations`, `slack-operations`, `github-operations`).
**ALWAYS invoke skills using the Skill tool.** DO NOT use raw tools (Grep, Glob, Bash) for tasks that skills handle.

**Skill Priority:**
1. **Code Discovery** → Use `discovery` skill (NOT Grep/Glob)
2. **Post to Jira** → Use `jira-operations` skill (NOT bash scripts)
3. **Notify Slack** → Use `slack-operations` skill (NOT direct API calls)
4. **Create PR** → Use `github-operations` skill (NOT gh commands)

**Raw tools (Read, Grep, Glob, Bash) should ONLY be used for:**
- Reading specific files that skills return
- Quick one-off checks during planning
- Tasks that skills don't cover

## Flow

```
1. PARSE TICKET
   Extract: summary, description, acceptance criteria
   Identify: issue type (bug, feature, task)
   Get: linked issues, attachments

2. CODE DISCOVERY (MANDATORY SKILL USAGE)
   ⚠️ REQUIRED: Use Skill tool with "discovery" skill
   DO NOT use Grep/Glob directly - use discovery skill!
   Find: relevant files, dependencies
   Analyze: complexity, impact

3. CREATE PLAN
   Generate: step-by-step implementation plan
   Estimate: complexity (S/M/L/XL)
   Identify: risks, dependencies

4. POST PLAN TO JIRA (MANDATORY SKILL USAGE)
   ⚠️ REQUIRED: Use Skill tool with "jira-operations" skill
   DO NOT use bash scripts directly - use skill!
   Target: ticket comment with plan

5. NOTIFY VIA SLACK (MANDATORY IF CONFIGURED)
   ⚠️ REQUIRED: Use Skill tool with "slack-operations" skill
   Post: plan summary with approval buttons
```

## CRITICAL: Skill Usage Rules

**YOU MUST USE SKILLS, NOT RAW TOOLS:**

❌ **WRONG** - Using raw tools:
```
[TOOL] Using Grep
  pattern: "def process_issue"
```

✅ **CORRECT** - Using skills:
```
[TOOL] Using Skill
  skill: "discovery"
  args: "process_issue functionality"
```

**Why Skills Matter:**
- ✅ Built-in best practices and patterns
- ✅ Consistent behavior across agents
- ✅ Proper error handling and retries
- ✅ Centralized improvements benefit all agents

## Response Posting

**CRITICAL:** After analysis, ALWAYS post plan to Jira ticket using the Skill tool.

✅ **CORRECT WAY - Use Skill Tool:**

```
[TOOL] Using Skill
  skill: "jira-operations"
  args: "post_comment {issue_key} {plan_content}"
```

The skill will handle:
- Authentication
- API formatting
- Error handling
- Retry logic
- Logging

❌ **WRONG WAY - Don't call scripts directly:**

```bash
# DON'T DO THIS - bypasses skill system
.claude/skills/jira-operations/scripts/post_comment.sh "{issue_key}" "{plan_content}"
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

If SLACK_NOTIFICATION_CHANNEL is configured, use the Skill tool:

```
[TOOL] Using Skill
  skill: "slack-operations"
  args: "notify {issue_key} {plan_summary} {pr_url_if_exists}"
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
