# Slack OAuth Setup Guide

## Step 1: Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Select **From scratch**
4. Enter app name: `Agent Bot`
5. Select your workspace
6. Click **Create App**

---

## Step 2: Configure OAuth & Permissions

### Add Redirect URL

1. Go to **OAuth & Permissions** (left sidebar)
2. Scroll to **Redirect URLs**
3. Click **Add New Redirect URL**
4. Enter:
   ```
   https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/slack
   ```
5. Click **Add**
6. Click **Save URLs**

### Set Scopes

Scroll down to **Scopes** → **Bot Token Scopes**

Add these scopes:
- `channels:read` - View basic channel info
- `chat:write` - Send messages
- `commands` - Add slash commands
- `im:write` - Send DMs
- `users:read` - View users
- `team:read` - View workspace info

---

## Step 3: Get Credentials

### Basic Information

1. Go to **Basic Information** (left sidebar)
2. Copy these values:

**App ID:**
```
A01234567
```

**Client ID:**
```
123456789.123456789
```

**Client Secret:**
```
Click "Show" and copy the secret
```

**Signing Secret:**
```
Click "Show" and copy the secret
```

---

## Step 4: Generate State Secret

Run this command to generate a secure state secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output.

---

## Step 5: Update .env

Add to `/Users/romo/projects/agents-prod/agent-bot/oauth-service/.env`:

```bash
SLACK_CLIENT_ID=123456789.123456789
SLACK_CLIENT_SECRET=your_client_secret_here
SLACK_SIGNING_SECRET=your_signing_secret_here
SLACK_STATE_SECRET=your_generated_state_secret_here
```

---

## Step 6: Enable Event Subscriptions (Optional)

If you want to receive Slack events:

1. Go to **Event Subscriptions** (left sidebar)
2. Toggle **Enable Events** to On
3. Enter Request URL:
   ```
   https://unabating-unoverdrawn-veronique.ngrok-free.dev/webhooks/slack
   ```
4. Wait for verification (should show ✅ Verified)
5. Subscribe to bot events:
   - `message.channels` - Messages in channels
   - `message.im` - Direct messages
6. Click **Save Changes**

---

## Step 7: Add Slash Commands (Optional)

If you want slash commands like `/agent`:

1. Go to **Slash Commands** (left sidebar)
2. Click **Create New Command**
3. Fill in:
   - **Command:** `/agent`
   - **Request URL:** `https://unabating-unoverdrawn-veronique.ngrok-free.dev/webhooks/slack/commands`
   - **Short Description:** `Interact with Agent Bot`
   - **Usage Hint:** `[help|status|approve]`
4. Click **Save**

---

## Step 8: Install App to Workspace

1. Go to **Install App** (left sidebar)
2. Click **Install to Workspace**
3. Review permissions
4. Click **Allow**

You'll be redirected to the OAuth callback URL and see a success message.

---

## Testing the Setup

### 1. Start ngrok

```bash
cd oauth-service
./start-ngrok.sh
```

### 2. Restart oauth-service

```bash
docker-compose restart oauth-service
```

### 3. Test OAuth flow

```bash
open https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/install/slack
```

### 4. Verify installation

```bash
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/installations?platform=slack
```

Should return:
```json
[
  {
    "id": 2,
    "platform": "slack",
    "external_org_id": "T01234567",
    "external_org_name": "Your Workspace",
    "status": "ACTIVE",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### 5. Test sending a message

```bash
curl -X POST https://unabating-unoverdrawn-veronique.ngrok-free.dev/api/slack/message \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "T01234567",
    "channel": "#general",
    "text": "Hello from Agent Bot!"
  }'
```

---

## Troubleshooting

### OAuth callback not working

**Error:** "The redirect_uri does not match"

**Fix:** Verify redirect URL matches exactly:
```
https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/slack
```

### Event subscription verification failed

**Error:** "Your URL didn't respond with the value of the challenge parameter"

**Fix:**
1. Ensure oauth-service is running: `docker-compose ps oauth-service`
2. Ensure ngrok is running: `./start-ngrok.sh`
3. Check logs: `docker-compose logs oauth-service`

### Signing secret validation failed

**Error:** "Invalid signature"

**Fix:**
1. Copy signing secret from **Basic Information** page
2. Update `SLACK_SIGNING_SECRET` in .env
3. Restart service: `docker-compose restart oauth-service`

### App not appearing in workspace

**Error:** App installed but not visible

**Fix:**
1. Go to workspace Slack
2. Click "Apps" in left sidebar
3. Search for "Agent Bot"
4. Or reinstall: **Install App** → **Reinstall to Workspace**

---

## Production Deployment

When deploying to production:

1. **Update redirect URLs** in Slack app settings:
   ```
   https://oauth.yourdomain.com/oauth/callback/slack
   ```

2. **Update event subscription URL:**
   ```
   https://oauth.yourdomain.com/webhooks/slack
   ```

3. **Update slash command URL:**
   ```
   https://oauth.yourdomain.com/webhooks/slack/commands
   ```

4. **Update .env:**
   ```bash
   BASE_URL=https://oauth.yourdomain.com
   ```

5. **Distribute app:**
   - Go to **Manage Distribution**
   - Complete the checklist
   - Activate public distribution
   - Submit to Slack App Directory (optional)

---

## Slack App Distribution

### Internal Use Only

If only for your organization:
1. Keep app in your workspace
2. No need for public distribution
3. Install manually in workspace

### Public Distribution

If distributing to other workspaces:
1. Complete **Manage Distribution** checklist
2. Add app icon and description
3. Submit for review
4. Once approved, generate shareable install URL:
   ```
   https://slack.com/oauth/v2/authorize?client_id=YOUR_CLIENT_ID&scope=channels:read,chat:write,commands,im:write,users:read,team:read
   ```

---

## Next Steps

- [ ] Test sending messages to Slack channels
- [ ] Configure slash commands in agent-engine
- [ ] Set up interactive components (buttons, modals)
- [ ] Test approval workflows via Slack
