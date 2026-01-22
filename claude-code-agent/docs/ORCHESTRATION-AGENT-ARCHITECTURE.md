# Orchestration Agent Architecture

## Overview

The **Brain agent** delegates all background operations to specialized subagents through an **Orchestration Agent**. This creates a clean separation of concerns and enables parallel task execution.

---

## Architecture Pattern

```
User Request
     ↓
Brain Agent (CLAUDE.md)
     ↓
Orchestration Agent (.claude/CLAUDE.md + orchestration skill)
     ↓
├─→ Webhook Management Subagent
├─→ Skill Management Subagent  
├─→ Agent Management Subagent
├─→ Database Operations Subagent
├─→ API Integration Subagent
└─→ Monitoring Subagent
```

---

## Brain Agent Structure

### **File: `.claude/CLAUDE.md`**

```markdown
# Brain Agent

You are the Brain - the central intelligence coordinating all operations.

## Your Role

You **analyze** user requests and **delegate** to specialized subagents.
You **never** perform operations directly - you orchestrate.

## Available Subagents

- **orchestration** - Coordinates all background operations
- **planning** - Creates detailed fix plans
- **executor** - Implements code changes

## Decision Flow

1. **Understand** user request
2. **Determine** which subagent(s) needed
3. **Delegate** to orchestration agent
4. **Monitor** progress
5. **Report** results to user

## Examples

User: "Create a webhook for GitHub"
→ Delegate to: orchestration (webhook-management)

User: "Upload a new skill"
→ Delegate to: orchestration (skill-management)

User: "Show me all webhook events"
→ Delegate to: orchestration (monitoring)

## Skills Available

- `orchestration` - Background operations management
- `webhook-management` - Webhook CRUD operations
- `skill-management` - Skill upload/delete
- `agent-management` - Agent configuration
```

---

## Orchestration Agent

### **Directory Structure**

```
agents/orchestration/
├── .claude/
│   └── CLAUDE.md           # Agent instructions
└── skills/
    ├── webhook-management/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── create_webhook.py
    │       ├── edit_command.py
    │       └── test_webhook.py
    ├── skill-management/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── upload_skill.py
    ├── agent-management/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── configure_agent.py
    └── monitoring/
        ├── SKILL.md
        └── scripts/
            └── query_events.py
```

### **File: `agents/orchestration/.claude/CLAUDE.md`**

```markdown
# Orchestration Agent

You coordinate all background operations for the Brain agent.

## Your Responsibilities

1. **Webhook Operations**
   - Create, edit, delete webhooks
   - Configure commands and triggers
   - Test webhook endpoints
   - Monitor webhook events

2. **Skill Operations**
   - Upload new skills
   - Update existing skills
   - Delete user skills
   - Validate skill structure

3. **Agent Operations**
   - Configure agent settings
   - Upload new agents
   - Manage agent permissions

4. **Database Operations**
   - Query data
   - Generate reports
   - Clean up old data

5. **API Integration**
   - Call external APIs
   - Handle authentication
   - Process responses

6. **Monitoring**
   - Track system health
   - Monitor webhook events
   - Generate alerts

## Available Skills

### webhook-management
Use for: Creating, editing, testing webhooks
Scripts: create_webhook.py, edit_command.py, test_webhook.py

### skill-management
Use for: Uploading, managing skills
Scripts: upload_skill.py, validate_skill.py

### agent-management
Use for: Configuring agents
Scripts: configure_agent.py, upload_agent.py

### monitoring
Use for: System monitoring, event tracking
Scripts: query_events.py, health_check.py

## Execution Pattern

1. **Receive** delegation from Brain
2. **Select** appropriate skill
3. **Execute** operation using skill scripts
4. **Validate** results
5. **Report** back to Brain

## Tools Available

- Read, Write, Edit - File operations
- Bash - Execute scripts
- API calls - HTTP requests

## Example Workflows

### Create Webhook
1. Receive request: "Create GitHub webhook for issue tracking"
2. Use webhook-management skill
3. Call create_webhook.py with parameters
4. Validate webhook created
5. Test webhook endpoint
6. Report webhook URL to Brain

### Upload Skill
1. Receive request: "Upload data-analyzer skill"
2. Use skill-management skill
3. Validate SKILL.md exists
4. Call upload_skill.py
5. Verify files in /data/config/skills/
6. Report success to Brain
```

---

## Subagent Delegation Pattern

### **Example: Webhook Creation**

**User Request:**
```
"Create a Jira webhook that triggers when issues are assigned to AI Agent"
```

**Brain Agent (Step 1: Analyze)**
```
User wants: Jira webhook with assignee trigger
Required: Webhook creation + command configuration
Delegate to: orchestration agent
```

**Brain → Orchestration Agent:**
```
Task: Create Jira webhook
Parameters:
  - Provider: Jira
  - Trigger: issues.assigned
  - Condition: assignee == "AI Agent"
  - Action: create_task
  - Agent: planning
```

**Orchestration Agent (Step 2: Execute)**
```
1. Load webhook-management skill
2. Execute create_webhook.py:
   - Call POST /api/webhooks
   - Configure assignee trigger
   - Set up auto-comment
   - Test webhook
3. Validate webhook active
4. Return webhook_id and endpoint
```

**Orchestration → Brain:**
```
✓ Webhook created: jira-assignee-001
✓ Endpoint: /webhooks/jira/jira-assignee-001
✓ Command configured: assignee trigger
✓ Test passed
```

**Brain → User:**
```
I've created a Jira webhook that triggers when issues are assigned to "AI Agent".

Webhook endpoint: /webhooks/jira/jira-assignee-001

When an issue is assigned to AI Agent:
1. A planning task will be created
2. The bot will comment: "I've been assigned and will analyze this ticket"

The webhook is active and tested.
```

---

## Skill Structure for Orchestration

### **webhook-management/SKILL.md**

```markdown
# Webhook Management Skill

Manages webhook lifecycle operations.

## Capabilities

- Create webhooks with custom configurations
- Edit webhook commands and triggers
- Configure bot mention tags
- Set up assignee triggers
- Test webhooks before deployment
- Monitor webhook events
- Delete webhooks

## Scripts

### create_webhook.py
Creates a new webhook configuration.

Usage:
```bash
python create_webhook.py \
  --provider github \
  --name "GitHub Issues" \
  --triggers "issues.opened,issue_comment.created" \
  --mention-tags "@agent,@bot"
```

### edit_command.py
Edits an existing webhook command.

Usage:
```bash
python edit_command.py \
  --webhook-id webhook-123 \
  --command-id cmd-456 \
  --trigger "issues.assigned" \
  --condition "assignee:AI Agent"
```

### test_webhook.py
Tests a webhook with sample payload.

Usage:
```bash
python test_webhook.py \
  --webhook-id webhook-123 \
  --event-type "issues.opened" \
  --payload-file sample.json
```

## API Endpoints Used

- POST /api/webhooks - Create webhook
- PUT /api/webhooks/{id} - Update webhook
- POST /api/webhooks/{id}/commands - Add command
- PUT /api/webhooks/{id}/commands/{cmd_id} - Edit command
- POST /api/webhooks/{id}/test - Test webhook
- DELETE /api/webhooks/{id} - Delete webhook

## Configuration Options

### Mention Tags
Configure which @mentions trigger the bot:
- @agent
- @ai-assistant
- @bot
- Custom tags

### Assignee Triggers
Configure which assignees trigger actions:
- AI Agent
- automation-bot
- Custom usernames

### Trigger Conditions
- Event type (issues.opened, pr.created, etc.)
- Field conditions (label, status, assignee)
- Pattern matching (regex, contains, equals)

## Examples

### Example 1: GitHub Mention Webhook
```python
create_webhook(
    provider="github",
    name="GitHub Mentions",
    mention_tags=["@agent", "@bot"],
    commands=[{
        "trigger": "issue_comment.created",
        "condition": "body contains @agent",
        "action": "create_task",
        "agent": "planning"
    }]
)
```

### Example 2: Jira Assignee Webhook
```python
create_webhook(
    provider="jira",
    name="Jira Assignee",
    assignee_triggers=["AI Agent"],
    commands=[{
        "trigger": "issues.assigned",
        "condition": "assignee == 'AI Agent'",
        "action": "ask",
        "agent": "brain"
    }]
)
```
```

---

## Benefits of Orchestration Pattern

### **1. Separation of Concerns**
- Brain focuses on understanding user intent
- Orchestration handles execution details
- Specialized subagents for specific domains

### **2. Parallel Execution**
```
Brain delegates multiple tasks:
├─→ Orchestration: Create webhook (async)
├─→ Orchestration: Upload skill (async)
└─→ Orchestration: Query events (async)
     ↓
All execute in parallel
     ↓
Results aggregated and reported
```

### **3. Maintainability**
- Each subagent has clear responsibilities
- Skills are modular and reusable
- Easy to add new capabilities

### **4. Testability**
- Each subagent can be tested independently
- Skills have isolated test suites
- Clear input/output contracts

### **5. Scalability**
- Add new subagents without modifying Brain
- Skills can be updated independently
- Horizontal scaling of subagents

---

## Implementation Checklist

### **Phase 1: Create Orchestration Agent**
- [ ] Create `agents/orchestration/.claude/CLAUDE.md`
- [ ] Define orchestration responsibilities
- [ ] Document available skills

### **Phase 2: Create Skills**
- [ ] webhook-management skill
- [ ] skill-management skill
- [ ] agent-management skill
- [ ] monitoring skill

### **Phase 3: Create Scripts**
- [ ] create_webhook.py
- [ ] edit_command.py
- [ ] test_webhook.py
- [ ] upload_skill.py
- [ ] query_events.py

### **Phase 4: Update Brain Agent**
- [ ] Update Brain CLAUDE.md with delegation pattern
- [ ] Add orchestration agent to agents list
- [ ] Document when to delegate

### **Phase 5: Test Integration**
- [ ] Test Brain → Orchestration delegation
- [ ] Test skill execution
- [ ] Test error handling
- [ ] Test parallel execution

---

## Example: Complete Workflow

**User:** "Set up webhooks for our GitHub repo with @agent mentions and urgent label triggers"

**Brain Agent:**
```
Analyzing request:
- Need 2 webhooks: mentions + labels
- Provider: GitHub
- Delegate to: orchestration agent
```

**Brain → Orchestration:**
```
Task 1: Create mention webhook
Task 2: Create label webhook
Execute in parallel
```

**Orchestration Agent:**
```
Task 1 (webhook-management skill):
  - create_webhook.py --provider github --mention-tags @agent
  - Result: webhook-001 created

Task 2 (webhook-management skill):
  - create_webhook.py --provider github --label-trigger urgent
  - Result: webhook-002 created

Both tasks complete
```

**Orchestration → Brain:**
```
✓ Created 2 webhooks:
  1. webhook-001: @agent mentions → /webhooks/github/webhook-001
  2. webhook-002: urgent labels → /webhooks/github/webhook-002
```

**Brain → User:**
```
I've set up 2 GitHub webhooks for your repo:

1. **Mention Webhook**
   - Triggers when someone mentions @agent in comments
   - Creates a planning task
   - Endpoint: /webhooks/github/webhook-001

2. **Urgent Label Webhook**
   - Triggers when "urgent" label is added
   - Creates high-priority planning task
   - Endpoint: /webhooks/github/webhook-002

Both webhooks are active and tested.
```

---

## Summary

**Orchestration Pattern:**
- ✅ Brain analyzes and delegates
- ✅ Orchestration agent executes
- ✅ Specialized skills for each operation
- ✅ Clean separation of concerns
- ✅ Parallel execution support
- ✅ Fully testable and maintainable

**Brain never does operations directly - always delegates to orchestration!**
