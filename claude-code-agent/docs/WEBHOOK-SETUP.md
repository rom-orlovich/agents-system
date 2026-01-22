# 🔗 Webhook Setup Guide

This guide shows you how to set up webhooks for GitHub, Jira, Slack, and other services.

## 📡 Step 1: Setup Public Tunnel

### Option A: Using ngrok (Recommended)

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

### Option B: Using Cloudflare Tunnel (Free, No Limits)

1. **Install cloudflared**:
   ```bash
   brew install cloudflared
   ```

2. **Start tunnel**:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. **Copy the public URL** and update `.env`

## 🔧 Step 2: Create Webhooks in Dashboard

1. Open dashboard: http://localhost:8000
2. Click **"Webhooks"** tab
3. Click **"Create Webhook"** in side menu

## 📦 Pre-configured Webhook Templates

### 🐙 GitHub Webhooks

#### Issue Created → Create Task
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

#### Pull Request Review
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

#### Push to Main → Run Tests
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

### 🎫 Jira Webhooks

#### Issue Created
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

#### Issue Updated
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

### 💬 Slack Webhooks

#### Slash Command
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

#### Message Mention
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

### 🔔 Generic Webhooks

#### Custom Integration
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

## 🔐 Step 3: Configure Service Webhooks

### GitHub Setup

1. Go to your repository → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://YOUR-DOMAIN.ngrok.io/webhooks/github`
3. **Content type**: `application/json`
4. **Secret**: (same as in your webhook config)
5. **Events**: Select events you want (Issues, Pull requests, Push, etc.)
6. Click **Add webhook**

### Jira Setup

1. Go to **Jira Settings** → **System** → **WebHooks**
2. Click **Create a WebHook**
3. **Name**: Claude Agent
4. **URL**: `https://YOUR-DOMAIN.ngrok.io/webhooks/jira`
5. **Events**: Select events (Issue created, updated, etc.)
6. Click **Create**

### Slack Setup

1. Go to https://api.slack.com/apps
2. Create new app or select existing
3. **Event Subscriptions** → Enable Events
4. **Request URL**: `https://YOUR-DOMAIN.ngrok.io/webhooks/slack`
5. Subscribe to events: `app_mention`, `message.channels`
6. **Slash Commands** → Create command
7. **Request URL**: `https://YOUR-DOMAIN.ngrok.io/webhooks/slack`

## 📊 Step 4: Test Your Webhooks

1. **Trigger an event** in your service (create issue, push code, etc.)
2. **Check dashboard** → Webhooks tab → Recent Events
3. **View task** created by webhook
4. **Check logs**: `make logs`

## 🔍 Troubleshooting

### Webhook not receiving events
- ✅ Check tunnel is running: `make tunnel`
- ✅ Verify `WEBHOOK_PUBLIC_DOMAIN` in `.env`
- ✅ Check webhook is enabled in dashboard
- ✅ Verify secret matches in both service and dashboard
- ✅ Check service webhook delivery logs

### Events received but no task created
- ✅ Check webhook command trigger matches event type
- ✅ Verify template syntax is correct
- ✅ Check logs: `make logs`
- ✅ View Recent Events in dashboard

### Authentication errors
- ✅ Verify webhook secret matches
- ✅ Check provider signature validation
- ✅ Review service webhook settings

## 🎯 Available Webhook Endpoints

| Service | Endpoint | Provider |
|---------|----------|----------|
| GitHub | `/webhooks/github` | `github` |
| Jira | `/webhooks/jira` | `jira` |
| Slack | `/webhooks/slack` | `slack` |
| GitLab | `/webhooks/gitlab` | `gitlab` |
| Bitbucket | `/webhooks/bitbucket` | `bitbucket` |
| Custom | `/webhooks/custom/{webhook_id}` | `generic` |

## 📝 Template Variables

Templates use Jinja2 syntax. Available variables depend on the service:

### GitHub
- `{{issue.title}}`, `{{issue.body}}`, `{{issue.user.login}}`
- `{{pull_request.title}}`, `{{pull_request.body}}`
- `{{repository.full_name}}`, `{{repository.url}}`
- `{{commits}}`, `{{head_commit.message}}`

### Jira
- `{{issue.key}}`, `{{issue.fields.summary}}`
- `{{issue.fields.description}}`, `{{issue.fields.priority.name}}`
- `{{changelog.items}}`

### Slack
- `{{user_name}}`, `{{channel_name}}`, `{{text}}`
- `{{event.user}}`, `{{event.text}}`, `{{event.channel}}`

## 🚀 Next Steps

1. Create webhooks in dashboard
2. Configure service webhooks
3. Test with real events
4. Monitor in dashboard
5. Adjust templates as needed
