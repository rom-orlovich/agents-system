# Human Approval Response Templates

Templates for approval workflow communications.

## Approval Request Template

### Draft PR Created

```markdown
## 📋 Approval Request

**Draft PR:** #{pr_number}
**Ticket:** {ticket_id}

### Summary

{summary}

### Planned Changes

{planned_changes_list}

### Files to Modify

{files_list}

### Risk Assessment

{risk_assessment}

### Estimated Impact

{estimated_impact}

### Approval Required

Please review and approve before implementation.

**To approve:**

- Comment `@agent approve` or `LGTM` on PR
- Click Approve button in Slack
- Transition Jira to "Approved"

---

_Automated by Claude Agent_
```

## Approval Status Template

### Waiting for Approval

```markdown
## ⏳ Waiting for Approval

**Status:** Awaiting human approval

**Draft PR:** {pr_url}
**Slack Notification:** Sent to {channel}
**Jira Ticket:** {ticket_key}

### Timeout

- **4 hours:** Reminder notification
- **24 hours:** Escalate to team lead
- **72 hours:** Auto-close with "stale" label

**To approve:**

- Comment `@agent approve` on PR
- Click Approve button in Slack
- Transition Jira to "Approved"
```

### Approval Received

```markdown
## ✅ Approval Received

**Status:** Approved

**Approved By:** {approver}
**Method:** {approval_method}
**Time:** {approval_time}

### Next Steps

Proceeding with implementation.

---

_Automated by Claude Agent_
```

### Rejection Received

```markdown
## ❌ Rejection Received

**Status:** Rejected

**Rejected By:** {rejector}
**Reason:** {rejection_reason}

### Next Steps

Re-delegating to planning agent for revision.

---

_Automated by Claude Agent_
```

## Reminder Template

### Approval Reminder

```markdown
## ⏰ Approval Reminder

**Draft PR:** #{pr_number}
**Waiting Since:** {waiting_duration}

### Request Summary

{summary}

### Action Required

Please review and approve/reject the draft PR.

**To approve:**

- Comment `@agent approve` on PR
- Click Approve button in Slack

**To reject:**

- Comment `@agent reject` on PR
- Click Reject button in Slack
```

## Escalation Template

### Escalation Notice

```markdown
## 🚨 Escalation Notice

**Draft PR:** #{pr_number}
**Waiting Since:** {waiting_duration}

### Status

Approval request has been pending for 24+ hours.

### Escalation

Escalating to team lead for review.

### Original Request

{original_request_summary}
```

## Best Practices

1. **Include all approval methods** - PR, Slack, Jira
2. **Show timeout information** - When reminders/escalation occur
3. **Provide clear instructions** - How to approve/reject
4. **Include context** - PR number, ticket ID, summary
5. **Track approval source** - Who approved and how
6. **Handle timeouts** - Reminders and escalation
7. **Maintain audit trail** - Log all approval events
