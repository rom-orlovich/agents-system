# Webhook Setup Guide - Full Integration

## Overview

This guide shows how to set up fully functional webhooks integrated with the new architecture, similar to Claude Code CLI. The webhooks support:

- ✅ GitHub issue tracking and automation
- ✅ Pull request review automation
- ✅ Comment-based interactions (@agent mentions)
- ✅ Automatic task creation and queueing
- ✅ GitHub API integration (post comments, reactions, labels)
- ✅ HMAC signature verification
- ✅ Public tunnel access (ngrok/cloudflared)

---

## Quick Start

### 1. Set Up Environment Variables

Create or update `.env` file:

```bash
# GitHub Integration
GITHUB_TOKEN=ghp_your_github_personal_access_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Optional: Database and Redis (if not using defaults)
DATABASE_URL=sqlite+aiosqlite:///data/db/agent.db
REDIS_URL=redis://localhost:6379
```

**Get GitHub Token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `write:discussion`
4. Copy the token to `GITHUB_TOKEN`

**Generate Webhook Secret:**
```bash
# Generate a random secret
openssl rand -hex 32
```

### 2. Start the Application

```bash
# Using Docker Compose
make rebuild

# Or manually
docker-compose up -d
```

### 3. Set Up Public Tunnel

**Option A: Using ngrok**
```bash
# Install ngrok
brew install ngrok

# Start tunnel
./scripts/setup_webhook_tunnel.sh 8000

# You'll get a URL like: https://abc123.ngrok.io
```

**Option B: Using cloudflared**
```bash
# Install cloudflared
brew install cloudflared

# Start tunnel
./scripts/setup_webhook_tunnel.sh 8000

# You'll get a URL like: https://xyz.trycloudflare.com
```

### 4. Configure GitHub Webhook

1. Go to your GitHub repository
2. Navigate to **Settings** → **Webhooks** → **Add webhook**
3. Configure:
   - **Payload URL**: `https://your-tunnel-url.ngrok.io/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: Your `GITHUB_WEBHOOK_SECRET` value
   - **Events**: Select individual events:
     - ✅ Issues
     - ✅ Issue comments
     - ✅ Pull requests
     - ✅ Pull request reviews
4. Click **Add webhook**

---

## How It Works

### Architecture Flow

```
GitHub Event
     ↓
Public Tunnel (ngrok/cloudflared)
     ↓
/webhooks/github endpoint
     ↓
HMAC Signature Verification
     ↓
Event Handler (issue/PR/comment)
     ↓
Task Creation → Redis Queue
     ↓
GitHub API Response (comment/reaction/label)
     ↓
Task Worker picks up task
     ↓
Agent processes task
```

### Supported Events

#### 1. **Issue Opened**
- **Trigger**: New issue created
- **Action**: Creates planning task to analyze issue
- **Response**: Posts comment acknowledging receipt
- **Label**: Adds "bot-processing" label

**Example:**
```
User creates issue: "Bug: Login not working"
↓
Bot posts comment: "🤖 Automated Analysis Started
I've created task `task-abc123` to analyze this issue..."
↓
Planning agent analyzes and responds
```

#### 2. **Issue Comment with @agent**
- **Trigger**: Comment contains "@agent"
- **Action**: Creates planning task
- **Response**: Adds 👀 reaction + acknowledgment comment

**Example:**
```
User comments: "@agent please help with this"
↓
Bot adds 👀 reaction
↓
Bot posts: "👋 I've received your request and created task `task-xyz`..."
↓
Planning agent processes request
```

#### 3. **Pull Request Opened**
- **Trigger**: New PR created
- **Action**: Creates executor task to review PR
- **Response**: Posts comment acknowledging review start

**Example:**
```
User opens PR: "Fix: Resolve login issue"
↓
Bot posts: "🔍 PR Review Started
I've created task `task-def456` to review this pull request..."
↓
Executor agent reviews code and provides feedback
```

---

## Testing

### Local Testing

```bash
# Test webhooks locally (no signature)
python scripts/test_webhook.py http://localhost:8000

# Test with signature verification
python scripts/test_webhook.py http://localhost:8000 your_webhook_secret
```

### Test with Real GitHub Repository

1. Create a test repository
2. Set up webhook as described above
3. Create a test issue
4. Add a comment with "@agent test"
5. Check the dashboard at http://localhost:8000
6. Verify task was created in "Task History" tab
7. Check GitHub for bot's response comment

---

## Configuration Options

### Webhook Customization

Edit `api/webhooks.py` to customize:

**Change mention trigger:**
```python
# Current: "@agent"
if "@agent" in comment_body:

# Change to: "@bot" or "@assistant"
if "@bot" in comment_body:
```

**Customize acknowledgment messages:**
```python
ack_message = (
    f"👋 Custom message here!\n\n"
    f"Task ID: {task_id}"
)
```

**Change agent assignment:**
```python
# Current: planning agent for issues
assigned_agent="planning"

# Change to: brain agent
assigned_agent="brain"
```

### GitHub API Features

The GitHub client (`core/github_client.py`) supports:

- ✅ Post comments to issues/PRs
- ✅ Add reactions (👀, 👍, ❤️, 🚀, etc.)
- ✅ Update issue labels
- ✅ Full GitHub API v3 support

**Example: Add custom label**
```python
await github_client.update_issue_labels(
    repo_owner,
    repo_name,
    issue_number,
    ["bug", "high-priority", "bot-reviewed"]
)
```

---

## Monitoring

### View Webhook Activity

**Dashboard:**
1. Open http://localhost:8000
2. Go to "Task History" tab
3. Filter by source: "webhook"
4. View task details and status

**Logs:**
```bash
# View webhook logs
docker-compose logs -f claude-code-agent | grep webhook

# View GitHub API logs
docker-compose logs -f claude-code-agent | grep github
```

### GitHub Webhook Deliveries

1. Go to repository **Settings** → **Webhooks**
2. Click on your webhook
3. View **Recent Deliveries** tab
4. Check request/response for each event

---

## Troubleshooting

### Webhook Not Receiving Events

**Check tunnel is running:**
```bash
# Verify tunnel URL is accessible
curl https://your-tunnel-url.ngrok.io/api/health
```

**Check GitHub webhook configuration:**
- Payload URL matches tunnel URL
- Content type is `application/json`
- Secret matches `GITHUB_WEBHOOK_SECRET`

**Check logs:**
```bash
docker-compose logs -f claude-code-agent
```

### Signature Verification Failing

**Error:** `Invalid webhook signature`

**Solutions:**
1. Verify `GITHUB_WEBHOOK_SECRET` matches GitHub webhook secret
2. Check secret has no extra spaces or newlines
3. Restart application after changing secret

**Disable verification for testing:**
```bash
# Remove GITHUB_WEBHOOK_SECRET from .env
# Webhook will skip signature verification (dev mode only!)
```

### Comments Not Posting to GitHub

**Error:** `github_comment_failed`

**Solutions:**
1. Verify `GITHUB_TOKEN` is set and valid
2. Check token has `repo` and `write:discussion` scopes
3. Verify repository owner/name are correct
4. Check rate limits: https://api.github.com/rate_limit

**Test GitHub token:**
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user
```

### Tasks Not Being Created

**Check Redis connection:**
```bash
docker-compose logs redis
redis-cli ping
```

**Check database:**
```bash
# View recent tasks
docker-compose exec claude-code-agent python -c "
from core.database import get_session
from core.database.models import TaskDB
import asyncio

async def check():
    async for db in get_session():
        result = await db.execute('SELECT * FROM tasks ORDER BY created_at DESC LIMIT 5')
        tasks = result.fetchall()
        for task in tasks:
            print(task)

asyncio.run(check())
"
```

---

## Advanced Configuration

### Multiple Webhooks

You can create multiple webhooks for different purposes:

**Dashboard UI:**
1. Click "➕ Create Webhook" in side menu
2. Configure webhook name, provider, commands
3. Get unique endpoint URL
4. Configure in GitHub

**Example: Separate webhooks for issues and PRs**
- Webhook 1: `/webhooks/github/webhook-issues-001` (issues only)
- Webhook 2: `/webhooks/github/webhook-prs-001` (PRs only)

### Custom Event Handlers

Add new event handlers in `api/webhooks.py`:

```python
@router.post("/webhooks/github")
async def github_webhook(request: Request, db: AsyncSession):
    event_type = request.headers.get("X-GitHub-Event")
    
    if event_type == "release":
        return await handle_release(payload, db)
    elif event_type == "push":
        return await handle_push(payload, db)
```

### Integration with Dynamic Webhook System

The static webhook endpoint (`/webhooks/github`) works alongside the dynamic webhook system:

**Static endpoint:** `/webhooks/github` (this guide)
- Hardcoded event handlers
- Direct GitHub integration
- Simple setup

**Dynamic endpoints:** `/webhooks/{provider}/{webhook_id}` (from implementation)
- Configurable via dashboard/API
- Custom command mapping
- Template-based responses

Both systems work together seamlessly!

---

## Production Deployment

### Use Permanent Tunnel

**ngrok:**
```bash
# Get permanent domain (requires paid plan)
ngrok http 8000 --domain=your-app.ngrok.app
```

**cloudflared:**
```bash
# Create named tunnel
cloudflared tunnel create claude-agent
cloudflared tunnel route dns claude-agent webhook.yourdomain.com
cloudflared tunnel run claude-agent
```

### Environment Variables

```bash
# Production .env
GITHUB_TOKEN=ghp_production_token
GITHUB_WEBHOOK_SECRET=strong_random_secret
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://production-redis:6379
```

### Security Best Practices

1. ✅ Always use HMAC signature verification
2. ✅ Use strong webhook secrets (32+ characters)
3. ✅ Rotate GitHub tokens regularly
4. ✅ Use HTTPS for all webhook URLs
5. ✅ Monitor webhook logs for suspicious activity
6. ✅ Rate limit webhook endpoints
7. ✅ Validate all payload data

---

## Summary

**Webhook system is now fully functional with:**
- ✅ Public tunnel access (ngrok/cloudflared)
- ✅ GitHub HMAC signature verification
- ✅ Automatic task creation and queueing
- ✅ GitHub API integration (comments, reactions, labels)
- ✅ Support for issues, PRs, and comments
- ✅ Integration with new architecture
- ✅ Testing utilities
- ✅ Comprehensive logging

**Next steps:**
1. Set up tunnel: `./scripts/setup_webhook_tunnel.sh`
2. Configure GitHub webhook with tunnel URL
3. Test with real repository
4. Monitor tasks in dashboard
5. Customize handlers as needed

The webhook system works exactly like Claude Code CLI but integrated with the new agent architecture!
