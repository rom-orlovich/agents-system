# Dynamic Webhook Registration System

## Overview

A comprehensive webhook management system that allows:
- **Dynamic webhook registration** via dashboard/API
- **Custom command mapping** per webhook
- **Brain agent autonomous webhook creation**
- **Interactive webhook responses** (comment, ask, respond)
- **Full persistence** (database + cloud-ready)

---

## Architecture

### **1. Webhook Configuration Model**

```python
class WebhookConfig(BaseModel):
    webhook_id: str              # Unique ID
    name: str                    # Human-readable name
    provider: str                # github, jira, slack, sentry, custom
    endpoint: str                # /webhooks/{provider}/{webhook_id}
    secret: Optional[str]        # HMAC secret for verification
    enabled: bool                # Active/inactive
    commands: List[WebhookCommand]  # Command mappings
    created_at: datetime
    created_by: str              # user or "brain-agent"
```

### **2. Webhook Command Model**

```python
class WebhookCommand(BaseModel):
    trigger: str                 # Event type or pattern
    action: str                  # create_task, comment, ask, respond
    agent: str                   # Which agent to assign
    template: str                # Message template
    conditions: Dict             # Filtering conditions
```

### **3. Webhook Action Types**

- **create_task** - Create a new task for an agent
- **comment** - Post a comment back to the source
- **ask** - Ask for clarification (interactive)
- **respond** - Send a response immediately
- **forward** - Forward to another webhook/service

---

## Database Schema

```sql
-- Webhook configurations
CREATE TABLE webhook_configs (
    webhook_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    secret TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    config_json TEXT,  -- Full JSON config
    created_at TIMESTAMP,
    created_by TEXT,
    updated_at TIMESTAMP
);

-- Webhook commands (one-to-many)
CREATE TABLE webhook_commands (
    command_id TEXT PRIMARY KEY,
    webhook_id TEXT REFERENCES webhook_configs(webhook_id),
    trigger TEXT NOT NULL,
    action TEXT NOT NULL,
    agent TEXT,
    template TEXT,
    conditions_json TEXT,
    priority INTEGER DEFAULT 0
);

-- Webhook events log
CREATE TABLE webhook_events (
    event_id TEXT PRIMARY KEY,
    webhook_id TEXT REFERENCES webhook_configs(webhook_id),
    provider TEXT,
    event_type TEXT,
    payload_json TEXT,
    matched_command TEXT,
    task_id TEXT,
    response_sent BOOLEAN,
    created_at TIMESTAMP
);
```

---

## API Endpoints

### **Webhook Management**

```
GET    /api/webhooks                 - List all webhooks
POST   /api/webhooks                 - Create new webhook
GET    /api/webhooks/{id}            - Get webhook details
PUT    /api/webhooks/{id}            - Update webhook
DELETE /api/webhooks/{id}            - Delete webhook
POST   /api/webhooks/{id}/enable     - Enable webhook
POST   /api/webhooks/{id}/disable    - Disable webhook
```

### **Command Management**

```
GET    /api/webhooks/{id}/commands          - List commands
POST   /api/webhooks/{id}/commands          - Add command
PUT    /api/webhooks/{id}/commands/{cmd_id} - Update command
DELETE /api/webhooks/{id}/commands/{cmd_id} - Delete command
```

### **Webhook Receivers**

```
POST   /webhooks/{provider}/{webhook_id}    - Dynamic webhook endpoint
```

### **Interactive Actions**

```
POST   /api/webhooks/{id}/comment   - Post comment to source
POST   /api/webhooks/{id}/ask       - Ask for clarification
POST   /api/webhooks/{id}/respond   - Send response
```

---

## Example Configurations

### **Example 1: GitHub Issue Tracker**

```json
{
  "webhook_id": "github-issues-001",
  "name": "GitHub Issue Tracker",
  "provider": "github",
  "endpoint": "/webhooks/github/github-issues-001",
  "secret": "your-webhook-secret",
  "enabled": true,
  "commands": [
    {
      "trigger": "issues.opened",
      "action": "create_task",
      "agent": "planning",
      "template": "Analyze issue: {{issue.title}}\n\n{{issue.body}}",
      "conditions": {
        "labels": ["bug", "enhancement"]
      }
    },
    {
      "trigger": "issue_comment.created",
      "action": "ask",
      "agent": "brain",
      "template": "User asked: {{comment.body}}",
      "conditions": {
        "body_contains": "@agent"
      }
    }
  ]
}
```

### **Example 2: Jira Automation**

```json
{
  "webhook_id": "jira-automation-001",
  "name": "Jira Sprint Automation",
  "provider": "jira",
  "endpoint": "/webhooks/jira/jira-automation-001",
  "enabled": true,
  "commands": [
    {
      "trigger": "jira:issue_created",
      "action": "create_task",
      "agent": "planning",
      "template": "New Jira ticket: {{issue.key}} - {{issue.summary}}"
    },
    {
      "trigger": "jira:issue_updated",
      "action": "comment",
      "agent": "brain",
      "template": "Acknowledged update to {{issue.key}}"
    }
  ]
}
```

### **Example 3: Custom Slack Integration**

```json
{
  "webhook_id": "slack-alerts-001",
  "name": "Slack Alert Handler",
  "provider": "slack",
  "endpoint": "/webhooks/slack/slack-alerts-001",
  "enabled": true,
  "commands": [
    {
      "trigger": "message.channels",
      "action": "respond",
      "agent": "brain",
      "template": "Processing your request: {{text}}",
      "conditions": {
        "channel": "#engineering"
      }
    }
  ]
}
```

---

## Brain Agent Capabilities

The Brain can autonomously create webhooks by:

1. **Creating webhook config files** in `/data/config/webhooks/`
2. **Using the API** to register webhooks
3. **Writing command mappings** based on requirements

### **Example: Brain Creates Webhook**

User asks:
```
Create a webhook for GitHub that automatically creates planning tasks 
when issues are labeled "urgent"
```

Brain executes:
```python
# Brain uses Write tool to create:
/data/config/webhooks/github-urgent-issues.json

{
  "name": "GitHub Urgent Issues",
  "provider": "github",
  "commands": [
    {
      "trigger": "issues.labeled",
      "action": "create_task",
      "agent": "planning",
      "conditions": {"label": "urgent"}
    }
  ]
}
```

Then calls API:
```bash
POST /api/webhooks
```

---

## Interactive Webhook Actions

### **1. Comment Back to Source**

```python
# When webhook receives event, agent can comment back
POST /api/webhooks/{webhook_id}/comment
{
  "event_id": "evt-123",
  "message": "I've created task-456 to handle this"
}
```

### **2. Ask for Clarification**

```python
# Agent asks user for more info
POST /api/webhooks/{webhook_id}/ask
{
  "event_id": "evt-123",
  "question": "Should I prioritize this over task-789?"
}
```

### **3. Send Response**

```python
# Immediate response to webhook source
POST /api/webhooks/{webhook_id}/respond
{
  "event_id": "evt-123",
  "response": "Task completed successfully"
}
```

---

## Persistence Strategy

### **Local (Development)**
- SQLite database: `/data/db/webhooks.db`
- Config files: `/data/config/webhooks/*.json`

### **Cloud (Production)**
- PostgreSQL for webhook configs
- S3/GCS for config backups
- Redis for event queue
- CloudWatch/Stackdriver for logs

---

## Dashboard UI

### **Webhooks Tab**

```
📡 Webhooks
├── List of registered webhooks
├── + Create Webhook button
├── Enable/Disable toggles
├── Edit/Delete actions
└── Test webhook button
```

### **Webhook Detail View**

```
Webhook: GitHub Issue Tracker
├── Status: ✅ Enabled
├── Endpoint: /webhooks/github/github-issues-001
├── Secret: ••••••••
├── Commands (3)
│   ├── issues.opened → create_task (planning)
│   ├── issue_comment → ask (brain)
│   └── pull_request → create_task (executor)
├── Recent Events (10)
└── [Edit] [Test] [Delete]
```

---

## Security

1. **HMAC Signature Verification** - All webhooks verify signatures
2. **Secret Rotation** - Support for rotating webhook secrets
3. **Rate Limiting** - Prevent webhook abuse
4. **IP Whitelisting** - Optional IP restrictions
5. **Audit Logging** - All webhook events logged

---

## Cloud Deployment

### **Environment Variables**

```bash
# Webhook Configuration
WEBHOOK_BASE_URL=https://your-domain.com
WEBHOOK_SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://host:6379

# Storage
STORAGE_BACKEND=s3
S3_BUCKET=your-webhook-configs
```

### **Kubernetes Deployment**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: webhook-service
spec:
  type: LoadBalancer
  ports:
    - port: 443
      targetPort: 8000
  selector:
    app: claude-agent
```

---

## Implementation Phases

### **Phase 1: Core Infrastructure** ✅
- Database models
- CRUD API endpoints
- Basic webhook receiver

### **Phase 2: Command System** 🔄
- Command mapping engine
- Action handlers (create_task, comment, ask, respond)
- Template rendering

### **Phase 3: Dashboard UI** 📋
- Webhook management interface
- Command builder
- Event log viewer

### **Phase 4: Brain Integration** 🧠
- Brain can create webhooks
- Brain can modify commands
- Brain can respond to events

### **Phase 5: Cloud Ready** ☁️
- PostgreSQL migration
- S3 config storage
- Load balancer setup
- Monitoring & alerts

---

## Next Steps

1. Implement database models
2. Create webhook CRUD API
3. Build command execution engine
4. Add dashboard UI
5. Enable Brain webhook creation
6. Deploy to cloud
