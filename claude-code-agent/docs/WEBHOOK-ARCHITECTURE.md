# Webhook Architecture: Hybrid Approach

## Overview

This system uses a **hybrid approach** combining **static routes** (hard-coded) and **dynamic routes** (database-driven) for maximum flexibility and maintainability.

## 🎯 Why Hybrid?

### Static Routes (Hard-Coded)
**Best for:**
- ✅ Production webhooks
- ✅ Standard integrations
- ✅ Team-managed configurations
- ✅ Type-safe, validated at startup
- ✅ Version controlled in git

**Limitations:**
- Requires code changes to add/modify
- Requires application restart

### Dynamic Routes (Database-Driven)
**Best for:**
- ✅ User-specific webhooks
- ✅ Runtime configuration
- ✅ A/B testing different webhook configs
- ✅ Multi-tenant scenarios

**Limitations:**
- Less type-safe
- Configuration stored in database
- More complex to debug

## 📁 File Structure

```
core/
  webhook_configs.py      # Static webhook configurations (hard-coded)
  webhook_engine.py       # Shared utilities (render_template, etc.)

api/
  webhooks/               # Static webhook handlers
    __init__.py          # Router registration
    github.py            # GitHub webhook handler (all logic in one file)
    jira.py              # Jira webhook handler
    slack.py             # Slack webhook handler
    sentry.py            # Sentry webhook handler
  webhooks_dynamic.py    # Dynamic webhook receiver (database-driven)
  webhook_status.py       # Webhook status/monitoring API
```

## 🔌 Static Routes (Hard-Coded)

### Endpoints
- `POST /webhooks/github` - GitHub webhook handler
- `POST /webhooks/jira` - Jira webhook handler
- `POST /webhooks/slack` - Slack webhook handler
- `POST /webhooks/sentry` - Sentry webhook handler

### Configuration
**File**: `core/webhook_configs.py`

```python
GITHUB_WEBHOOK: WebhookConfig = WebhookConfig(
    name="github",
    endpoint="/webhooks/github",
    source="github",
    target_agent="brain",
    command_prefix="@agent",
    commands=[
        WebhookCommand(
            name="analyze",
            aliases=["analysis"],
            target_agent="planning",
            prompt_template="Analyze: {{issue.title}}",
        ),
        # ... more commands
    ],
    default_command="analyze",
)
```

### Handler Structure
Each handler (`api/webhooks/github.py`, etc.) contains:
1. **Route handler**: `@router.post("/github")`
2. **Verification function**: `verify_github_signature()`
3. **Immediate response function**: `send_github_immediate_response()`
4. **Command matching function**: `match_github_command()`
5. **Task creation function**: `create_github_task()`

**Key Principle**: One file per provider, all logic isolated.

### Command Matching
- Matches by **command name** or **aliases** in payload text
- Requires **command prefix** (e.g., `@agent`)
- Falls back to **default command** if no match

### Adding a New Static Webhook

1. **Add config** to `core/webhook_configs.py`:
```python
MY_NEW_WEBHOOK: WebhookConfig = WebhookConfig(
    name="my-new-webhook",
    endpoint="/webhooks/my-provider",
    source="my-provider",
    # ... configuration
)
```

2. **Create handler file** `api/webhooks/my_provider.py`:
```python
# Complete handler with all functions
@router.post("/my-provider")
async def my_provider_webhook(...):
    # Handler logic
    pass
```

3. **Register router** in `api/webhooks/__init__.py`:
```python
from .my_provider import router as my_provider_router
router.include_router(my_provider_router, prefix="/webhooks")
```

## 🔄 Flow Tracking

### Overview

Each webhook-initiated task flow creates a special `flow_id` that tracks the entire lifecycle: webhook trigger → analysis → plan creation → PR creation → execution. All tasks in this flow belong to one conversation unless explicitly broken.

### Flow ID Generation

Flow IDs are generated from external IDs (Jira ticket key, GitHub PR number, etc.):

```python
from core.webhook_engine import generate_external_id, generate_flow_id

# Generate external_id from webhook payload
external_id = generate_external_id("jira", payload)  # e.g., "jira:PROJ-123"

# Generate stable flow_id
flow_id = generate_flow_id(external_id)  # e.g., "flow-abc123def456"
```

**Key Properties:**
- **Stable**: Same external_id always generates same flow_id
- **Unique**: Different external_ids generate different flow_ids
- **Persistent**: Flow_id propagates across entire task chain

### Conversation Inheritance

**Default Behavior**: Child tasks automatically inherit parent's `conversation_id`.

**Example Flow:**
```
Webhook → Task #1 (conversation_id="conv-xyz")
  ↓
Task #1 → Task #2 (inherits conversation_id="conv-xyz")
  ↓
Task #2 → Task #3 (inherits conversation_id="conv-xyz")
```

**Breaking Conversation Chain:**

Users can explicitly start new conversations via:
- **Keywords**: "new conversation", "start fresh", "new context", "reset conversation"
- **API Flag**: `new_conversation: true` in task metadata

**Example:**
```
Webhook → Task #1 (conversation_id="conv-1")
  ↓
Task #1 → Task #2 with "new conversation" (conversation_id="conv-2", flow_id="flow-abc" still same)
  ↓
Task #2 → Task #3 (inherits conversation_id="conv-2")
```

**Important**: `flow_id` always propagates even when conversation breaks (for end-to-end tracking).

### Claude Code Tasks Integration

**Background agents read `~/.claude/tasks/` directory** to see completed tasks, dependencies, and results. No context injection needed.

**Sync Behavior:**
- Orchestration tasks are synced to Claude Code Tasks directory (if `sync_to_claude_tasks=True`)
- Claude Code task ID stored in `source_metadata["claude_task_id"]`
- Task status updates when orchestration task completes
- Background agents can check `~/.claude/tasks/` to see task status

**Example Task JSON:**
```json
{
  "id": "claude-task-task-123",
  "title": "Analyze Jira ticket PROJ-123",
  "status": "completed",
  "dependencies": ["claude-task-task-parent"],
  "metadata": {
    "orchestration_task_id": "task-123",
    "flow_id": "flow-abc123",
    "conversation_id": "conv-xyz"
  }
}
```

### Webhook Flow with Flow Tracking

**Updated Flow:**
1. Webhook received → Generate `external_id` (e.g., "jira:PROJ-123")
2. Generate `flow_id` from external_id
3. Create Task #1 (root) with `flow_id`, `initiated_task_id=task_id`
4. Get or create conversation with `flow_id`
5. Sync to Claude Code Tasks (if enabled)
6. Task #1 creates Task #2 → Check: new conversation requested?
   - **NO** → Inherit `flow_id`, `conversation_id` (default)
   - **YES** → Create new conversation, keep `flow_id`
7. All tasks update conversation metrics on completion
8. Update Claude Code Task status when orchestration task completes

## 🔄 Dynamic Routes (Database-Driven)

### Endpoints
- `POST /webhooks/{provider}/{webhook_id}` - Dynamic webhook receiver

### Management API
- `GET /api/webhooks` - List all webhooks
- `POST /api/webhooks` - Create new webhook
- `GET /api/webhooks/{id}` - Get webhook details
- `PUT /api/webhooks/{id}` - Update webhook
- `DELETE /api/webhooks/{id}` - Delete webhook
- `POST /api/webhooks/{id}/enable` - Enable webhook
- `POST /api/webhooks/{id}/disable` - Disable webhook
- `POST /api/webhooks/{id}/commands` - Add command
- `PUT /api/webhooks/{id}/commands/{cmd_id}` - Update command
- `DELETE /api/webhooks/{id}/commands/{cmd_id}` - Delete command

### Configuration
**Storage**: Database (`webhook_configs` table)

**Model**: `WebhookConfigDB`
- `webhook_id`: Unique identifier
- `provider`: github, jira, slack, sentry, etc.
- `endpoint`: `/webhooks/{provider}/{webhook_id}`
- `secret`: Webhook secret for signature verification
- `enabled`: Enable/disable flag

**Commands**: `WebhookCommandDB`
- `trigger`: Event type (e.g., `issues.opened`)
- `action`: Action to execute (`create_task`, `comment`, etc.)
- `template`: Message template with `{{variables}}`
- `conditions`: JSON conditions for matching
- `priority`: Execution order

### Command Matching
- Matches by **trigger** (event type)
- Filters by **conditions** (payload matching)
- Executes in **priority** order (lowest first)

## 🔀 How They Work Together

### Request Flow

1. **Webhook received** at `/webhooks/github` or `/webhooks/github/{webhook_id}`

2. **Routing decision**:
   - Static route: `/webhooks/github` → `api/webhooks/github.py`
   - Dynamic route: `/webhooks/github/{webhook_id}` → `api/webhooks_dynamic.py`

3. **Processing**:
   - **Static**: Uses hard-coded config from `core/webhook_configs.py`
   - **Dynamic**: Loads config from database

4. **Shared utilities**: Both use `core/webhook_engine.py`:
   - `render_template()` - Template rendering
   - `action_create_task()` - Task creation
   - `action_comment()` - Comment posting
   - etc.

## 📊 Comparison

| Feature | Static Routes | Dynamic Routes |
|---------|--------------|----------------|
| **Configuration** | Code (`core/webhook_configs.py`) | Database |
| **Type Safety** | ✅ Pydantic validation | ⚠️ Runtime validation |
| **Version Control** | ✅ Git tracked | ❌ Database only |
| **Startup Validation** | ✅ Yes | ❌ No |
| **Runtime Changes** | ❌ Requires restart | ✅ Immediate |
| **Command Matching** | Name/aliases + prefix | Trigger + conditions |
| **File Structure** | One file per provider | Generic handler |
| **Best For** | Production, standard | User-specific, runtime |

## 🎯 Recommendations

### Use Static Routes When:
- ✅ Standard integrations (GitHub, Jira, Slack, Sentry)
- ✅ Production webhooks
- ✅ Team-managed configurations
- ✅ Type safety is important
- ✅ Changes should be code-reviewed

### Use Dynamic Routes When:
- ✅ User-specific webhooks
- ✅ Runtime configuration needed
- ✅ A/B testing different configs
- ✅ Multi-tenant scenarios
- ✅ Temporary or experimental webhooks

## 🔧 Migration Path

**From Dynamic to Static:**
1. Export webhook config from database
2. Convert to `WebhookConfig` format
3. Add to `core/webhook_configs.py`
4. Create handler file in `api/webhooks/`
5. Register router
6. Test and deploy

**From Static to Dynamic:**
1. Create webhook via `/api/webhooks` API
2. Configure commands via `/api/webhooks/{id}/commands`
3. Use endpoint `/webhooks/{provider}/{webhook_id}`

## 📝 Examples

### Static Webhook Example

```python
# core/webhook_configs.py
GITHUB_WEBHOOK: WebhookConfig = WebhookConfig(
    name="github",
    endpoint="/webhooks/github",
    source="github",
    commands=[
        WebhookCommand(
            name="analyze",
            aliases=["analysis"],
            target_agent="planning",
            prompt_template="Analyze: {{issue.title}}",
        ),
    ],
)
```

**Usage**: `POST /webhooks/github` with GitHub webhook payload

### Dynamic Webhook Example

```bash
# Create via API
curl -X POST http://localhost:8000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "github",
    "name": "My Custom Webhook",
    "secret": "my-secret"
  }'

# Add command
curl -X POST http://localhost:8000/api/webhooks/{webhook_id}/commands \
  -H "Content-Type: application/json" \
  -d '{
    "trigger": "issues.opened",
    "action": "create_task",
    "agent": "planning",
    "template": "New issue: {{issue.title}}"
  }'
```

**Usage**: `POST /webhooks/github/{webhook_id}` with GitHub webhook payload

## ✅ Benefits of Hybrid Approach

1. **Flexibility**: Choose the right approach for each use case
2. **Maintainability**: Static routes are easy to understand and maintain
3. **Scalability**: Dynamic routes support runtime configuration
4. **Type Safety**: Static routes validated at startup
5. **Backward Compatibility**: Old dynamic system still works
6. **Gradual Migration**: Move from dynamic to static over time
