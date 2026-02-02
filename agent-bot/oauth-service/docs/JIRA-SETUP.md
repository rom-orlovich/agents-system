# Jira OAuth Setup Guide

## Step 1: Create Atlassian OAuth App

1. Go to [developer.atlassian.com/console/myapps](https://developer.atlassian.com/console/myapps/)
2. Click **Create** → **OAuth 2.0 integration**
3. Enter app name: `Agent Bot`
4. Check agreement and click **Create**

---

## Step 2: Configure OAuth 2.0 (3LO)

### Add Callback URL

1. Click **Authorization** (left sidebar)
2. Under **OAuth 2.0 (3LO)**, click **Add**
3. Enter callback URL:
   ```
   https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/jira
   ```
4. Click **Save changes**

---

## Step 3: Configure Permissions

1. Click **Permissions** (left sidebar)
2. Click **Add** under Jira API
3. Select these scopes:

**Jira platform REST API:**
- `read:jira-work` - View Jira issues
- `write:jira-work` - Create and update issues
- `read:jira-user` - View user information

**Optional (for advanced features):**
- `read:project:jira` - View project details
- `read:issue-details:jira` - View issue details
- `write:issue:jira` - Update issues
- `read:comment:jira` - View comments
- `write:comment:jira` - Add comments

4. Click **Save changes**

---

## Step 4: Get Credentials

1. Click **Settings** (left sidebar)
2. Copy these values:

**Client ID:**
```
Your client ID will be shown here
```

**Secret:**
If not generated yet:
1. Click **Generate secret**
2. Copy the secret (⚠️ **only shown once!**)
3. Save it securely

---

## Step 5: Update .env

Add to `/Users/romo/projects/agents-prod/agent-bot/oauth-service/.env`:

```bash
JIRA_CLIENT_ID=your_jira_client_id_here
JIRA_CLIENT_SECRET=your_jira_client_secret_here
```

---

## Step 6: Configure Distribution (Optional)

If distributing to other Jira sites:

1. Click **Distribution** (left sidebar)
2. Fill in app details:
   - App name: `Agent Bot`
   - Description: `Automated issue management and code fixes`
   - Support URL: Your support page URL
   - Privacy policy URL: Your privacy policy URL
3. Upload app icon (512x512 PNG)
4. Click **Save changes**

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
open https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/install/jira
```

This will:
1. Redirect to Atlassian authorization page
2. Ask you to select Jira site (if multiple)
3. Request permission for scopes
4. Redirect back to callback URL
5. Store access token and refresh token

### 4. Verify installation

```bash
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/installations?platform=jira
```

Should return:
```json
[
  {
    "id": 3,
    "platform": "jira",
    "external_org_id": "your-jira-site-id",
    "external_org_name": "yourcompany.atlassian.net",
    "status": "ACTIVE",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### 5. Test API access

```bash
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/api/jira/issues?project=PROJ
```

---

## Jira OAuth Flow Details

### Authorization URL
```
https://auth.atlassian.com/authorize?
  audience=api.atlassian.com&
  client_id={CLIENT_ID}&
  scope={SCOPES}&
  redirect_uri={CALLBACK_URL}&
  state={STATE}&
  response_type=code&
  prompt=consent
```

### Token Exchange
```bash
POST https://auth.atlassian.com/oauth/token
Content-Type: application/json

{
  "grant_type": "authorization_code",
  "client_id": "{CLIENT_ID}",
  "client_secret": "{CLIENT_SECRET}",
  "code": "{AUTHORIZATION_CODE}",
  "redirect_uri": "{CALLBACK_URL}"
}
```

### Token Refresh
```bash
POST https://auth.atlassian.com/oauth/token
Content-Type: application/json

{
  "grant_type": "refresh_token",
  "client_id": "{CLIENT_ID}",
  "client_secret": "{CLIENT_SECRET}",
  "refresh_token": "{REFRESH_TOKEN}"
}
```

---

## Troubleshooting

### OAuth callback not working

**Error:** "Invalid redirect_uri"

**Fix:** Verify callback URL matches exactly:
```
https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/jira
```

### Token expired

**Error:** "401 Unauthorized"

**Fix:** Tokens auto-refresh. If issues persist:
1. Check `token_expires_at` in database
2. Manually refresh: `curl -X POST https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/refresh/jira?installation_id={ID}`

### Multiple Jira sites

**Issue:** User has access to multiple Jira sites

**Solution:** OAuth flow will prompt user to select site. Store selected site in installation metadata.

### Insufficient permissions

**Error:** "403 Forbidden" when accessing Jira API

**Fix:**
1. Check granted scopes in **Permissions**
2. User must have appropriate Jira permissions
3. Re-authorize to grant new scopes

### Webhook configuration (for events)

If you need Jira webhooks:

1. Go to your Jira site
2. Settings → System → **WebHooks**
3. Click **Create a WebHook**
4. Configure:
   - **Name:** `Agent Bot Webhook`
   - **Status:** Enabled
   - **URL:** `https://unabating-unoverdrawn-veronique.ngrok-free.dev/webhooks/jira`
   - **Events:** Select issue events
   - **JQL Filter:** (optional) `labels = "AI-Fix"`
5. Click **Create**

---

## Production Deployment

When deploying to production:

1. **Update callback URL** in Atlassian console:
   ```
   https://oauth.yourdomain.com/oauth/callback/jira
   ```

2. **Update webhook URL** in Jira site:
   ```
   https://oauth.yourdomain.com/webhooks/jira
   ```

3. **Update .env:**
   ```bash
   BASE_URL=https://oauth.yourdomain.com
   ```

4. **Submit for marketplace** (optional):
   - Complete distribution settings
   - Add app listing details
   - Submit for review
   - Once approved, publish to Atlassian Marketplace

---

## Jira Cloud vs Server/Data Center

### Jira Cloud (Recommended)

- ✅ OAuth 2.0 (3LO) supported
- ✅ Automatic token refresh
- ✅ No VPN required
- ✅ REST API v3

**Setup:** Follow this guide

### Jira Server/Data Center

- ⚠️ Uses OAuth 1.0a (different flow)
- ⚠️ Requires RSA key pairs
- ⚠️ More complex setup
- ⚠️ REST API v2

**Setup:** Contact Jira admin for OAuth 1.0a configuration

---

## API Usage Examples

### Create Issue

```bash
curl -X POST https://unabating-unoverdrawn-veronique.ngrok-free.dev/api/jira/issues \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "your-site-id",
    "project": "PROJ",
    "summary": "Bug: Login page not loading",
    "description": "Users report 500 error on login",
    "issue_type": "Bug",
    "labels": ["AI-Fix"]
  }'
```

### Update Issue

```bash
curl -X PATCH https://unabating-unoverdrawn-veronique.ngrok-free.dev/api/jira/issues/PROJ-123 \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "your-site-id",
    "status": "In Progress",
    "assignee": "agent-bot"
  }'
```

### Add Comment

```bash
curl -X POST https://unabating-unoverdrawn-veronique.ngrok-free.dev/api/jira/issues/PROJ-123/comments \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "your-site-id",
    "body": "Working on this issue. ETA: 2 hours."
  }'
```

---

## Next Steps

- [ ] Test creating and updating Jira issues
- [ ] Configure webhooks for issue events
- [ ] Set up JQL filters for AI-Fix label
- [ ] Test full integration with agent-engine
