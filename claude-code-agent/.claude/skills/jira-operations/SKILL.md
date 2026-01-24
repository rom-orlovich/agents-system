---
name: jira-operations
description: Jira CLI commands for issues, sprints, boards, and workflow operations
user-invocable: false
---

Jira operations using `jira` CLI.

## Environment
- `JIRA_API_TOKEN` - Jira API token
- `JIRA_BASE_URL` - Jira instance URL (e.g., https://yourcompany.atlassian.net)
- `JIRA_USER_EMAIL` - User email for authentication

## Common Commands

### Issues
```bash
jira issue list -q "project=PROJ AND sprint in openSprints()"
jira issue create -t Bug -s "Bug title" -b "Description" -a @me
jira issue edit PROJ-123 -s "Updated summary"
jira issue move PROJ-123 "In Review"
jira issue comment PROJ-123 "This is a comment"
jira issue assign PROJ-123 @me
```

### Sprints
```bash
jira sprint list --board 1 --state active,future
jira sprint create --name "Sprint 10" --start-date 2024-01-15 --duration 2w
jira issue move PROJ-123 --sprint 42
jira sprint report 42
```

### Board Operations
```bash
jira board list
jira board view 1
jira board view 1 --columns
```

### Search and Filtering
```bash
jira issue list -q "project=PROJ AND status='In Progress' AND assignee=currentUser()"
jira issue list -q "labels=urgent"
jira issue list -q "component='Backend'"
```

### Bulk Operations
```bash
jira issue list -q "project=PROJ AND status='To Do'" | xargs -I {} jira issue move {} "In Progress"
jira issue list -q "project=PROJ AND assignee is EMPTY" | xargs -I {} jira issue assign {} @me
```

## Common Workflows

### Bug Triage
```bash
jira issue list -q "project=PROJ AND type=Bug AND status='To Do'"
jira issue assign PROJ-123 @me
jira issue edit PROJ-123 --priority High
jira issue move PROJ-123 "In Progress"
```

### Sprint Planning
```bash
jira issue list -q "project=PROJ AND sprint is EMPTY ORDER BY priority DESC"
jira issue move PROJ-123 --sprint 42
```

### Release Management
```bash
jira issue list -q "project=PROJ AND fixVersion='1.2.0'"
jira issue move PROJ-123 "Done"
```

## Automation Scripts

### Post Analysis Results to Jira
```bash
# Post comment with analysis results
.claude/skills/jira-operations/scripts/post_comment.sh PROJ-123 "Analysis complete: Bug found in authentication module"

# Format markdown analysis to ADF (Atlassian Document Format)
FORMATTED=$(./claude/skills/jira-operations/scripts/format_analysis.sh "# Analysis Results
## Findings
- Issue in login.py line 45
- Memory leak detected")
echo $FORMATTED | jq .
```

### Automated Ticket Updates from CI/CD
```bash
# Example: Post build status to Jira ticket
BUILD_STATUS="✅ Build #123 succeeded. Tests: 150 passed, 0 failed."
.claude/skills/jira-operations/scripts/post_comment.sh $JIRA_TICKET "$BUILD_STATUS"
```

### Integration with GitHub
```bash
# Post PR analysis to related Jira ticket
ANALYSIS_RESULT=$(gh pr view 42 --json title,body | jq -r '.title + "\n\n" + .body')
.claude/skills/jira-operations/scripts/post_comment.sh PROJ-123 "$ANALYSIS_RESULT"
```
