---
name: slack-jira-inquiry
description: Query Jira tickets from Slack. Search, summarize, and report ticket status.
---

# Slack Jira Inquiry Workflow

> Query Jira from Slack → Search/Summarize → Respond

## Trigger
- Slack: `@agent jira PROJ-123`
- Slack: `/agent tickets [query]`
- Slack: `@agent my tickets`

## Flow

```
1. PARSE REQUEST
   Extract: ticket ID, search query, filters
   Classify: single / search / summary

2. JIRA QUERY
   Invoke: jira-operations skill
   Fetch: ticket details / search results

3. FORMAT RESPONSE
   Generate: Slack-friendly summary
   Include: status, assignee, priority

4. RESPOND
   Invoke: slack-operations skill
   Post: formatted response
```

## Request Types

### Single Ticket
```
Input: @agent jira PROJ-123
Output:
🎫 *PROJ-123: {summary}*
Status: {status} | Priority: {priority}
Assignee: {assignee}
Updated: {date}

{description_preview}

🔗 [View in Jira]({url})
```

### Search
```
Input: @agent tickets assigned to me
Output:
📋 *Your Tickets (5)*

1. PROJ-123: Fix login bug [In Progress]
2. PROJ-124: Add OAuth [To Do]
...
```

### Summary
```
Input: @agent sprint summary
Output:
📊 *Sprint Summary*
✅ Done: 12
🔄 In Progress: 5
📋 To Do: 8

Top priorities:
1. PROJ-123 (P1)
2. PROJ-125 (P2)
```

## No Approval Required
Read-only Jira queries.
