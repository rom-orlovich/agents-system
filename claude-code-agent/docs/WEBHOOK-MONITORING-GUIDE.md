# Webhook Monitoring Guide

## ✅ Features Added

Your dashboard now includes comprehensive webhook monitoring with:

### 1. **Webhook Status Overview**
- Total webhook count
- Active webhook count  
- Public domain display
- Real-time status updates

### 2. **Available Webhook URLs**
Shows all webhook endpoints with:
- **Static endpoints** (GitHub, Jira, Slack)
- **Dynamic endpoints** (user-created webhooks)
- **Public URLs** (when ngrok domain is configured)
- **Copy to clipboard** button for each URL

### 3. **Recent Webhook Events Log**
- Last 50 webhook events
- Event type and timestamp
- Matched commands
- Created tasks
- Response status

---

## 🔧 Configuration

### Set Your Public Domain

Add to `.env`:
```bash
# If using ngrok
WEBHOOK_PUBLIC_DOMAIN=abc123.ngrok.io

# If using cloudflare tunnel
WEBHOOK_PUBLIC_DOMAIN=webhooks.yourdomain.com

# If using custom domain
WEBHOOK_PUBLIC_DOMAIN=api.yourdomain.com
```

**Without this:** Dashboard shows "Public URL not available"  
**With this:** Dashboard shows full `https://` URLs ready to copy

---

## 📊 Dashboard Features

### Webhook Status Tab

When you click **📡 Webhooks** in the side menu, you'll see:

**1. Status Cards:**
```
┌─────────────────┬─────────────────┬─────────────────┐
│ Total Webhooks  │     Active      │ Public Domain   │
│       5         │        3        │ abc123.ngrok.io │
└─────────────────┴─────────────────┴─────────────────┘
```

**2. Available Webhook URLs:**
```
🔗 Available Webhook URLs

┌──────────────────────────────────────────────────┐
│ GitHub Static                          [static]  │
│ Endpoint: /webhooks/github                       │
│ Public URL: https://abc123.ngrok.io/webhooks... │
│                                      [📋 Copy]   │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ My Custom Webhook              [dynamic] [✓]     │
│ Endpoint: /webhooks/github/webhook-abc123        │
│ Public URL: https://abc123.ngrok.io/webhooks... │
│                                      [📋 Copy]   │
└──────────────────────────────────────────────────┘
```

**3. Recent Webhook Events:**
```
📋 Recent Webhook Events                    [🔄]

issues.opened                    2026-01-22 13:30
Provider: github | Command: cmd-123 | Task: task-456
[Response Sent]

issue_comment.created            2026-01-22 13:25
Provider: github | Command: cmd-789 | Task: task-012
[Response Sent]
```

---

## 🎯 How to Use

### View Webhook Status

1. Open dashboard: http://localhost:8000
2. Click **📡 Webhooks** in side menu
3. See all webhook URLs and status

### Copy Webhook URL

1. Find your webhook in the list
2. Click **📋 Copy** button next to Public URL
3. Paste into GitHub/Jira/Slack webhook configuration

### Monitor Webhook Activity

1. Check "Recent Webhook Events" section
2. See which events triggered
3. View created tasks
4. Check if responses were sent

### Refresh Data

Click **🔄 Refresh** button to reload:
- Webhook status
- Available URLs
- Recent events

---

## 🔗 Static vs Dynamic Webhooks

### Static Webhooks (Always Available)

These are built-in and always active:

| Name | Endpoint | Provider |
|------|----------|----------|
| GitHub Static | `/webhooks/github` | github |
| Jira Static | `/webhooks/jira` | jira |
| Slack Static | `/webhooks/slack` | slack |

**Use for:** Simple, hardcoded webhook handlers

### Dynamic Webhooks (User-Created)

Created via dashboard or API:

| Name | Endpoint | Provider |
|------|----------|----------|
| My Issue Tracker | `/webhooks/github/webhook-abc123` | github |
| PR Reviewer | `/webhooks/github/webhook-def456` | github |

**Use for:** Custom, configurable webhook handlers with commands

---

## 🌐 Using with Ngrok

### Start Ngrok Tunnel

```bash
# Start tunnel
make tunnel

# Or manually
ngrok http 8000
```

### Copy Your Domain

Ngrok will show:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

### Update .env

```bash
WEBHOOK_PUBLIC_DOMAIN=abc123.ngrok.io
```

### Restart

```bash
docker-compose restart
```

### Verify

1. Open dashboard
2. Go to Webhooks tab
3. See public URLs like: `https://abc123.ngrok.io/webhooks/github`

---

## 📋 API Endpoints

The monitoring uses these new API endpoints:

### Get Webhook Status
```bash
GET /api/webhooks/status

Response:
{
  "success": true,
  "data": {
    "webhooks": [...],
    "total_count": 5,
    "active_count": 3,
    "public_domain": "abc123.ngrok.io",
    "static_endpoints": [...]
  }
}
```

### Get Recent Events
```bash
GET /api/webhooks/events/recent?limit=50

Response:
{
  "success": true,
  "data": [
    {
      "event_id": "evt-123",
      "webhook_id": "webhook-456",
      "provider": "github",
      "event_type": "issues.opened",
      "task_id": "task-789",
      "created_at": "2026-01-22T13:30:00"
    }
  ]
}
```

### Get Webhook-Specific Events
```bash
GET /api/webhooks/{webhook_id}/events?limit=50
```

---

## 🎨 UI Features

### Color Coding

- **Blue badges** = Static webhooks
- **Green badges** = Dynamic webhooks
- **Red badges** = Disabled webhooks
- **Yellow warning** = Public URL not configured

### Status Indicators

- ✅ **Active** = Webhook is enabled
- ❌ **Disabled** = Webhook is disabled
- ⚠️ **Warning** = Configuration issue

### Real-time Updates

- Click 🔄 Refresh to update data
- Auto-refreshes when switching to Webhooks tab
- Shows latest 50 events

---

## 🔍 Troubleshooting

### "Public URL not available" Warning

**Problem:** WEBHOOK_PUBLIC_DOMAIN not set

**Solution:**
```bash
# Add to .env
WEBHOOK_PUBLIC_DOMAIN=your-ngrok-domain.ngrok.io

# Restart
docker-compose restart
```

### No Webhooks Showing

**Problem:** No webhooks created yet

**Solution:**
1. Click "➕ Create Webhook" in side menu
2. Or use static endpoints (always available)

### No Recent Events

**Problem:** No webhook events received yet

**Solution:**
1. Configure webhook in GitHub/Jira/Slack
2. Trigger an event (create issue, comment, etc.)
3. Check events list

### Events Not Appearing

**Problem:** Webhook not receiving events

**Check:**
1. Ngrok tunnel is running
2. Public domain is correct in .env
3. GitHub webhook URL matches public URL
4. Webhook secret matches (if configured)

---

## ✅ Summary

**You now have:**
- ✅ Real-time webhook status monitoring
- ✅ All webhook URLs displayed with copy buttons
- ✅ Ngrok domain support
- ✅ Recent webhook events log
- ✅ Static and dynamic webhook visibility
- ✅ Easy-to-use dashboard UI

**To use:**
1. Set `WEBHOOK_PUBLIC_DOMAIN` in `.env`
2. Start ngrok: `make tunnel`
3. Open dashboard → Webhooks tab
4. Copy webhook URLs
5. Configure in GitHub/Jira/Slack
6. Monitor events in real-time

**Your webhooks are now fully visible and monitored!** 🎉
