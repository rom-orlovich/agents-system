# Unified Webhook System - Complete Guide

## ✅ Problem Solved

**Before:** Two separate webhook systems that didn't align
- Static webhooks (`/webhooks/github`) - Full GitHub API integration but not configurable
- Dynamic webhooks (`/webhooks/{provider}/{webhook_id}`) - Configurable but limited functionality

**After:** Unified system where **user-created webhooks have the same power as static webhooks**
- ✅ Full GitHub API integration (comments, reactions, labels)
- ✅ Configurable via dashboard/API
- ✅ Pre-built templates for common use cases
- ✅ Support for GitHub, Jira, Slack, and custom providers

---

## 🎯 Key Features

### **1. Enhanced Actions**

User-created webhooks now support **7 action types**:

| Action | Description | Example Use Case |
|--------|-------------|------------------|
| `create_task` | Create agent task | Auto-analyze new issues |
| `comment` | Post comment to source | Acknowledge issue creation |
| `ask` | Interactive question | Request clarification |
| `respond` | Immediate response | Quick acknowledgment |
| `forward` | Forward to another service | Send to Slack |
| **`github_reaction`** | Add GitHub reaction | Add 👀 to comments |
| **`github_label`** | Add GitHub labels | Tag with "bot-processing" |

### **2. GitHub API Integration**

Dynamic webhooks can now:
- ✅ Post comments to issues and PRs
- ✅ Add reactions (👀, 👍, ❤️, 🚀, etc.)
- ✅ Update issue labels
- ✅ Extract repo info automatically
- ✅ Handle issue/PR numbers

### **3. Pre-built Templates**

Six ready-to-use templates:
1. **GitHub Issue Tracking** - Auto-triage and respond to issues
2. **GitHub PR Review** - Automated PR reviews
3. **GitHub Mention Bot** - Respond to @agent mentions
4. **GitHub Bug Triage** - Special handling for bug reports
5. **Jira Issue Sync** - Sync Jira with agent tasks
6. **Slack Notifications** - Respond to Slack mentions

---

## 🚀 How to Use

### **Option 1: Create from Template (Easiest)**

**Via API:**
```bash
curl -X POST http://localhost:8000/api/webhooks/from-template/github_issue_tracking \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Issue Tracker",
    "secret": "your_webhook_secret"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "webhook_id": "webhook-abc123",
    "endpoint": "/webhooks/github/webhook-abc123",
    "name": "My Issue Tracker",
    "provider": "github",
    "template_id": "github_issue_tracking",
    "commands_count": 4
  }
}
```

**Via Dashboard:**
1. Click "➕ Create Webhook" in side menu
2. Select "Use Template"
3. Choose template (e.g., "GitHub Issue Tracking")
4. Customize name and secret
5. Click "Create"

### **Option 2: Create Custom Webhook**

**Full Example - GitHub Issue Tracker:**
```bash
curl -X POST http://localhost:8000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Issue Tracker",
    "provider": "github",
    "secret": "your_secret",
    "commands": [
      {
        "trigger": "issues.opened",
        "action": "github_reaction",
        "template": "eyes",
        "priority": 0
      },
      {
        "trigger": "issues.opened",
        "action": "github_label",
        "template": "bot-processing, needs-triage",
        "priority": 1
      },
      {
        "trigger": "issues.opened",
        "action": "create_task",
        "agent": "planning",
        "template": "Analyze: {{issue.title}}\n\n{{issue.body}}",
        "priority": 2
      },
      {
        "trigger": "issues.opened",
        "action": "comment",
        "template": "🤖 I'\''ve created a task to analyze this issue!",
        "priority": 3
      }
    ]
  }'
```

### **Option 3: Use Dashboard UI**

1. Open http://localhost:8000
2. Click "➕ Create Webhook" in side menu
3. Fill in webhook details:
   - Name: "My GitHub Bot"
   - Provider: GitHub
   - Secret: your_webhook_secret
4. Add commands:
   - **Command 1:**
     - Trigger: `issues.opened`
     - Action: `github_reaction`
     - Template: `eyes`
   - **Command 2:**
     - Trigger: `issues.opened`
     - Action: `comment`
     - Template: `🤖 I'm on it!`
5. Click "Create Webhook"

---

## 📋 Available Templates

### **1. GitHub Issue Tracking**
```
Template ID: github_issue_tracking
Provider: GitHub
Commands: 4
```

**What it does:**
1. Adds 👀 reaction to new issues
2. Labels with "bot-processing, needs-triage"
3. Creates planning task to analyze issue
4. Posts acknowledgment comment

**Use case:** Automatically triage and respond to all new issues

### **2. GitHub PR Review**
```
Template ID: github_pr_review
Provider: GitHub
Commands: 3
```

**What it does:**
1. Adds 👀 reaction to new PRs
2. Creates executor task to review PR
3. Posts review acknowledgment comment

**Use case:** Automated code review for all pull requests

### **3. GitHub Mention Bot**
```
Template ID: github_mention_bot
Provider: GitHub
Commands: 3
```

**What it does:**
1. Detects @agent mentions in comments
2. Adds 👀 reaction to mention
3. Creates task to handle request
4. Posts acknowledgment

**Use case:** On-demand assistance via @mentions

### **4. GitHub Bug Triage**
```
Template ID: github_bug_triage
Provider: GitHub
Commands: 4
```

**What it does:**
1. Detects when "bug" label is added
2. Adds 👍 reaction
3. Labels with "needs-investigation, priority-high"
4. Creates high-priority investigation task
5. Posts bug acknowledgment

**Use case:** Special handling for bug reports

### **5. Jira Issue Sync**
```
Template ID: jira_issue_sync
Provider: Jira
Commands: 1
```

**What it does:**
1. Creates planning task for new Jira issues

**Use case:** Sync Jira issues with agent system

### **6. Slack Notifications**
```
Template ID: slack_notifications
Provider: Slack
Commands: 2
```

**What it does:**
1. Detects @agent mentions in Slack
2. Creates brain task
3. Sends quick acknowledgment

**Use case:** Slack-based agent interaction

---

## 🎨 Action Reference

### **create_task**
Creates an agent task in the queue.

**Template variables:**
```
{{issue.title}}
{{issue.body}}
{{issue.number}}
{{pull_request.title}}
{{comment.body}}
```

**Example:**
```json
{
  "action": "create_task",
  "agent": "planning",
  "template": "Analyze issue: {{issue.title}}\n\n{{issue.body}}"
}
```

### **comment**
Posts a comment to GitHub issue/PR, Jira issue, or Slack channel.

**Template variables:** Same as create_task

**Example:**
```json
{
  "action": "comment",
  "template": "🤖 I've created task to analyze this!"
}
```

### **github_reaction**
Adds a reaction to GitHub comment/issue/PR.

**Valid reactions:** `eyes`, `+1`, `-1`, `laugh`, `confused`, `heart`, `hooray`, `rocket`

**Template:** Reaction name

**Example:**
```json
{
  "action": "github_reaction",
  "template": "eyes"
}
```

### **github_label**
Adds labels to GitHub issue/PR.

**Template:** Comma-separated label names

**Example:**
```json
{
  "action": "github_label",
  "template": "bot-processing, needs-triage, high-priority"
}
```

### **ask**
Creates an interactive task that requires user response.

**Example:**
```json
{
  "action": "ask",
  "agent": "brain",
  "template": "Should I proceed with {{issue.title}}?"
}
```

### **respond**
Sends immediate response (logged but not posted).

**Example:**
```json
{
  "action": "respond",
  "template": "Acknowledged: {{event.type}}"
}
```

### **forward**
Forwards event to another service.

**Example:**
```json
{
  "action": "forward",
  "template": "Forward to monitoring system"
}
```

---

## 🔄 Complete Workflow Example

**Scenario:** Comprehensive GitHub issue handling

**Webhook Configuration:**
```json
{
  "name": "Complete GitHub Handler",
  "provider": "github",
  "secret": "my_secret",
  "commands": [
    {
      "trigger": "issues.opened",
      "action": "github_reaction",
      "template": "eyes",
      "priority": 0
    },
    {
      "trigger": "issues.opened",
      "action": "github_label",
      "template": "bot-processing",
      "priority": 1
    },
    {
      "trigger": "issues.opened",
      "action": "create_task",
      "agent": "planning",
      "template": "Analyze: {{issue.title}}\n\n{{issue.body}}",
      "priority": 2
    },
    {
      "trigger": "issues.opened",
      "action": "comment",
      "template": "🤖 **Automated Analysis Started**\n\nTask created. I'll review and respond shortly!",
      "priority": 3
    },
    {
      "trigger": "issue_comment.created",
      "action": "github_reaction",
      "template": "eyes",
      "conditions": {"body": "@agent"},
      "priority": 0
    },
    {
      "trigger": "issue_comment.created",
      "action": "create_task",
      "agent": "planning",
      "template": "Issue #{{issue.number}}: {{comment.body}}",
      "conditions": {"body": "@agent"},
      "priority": 1
    },
    {
      "trigger": "issue_comment.created",
      "action": "comment",
      "template": "👋 Got it! I'll look into that.",
      "conditions": {"body": "@agent"},
      "priority": 2
    }
  ]
}
```

**What happens:**

1. **User creates issue** → Bot adds 👀, labels it, creates task, posts comment
2. **User mentions @agent** → Bot adds 👀, creates task, responds
3. **All actions execute in priority order**
4. **Tasks queued for agent processing**
5. **Full GitHub integration works seamlessly**

---

## 🆚 Comparison: Static vs Dynamic Webhooks

| Feature | Static (`/webhooks/github`) | Dynamic (`/webhooks/{provider}/{id}`) |
|---------|----------------------------|--------------------------------------|
| **GitHub API** | ✅ Full integration | ✅ **Now full integration!** |
| **Configurable** | ❌ Hardcoded | ✅ Via API/Dashboard |
| **Templates** | ❌ No | ✅ 6 pre-built templates |
| **Custom commands** | ❌ No | ✅ Unlimited |
| **Reactions** | ✅ Yes | ✅ **Now yes!** |
| **Labels** | ✅ Yes | ✅ **Now yes!** |
| **Comments** | ✅ Yes | ✅ **Now yes!** |
| **Multi-provider** | ❌ GitHub only | ✅ GitHub, Jira, Slack, Custom |
| **Dashboard UI** | ❌ No | ✅ Yes |
| **Template rendering** | ❌ No | ✅ Yes |
| **Conditions** | ❌ Hardcoded | ✅ Configurable |

**Recommendation:** Use **dynamic webhooks** for all new integrations. They have all the power of static webhooks plus configurability!

---

## 📊 API Endpoints

### **List Templates**
```bash
GET /api/templates
GET /api/templates?provider=github
```

### **Create from Template**
```bash
POST /api/webhooks/from-template/{template_id}
Body: {"name": "My Webhook", "secret": "optional"}
```

### **Create Custom Webhook**
```bash
POST /api/webhooks
Body: {webhook configuration}
```

### **List Webhooks**
```bash
GET /api/webhooks
```

### **Get Webhook**
```bash
GET /api/webhooks/{webhook_id}
```

### **Update Webhook**
```bash
PUT /api/webhooks/{webhook_id}
```

### **Delete Webhook**
```bash
DELETE /api/webhooks/{webhook_id}
```

### **Enable/Disable**
```bash
POST /api/webhooks/{webhook_id}/enable
POST /api/webhooks/{webhook_id}/disable
```

---

## ✅ Summary

**Yes, the systems are now fully aligned!**

✅ **User-created webhooks = Same power as static webhooks**
✅ **Full GitHub API integration in dynamic system**
✅ **Pre-built templates for instant setup**
✅ **Configurable via dashboard and API**
✅ **Support for all providers (GitHub, Jira, Slack)**

**You can now create fully functional webhooks like the static ones, but with:**
- More flexibility
- Template support
- Dashboard UI
- Custom configurations
- Multiple providers

The unified system gives you the best of both worlds!
