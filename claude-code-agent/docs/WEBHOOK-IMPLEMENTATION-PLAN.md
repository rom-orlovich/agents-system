# Webhook Registration System - Implementation Plan

## ✅ Current Status

**Existing webhook support:**
- ✅ Basic GitHub webhook handler (`/webhooks/github`)
- ✅ HMAC signature verification
- ✅ Hardcoded event handlers (issues, PR, comments)
- ✅ Task creation from webhooks

**What's missing:**
- ❌ Dynamic webhook registration
- ❌ Custom command mapping
- ❌ Interactive actions (comment, ask, respond)
- ❌ Webhook management UI
- ❌ Brain autonomous webhook creation
- ❌ Persistent webhook configurations

---

## 🎯 Implementation Phases

### **Phase 1: Database & Models** (30 min)
Create database models for:
- `WebhookConfigDB` - Webhook configurations
- `WebhookCommandDB` - Command mappings
- `WebhookEventDB` - Event logs

### **Phase 2: Core API** (45 min)
Implement CRUD endpoints:
- `GET /api/webhooks` - List webhooks
- `POST /api/webhooks` - Create webhook
- `PUT /api/webhooks/{id}` - Update webhook
- `DELETE /api/webhooks/{id}` - Delete webhook
- `POST /api/webhooks/{id}/commands` - Add command

### **Phase 3: Dynamic Receiver** (30 min)
Build dynamic webhook receiver:
- Route `/webhooks/{provider}/{webhook_id}`
- Load webhook config from database
- Match event to commands
- Execute actions

### **Phase 4: Action Handlers** (45 min)
Implement action types:
- `create_task` - Create agent task
- `comment` - Post comment to source
- `ask` - Interactive question
- `respond` - Immediate response

### **Phase 5: Dashboard UI** (60 min)
Add webhook management to dashboard:
- Webhooks tab in navigation
- List/create/edit webhooks
- Command builder interface
- Event log viewer

### **Phase 6: Brain Integration** (30 min)
Enable Brain to:
- Create webhook configs via API
- Write webhook files to `/data/config/webhooks/`
- Modify existing webhooks

### **Phase 7: Testing & Documentation** (30 min)
- Integration tests
- API documentation
- User guide
- Cloud deployment guide

**Total estimated time: ~4 hours**

---

## 📋 Detailed Implementation

### **1. Database Models**

```python
# core/database/models.py

class WebhookConfigDB(Base):
    __tablename__ = "webhook_configs"
    
    webhook_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)  # github, jira, slack, custom
    endpoint = Column(String(500), nullable=False)
    secret = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True)
    config_json = Column(Text, nullable=False)  # Full JSON config
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    commands = relationship("WebhookCommandDB", back_populates="webhook")
    events = relationship("WebhookEventDB", back_populates="webhook")

class WebhookCommandDB(Base):
    __tablename__ = "webhook_commands"
    
    command_id = Column(String(255), primary_key=True)
    webhook_id = Column(String(255), ForeignKey("webhook_configs.webhook_id"))
    trigger = Column(String(255), nullable=False)  # Event pattern
    action = Column(String(50), nullable=False)    # create_task, comment, ask, respond
    agent = Column(String(255), nullable=True)
    template = Column(Text, nullable=False)
    conditions_json = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    
    webhook = relationship("WebhookConfigDB", back_populates="commands")

class WebhookEventDB(Base):
    __tablename__ = "webhook_events"
    
    event_id = Column(String(255), primary_key=True)
    webhook_id = Column(String(255), ForeignKey("webhook_configs.webhook_id"))
    provider = Column(String(50), nullable=False)
    event_type = Column(String(255), nullable=False)
    payload_json = Column(Text, nullable=False)
    matched_command = Column(String(255), nullable=True)
    task_id = Column(String(255), nullable=True)
    response_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    webhook = relationship("WebhookConfigDB", back_populates="events")
```

### **2. API Endpoints**

```python
# api/webhooks_management.py

@router.get("/webhooks")
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    """List all registered webhooks."""
    
@router.post("/webhooks")
async def create_webhook(webhook: WebhookCreate, db: AsyncSession = Depends(get_db)):
    """Create a new webhook configuration."""
    
@router.get("/webhooks/{webhook_id}")
async def get_webhook(webhook_id: str, db: AsyncSession = Depends(get_db)):
    """Get webhook details."""
    
@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, webhook: WebhookUpdate, db: AsyncSession = Depends(get_db)):
    """Update webhook configuration."""
    
@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, db: AsyncSession = Depends(get_db)):
    """Delete webhook."""
    
@router.post("/webhooks/{webhook_id}/commands")
async def add_command(webhook_id: str, command: CommandCreate, db: AsyncSession = Depends(get_db)):
    """Add command to webhook."""
```

### **3. Dynamic Webhook Receiver**

```python
# api/webhooks_dynamic.py

@router.post("/webhooks/{provider}/{webhook_id}")
async def dynamic_webhook_receiver(
    provider: str,
    webhook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Dynamic webhook receiver that routes to registered webhooks."""
    
    # 1. Load webhook config from database
    webhook = await get_webhook_config(webhook_id, db)
    
    # 2. Verify signature if secret configured
    if webhook.secret:
        await verify_webhook_signature(request, webhook.secret, provider)
    
    # 3. Parse payload
    payload = await request.json()
    event_type = extract_event_type(request, provider)
    
    # 4. Match event to commands
    matched_commands = match_commands(webhook.commands, event_type, payload)
    
    # 5. Execute actions
    results = []
    for command in matched_commands:
        result = await execute_command(command, payload, db)
        results.append(result)
    
    # 6. Log event
    await log_webhook_event(webhook_id, provider, event_type, payload, results, db)
    
    return {"status": "processed", "actions": len(results)}
```

### **4. Command Execution Engine**

```python
# core/webhook_engine.py

async def execute_command(command: WebhookCommandDB, payload: dict, db: AsyncSession):
    """Execute a webhook command."""
    
    # Render template with payload data
    message = render_template(command.template, payload)
    
    # Execute action
    if command.action == "create_task":
        return await action_create_task(command.agent, message, payload, db)
    
    elif command.action == "comment":
        return await action_comment(payload, message)
    
    elif command.action == "ask":
        return await action_ask(command.agent, message, payload, db)
    
    elif command.action == "respond":
        return await action_respond(payload, message)
    
    else:
        raise ValueError(f"Unknown action: {command.action}")

async def action_create_task(agent: str, message: str, payload: dict, db: AsyncSession):
    """Create a task for an agent."""
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    # Create task in database
    # Push to queue
    return {"action": "create_task", "task_id": task_id}

async def action_comment(payload: dict, message: str):
    """Post a comment back to the source."""
    provider = payload.get("provider")
    if provider == "github":
        await github_post_comment(payload, message)
    elif provider == "jira":
        await jira_post_comment(payload, message)
    return {"action": "comment", "status": "sent"}

async def action_ask(agent: str, message: str, payload: dict, db: AsyncSession):
    """Ask for clarification (creates interactive task)."""
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    # Create task with interactive flag
    return {"action": "ask", "task_id": task_id}

async def action_respond(payload: dict, message: str):
    """Send immediate response."""
    # Send response to webhook source
    return {"action": "respond", "status": "sent"}
```

### **5. Dashboard UI**

```html
<!-- Webhooks Tab -->
<div id="tab-webhooks" class="tab-content">
    <section class="panel webhooks-panel">
        <div class="panel-header">
            <h2>Registered Webhooks</h2>
            <button onclick="app.showWebhookCreate()">+ Create Webhook</button>
        </div>
        <div id="webhooks-list" class="webhooks-list">
            <!-- Webhook cards -->
        </div>
    </section>
</div>

<!-- Webhook Create Modal -->
<div id="webhook-create-modal" class="modal hidden">
    <form id="webhook-create-form">
        <input type="text" id="webhook-name" placeholder="Webhook Name">
        <select id="webhook-provider">
            <option value="github">GitHub</option>
            <option value="jira">Jira</option>
            <option value="slack">Slack</option>
            <option value="custom">Custom</option>
        </select>
        <input type="password" id="webhook-secret" placeholder="Secret (optional)">
        <button type="submit">Create Webhook</button>
    </form>
</div>
```

### **6. Brain Integration**

The Brain can create webhooks by:

**Method 1: Using the API**
```python
# Brain calls API endpoint
POST /api/webhooks
{
  "name": "GitHub Urgent Issues",
  "provider": "github",
  "commands": [...]
}
```

**Method 2: Writing config files**
```python
# Brain uses Write tool
/data/config/webhooks/github-urgent-issues.json
```

Then the system auto-loads configs on startup.

---

## 🗂️ File Structure

```
claude-code-agent/
├── api/
│   ├── webhooks.py              # Existing basic handlers
│   ├── webhooks_management.py   # NEW: CRUD API
│   └── webhooks_dynamic.py      # NEW: Dynamic receiver
├── core/
│   ├── database/
│   │   └── models.py            # ADD: Webhook models
│   └── webhook_engine.py        # NEW: Command execution
├── services/dashboard/static/
│   ├── index.html               # ADD: Webhooks tab
│   └── js/app.js                # ADD: Webhook management
├── data/
│   └── config/
│       └── webhooks/            ## 📚 **Documentation Created:**

1. **`docs/WEBHOOK-SYSTEM-DESIGN.md`** - Complete architecture with Brain management
2. **`docs/WEBHOOK-IMPLEMENTATION-PLAN.md`** - Step-by-step implementation guide
3. **`docs/WEBHOOK-CONFIGURATION-UI.md`** - Dashboard UI for editing commands, triggers, bot tags
4. **`docs/ORCHESTRATION-AGENT-ARCHITECTURE.md`** - Brain delegation pattern with subagents
5. **`docs/TDD-APPROACH.md`** - Test-driven development methodology

---

## 🎯 **Key Features Documented**

### **Fully Configurable via Dashboard:**
- ✅ Edit webhook commands (triggers, actions, templates)
- ✅ Configure bot mention tags (@agent, @ai-assistant, etc.)
- ✅ Set trigger patterns (mention, assignee, labels, status)
- ✅ Customize response templates
- ✅ Test webhooks before deployment
- ✅ Provider-specific settings (GitHub, Jira, Slack)

### **Orchestration Agent Pattern:**
- ✅ Brain delegates all operations to orchestration agent
- ✅ Specialized skills for each operation type
- ✅ Parallel execution support
- ✅ Clean separation of concerns
- ✅ Fully testable and maintainable

---
### **1. Create Webhook via Dashboard**
1. Open http://localhost:8000
2. Click **Webhooks** tab
3. Click **+ Create Webhook**
4. Fill in details and commands
5. Get endpoint URL

### **2. Create Webhook via API**
```bash
curl -X POST http://localhost:8000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Webhook",
    "provider": "github",
    "commands": [
      {
        "trigger": "issues.opened",
        "action": "create_task",
        "agent": "planning",
        "template": "New issue: {{issue.title}}"
      }
    ]
  }'
```

### **3. Brain Creates Webhook**
```
Ask Brain: "Create a webhook for GitHub that creates planning tasks when issues are opened"

Brain will:
1. Call POST /api/webhooks
2. Configure commands
3. Return webhook endpoint
```

---

## 📊 Next Steps

1. ✅ Design complete
2. 🔄 Implement database models
3. 🔄 Build CRUD API
4. 🔄 Create dynamic receiver
5. 🔄 Add action handlers
6. 🔄 Build dashboard UI
7. 🔄 Test end-to-end
8. 🔄 Deploy to cloud

**Ready to start implementation!**
