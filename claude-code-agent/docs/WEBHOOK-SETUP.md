# 🔗 Webhook Setup & Architecture Guide

This comprehensive guide covers both the architecture and setup instructions for webhooks in this system.

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Setup Instructions](#setup-instructions)
3. [Configuration Examples](#configuration-examples)
4. [Reference](#reference)

---

## 🏗️ Architecture Overview

### Hybrid Webhook Architecture

This system uses a **hybrid approach** combining **static routes** (hard-coded) and **dynamic routes** (database-driven) for maximum flexibility and maintainability.

### Why Hybrid?

#### Static Routes (Hard-Coded)
**Best for:**
- ✅ Production webhooks
- ✅ Standard integrations
- ✅ Team-managed configurations
- ✅ Type-safe, validated at startup
- ✅ Version controlled in git

**Limitations:**
- Requires code changes to add/modify
- Requires application restart

#### Dynamic Routes (Database-Driven)
**Best for:**
- ✅ User-specific webhooks
- ✅ Runtime configuration
- ✅ A/B testing different webhook configs
- ✅ Multi-tenant scenarios

**Limitations:**
- Less type-safe
- Configuration stored in database
- More complex to debug

### File Structure

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

### Static Routes (Hard-Coded)

#### Endpoints
- `POST /webhooks/github` - GitHub webhook handler
- `POST /webhooks/jira` - Jira webhook handler
- `POST /webhooks/slack` - Slack webhook handler
- `POST /webhooks/sentry` - Sentry webhook handler

#### Configuration
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

#### Handler Structure
Each handler (`api/webhooks/github.py`, etc.) contains:
1. **Route handler**: `@router.post("/github")`
2. **Verification function**: `verify_github_signature()`
3. **Immediate response function**: `send_github_immediate_response()`
4. **Command matching function**: `match_github_command()`
5. **Task creation function**: `create_github_task()`

**Key Principle**: One file per provider, all logic isolated.

#### Command Matching
- Matches by **command name** or **aliases** in payload text
- Requires **command prefix** (e.g., `@agent`)
- Falls back to **default command** if no match

### Dynamic Routes (Database-Driven)

#### Endpoints
- `POST /webhooks/{provider}/{webhook_id}` - Dynamic webhook receiver

#### Management API
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

#### Configuration
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

#### Command Matching
- Matches by **trigger** (event type)
- Filters by **conditions** (payload matching)
- Executes in **priority** order (lowest first)

### How They Work Together

#### Request Flow

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

### Comparison

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

### Recommendations

#### Use Static Routes When:
- ✅ Standard integrations (GitHub, Jira, Slack, Sentry)
- ✅ Production webhooks
- ✅ Team-managed configurations
- ✅ Type safety is important
- ✅ Changes should be code-reviewed

#### Use Dynamic Routes When:
- ✅ User-specific webhooks
- ✅ Runtime configuration needed
- ✅ A/B testing different configs
- ✅ Multi-tenant scenarios
- ✅ Temporary or experimental webhooks

### Migration Path

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

### Benefits of Hybrid Approach

1. **Flexibility**: Choose the right approach for each use case
2. **Maintainability**: Static routes are easy to understand and maintain
3. **Scalability**: Dynamic routes support runtime configuration
4. **Type Safety**: Static routes validated at startup
5. **Backward Compatibility**: Old dynamic system still works
6. **Gradual Migration**: Move from dynamic to static over time

---

## 🚀 Setup Instructions

### Step 1: Setup Public Tunnel

#### Option A: Using ngrok (Recommended)

1. **Install ngrok**:
   ```bash
   brew install ngrok
   # or download from https://ngrok.com/download
   ```

2. **Get your auth token** from https://dashboard.ngrok.com/get-started/your-authtoken

3. **Set auth token**:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

4. **Start the tunnel**:
   ```bash
   make tunnel
   ```

5. **Copy your public URL** (e.g., `https://abc123.ngrok.io`)

6. **Update .env**:
   ```bash
   WEBHOOK_PUBLIC_DOMAIN=https://abc123.ngrok.io
   ```

#### Option B: Using Cloudflare Tunnel (Free, No Limits)

1. **Install cloudflared**:
   ```bash
   brew install cloudflared
   ```

2. **Start tunnel**:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. **Copy the public URL** and update `.env`

### Step 2: Choose Webhook Type

#### Option A: Use Static Routes (Recommended)

Static webhooks are hard-coded and ready to use. No setup needed!

**Available Static Webhooks:**
- `POST /webhooks/github` - GitHub issues, PRs, comments
- `POST /webhooks/jira` - Jira ticket updates
- `POST /webhooks/slack` - Slack commands and mentions
- `POST /webhooks/sentry` - Sentry error alerts

**Configuration**: Edit `core/webhook_configs.py` to customize commands and templates.

**To add a new static webhook:**
1. Add config to `core/webhook_configs.py`
2. Create handler file in `api/webhooks/{provider}.py`
3. Register router in `api/webhooks/__init__.py`

#### Option B: Create Dynamic Webhooks via API

1. Open dashboard: http://localhost:8000
2. Click **"Webhooks"** tab
3. Click **"Create Webhook"** in side menu
4. Configure provider, triggers, and actions

### Step 3: Configure Service Webhooks

#### GitHub Setup

1. Go to your repository → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://YOUR-DOMAIN.ngrok.io/webhooks/github` (static route)
   - Or use dynamic route: `https://YOUR-DOMAIN.ngrok.io/webhooks/github/{webhook_id}` (created via API)
3. **Content type**: `application/json`
4. **Secret**: (same as in your webhook config)
5. **Events**: Select events you want (Issues, Pull requests, Push, etc.)
6. Click **Add webhook**

#### Jira Setup

1. Go to **Jira Settings** → **System** → **WebHooks**
2. Click **Create a WebHook**
3. **Name**: Claude Agent
4. **URL**: `https://YOUR-DOMAIN.ngrok.io/webhooks/jira` (static route)
   - Or use dynamic route: `https://YOUR-DOMAIN.ngrok.io/webhooks/jira/{webhook_id}` (created via API)
5. **Events**: Select events (Issue created, updated, etc.)
6. Click **Create**

#### Slack Setup

1. Go to https://api.slack.com/apps
2. Create new app or select existing
3. **Event Subscriptions** → Enable Events
4. **Request URL**: `https://YOUR-DOMAIN.ngrok.io/webhooks/slack` (static route)
   - Or use dynamic route: `https://YOUR-DOMAIN.ngrok.io/webhooks/slack/{webhook_id}` (created via API)
5. Subscribe to events: `app_mention`, `message.channels`
6. **Slash Commands** → Create command
7. **Request URL**: `https://YOUR-DOMAIN.ngrok.io/webhooks/slack` (static route)

### Step 4: Test Your Webhooks

1. **Trigger an event** in your service (create issue, push code, etc.)
2. **Check dashboard** → Webhooks tab → Recent Events
3. **View task** created by webhook
4. **Check logs**: `make logs`

---

## 📦 Configuration Examples

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

### Pre-configured Static Webhook Commands

#### 🐙 GitHub Webhooks

##### Issue Created → Create Task
```yaml
Name: GitHub Issues
Provider: github
Secret: your-webhook-secret
Enabled: ✓

Commands:
  - Trigger: issues.opened
    Action: create_task
    Agent: planning
    Template: |
      New GitHub issue: {{issue.title}}
      
      Repository: {{repository.full_name}}
      Author: {{issue.user.login}}
      
      {{issue.body}}
      
      Please analyze this issue and create a plan to resolve it.
```

##### Pull Request Review
```yaml
Name: GitHub PR Review
Provider: github
Secret: your-webhook-secret
Enabled: ✓

Commands:
  - Trigger: pull_request.opened
    Action: create_task
    Agent: executor
    Template: |
      Review pull request: {{pull_request.title}}
      
      Repository: {{repository.full_name}}
      Author: {{pull_request.user.login}}
      Branch: {{pull_request.head.ref}}
      
      {{pull_request.body}}
      
      Please review this PR for:
      1. Code quality
      2. Security issues
      3. Best practices
      4. Test coverage
```

##### Push to Main → Run Tests
```yaml
Name: GitHub CI/CD
Provider: github
Secret: your-webhook-secret
Enabled: ✓

Commands:
  - Trigger: push
    Action: create_task
    Agent: executor
    Template: |
      New push to {{ref}}
      
      Repository: {{repository.full_name}}
      Pusher: {{pusher.name}}
      Commits: {{commits|length}}
      
      Latest commit: {{head_commit.message}}
      
      Please run tests and report results.
```

#### 🎫 Jira Webhooks

##### Issue Created
```yaml
Name: Jira Issues
Provider: jira
Secret: your-webhook-secret
Enabled: ✓

Commands:
  - Trigger: jira:issue_created
    Action: create_task
    Agent: planning
    Template: |
      New Jira issue: {{issue.key}} - {{issue.fields.summary}}
      
      Type: {{issue.fields.issuetype.name}}
      Priority: {{issue.fields.priority.name}}
      Reporter: {{issue.fields.reporter.displayName}}
      
      Description:
      {{issue.fields.description}}
      
      Please analyze and create implementation plan.
```

##### Issue Updated
```yaml
Name: Jira Updates
Provider: jira
Secret: your-webhook-secret
Enabled: ✓

Commands:
  - Trigger: jira:issue_updated
    Action: create_task
    Agent: brain
    Template: |
      Jira issue updated: {{issue.key}}
      
      Changes: {{changelog.items|map(attribute='field')|join(', ')}}
      
      Please review the changes and update related tasks.
```

#### 💬 Slack Webhooks

##### Slash Command
```yaml
Name: Slack Commands
Provider: slack
Secret: your-webhook-secret
Enabled: ✓

Commands:
  - Trigger: slash_command
    Action: respond
    Agent: brain
    Template: |
      Slack command from {{user_name}} in #{{channel_name}}:
      
      {{text}}
```

##### Message Mention
```yaml
Name: Slack Mentions
Provider: slack
Secret: your-webhook-secret
Enabled: ✓

Commands:
  - Trigger: app_mention
    Action: respond
    Agent: brain
    Template: |
      {{event.user}} mentioned the bot in #{{event.channel}}:
      
      {{event.text}}
```

#### 🔔 Generic Webhooks

##### Custom Integration
```yaml
Name: Custom Service
Provider: generic
Secret: your-webhook-secret
Enabled: ✓

Commands:
  - Trigger: custom.event
    Action: create_task
    Agent: brain
    Template: |
      Custom event received:
      
      {{payload}}
```

---

## 📚 Reference

### Available Webhook Endpoints

#### Static Routes (Hard-Coded)

| Service | Endpoint | Type | Configuration |
|---------|----------|------|---------------|
| GitHub | `POST /webhooks/github` | Static | `core/webhook_configs.py` |
| Jira | `POST /webhooks/jira` | Static | `core/webhook_configs.py` |
| Slack | `POST /webhooks/slack` | Static | `core/webhook_configs.py` |
| Sentry | `POST /webhooks/sentry` | Static | `core/webhook_configs.py` |

#### Dynamic Routes (Database-Driven)

| Service | Endpoint | Type | Management |
|---------|----------|------|------------|
| GitHub | `POST /webhooks/github/{webhook_id}` | Dynamic | `/api/webhooks` |
| Jira | `POST /webhooks/jira/{webhook_id}` | Dynamic | `/api/webhooks` |
| Slack | `POST /webhooks/slack/{webhook_id}` | Dynamic | `/api/webhooks` |
| Sentry | `POST /webhooks/sentry/{webhook_id}` | Dynamic | `/api/webhooks` |
| Custom | `POST /webhooks/custom/{webhook_id}` | Dynamic | `/api/webhooks` |

**Note**: Both static and dynamic routes can coexist. Static routes are recommended for standard integrations, while dynamic routes are useful for user-specific or runtime-configured webhooks.

### Template Variables

Templates use Jinja2 syntax. Available variables depend on the service:

#### GitHub
- `{{issue.title}}`, `{{issue.body}}`, `{{issue.user.login}}`
- `{{pull_request.title}}`, `{{pull_request.body}}`
- `{{repository.full_name}}`, `{{repository.url}}`
- `{{commits}}`, `{{head_commit.message}}`

#### Jira
- `{{issue.key}}`, `{{issue.fields.summary}}`
- `{{issue.fields.description}}`, `{{issue.fields.priority.name}}`
- `{{changelog.items}}`

#### Slack
- `{{user_name}}`, `{{channel_name}}`, `{{text}}`
- `{{event.user}}`, `{{event.text}}`, `{{event.channel}}`

### Troubleshooting

#### Webhook not receiving events
- ✅ Check tunnel is running: `make tunnel`
- ✅ Verify `WEBHOOK_PUBLIC_DOMAIN` in `.env`
- ✅ Check webhook is enabled in dashboard
- ✅ Verify secret matches in both service and dashboard
- ✅ Check service webhook delivery logs

#### Events received but no task created
- ✅ Check webhook command trigger matches event type
- ✅ Verify template syntax is correct
- ✅ Check logs: `make logs`
- ✅ View Recent Events in dashboard

#### Authentication errors
- ✅ Verify webhook secret matches
- ✅ Check provider signature validation
- ✅ Review service webhook settings

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

### Next Steps

1. Create webhooks in dashboard
2. Configure service webhooks
3. Test with real events
4. Monitor in dashboard
5. Adjust templates as needed
