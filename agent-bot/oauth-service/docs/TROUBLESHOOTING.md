# OAuth Service Troubleshooting

## GitHub 404 Error - "Page not found"

**Symptom:** Clicking "Install GitHub App" shows a 404 error page.

**Cause:** Missing or invalid GitHub App private key in `.env` file.

### Quick Fix

1. **Generate private key** (if you haven't already):
   - Go to https://github.com/settings/apps/agent-bot-oauth
   - Scroll to **Private keys** → Click **Generate a private key**
   - A `.pem` file will download (e.g., `agent-bot-oauth.2024-01-01.private-key.pem`)

2. **Convert `.pem` to `.env` format:**
   ```bash
   cat ~/Downloads/agent-bot-oauth.*.private-key.pem | \
     awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}'
   ```

3. **Update `.env` file:**
   ```bash
   # Replace this line in /Users/romo/projects/agents-prod/agent-bot/oauth-service/.env
   GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
   ```
   Paste the output from step 2 (keep the quotes, `\n` newlines are correct).

4. **Restart service:**
   ```bash
   cd /Users/romo/projects/agents-prod/agent-bot
   docker-compose restart oauth-service
   ```

5. **Test again:**
   ```bash
   open https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/install/github
   ```

---

## Slack OAuth Errors

**Symptom:** "Invalid client_id" or redirect errors.

**Fix:**
1. Go to https://api.slack.com/apps → Your app → **OAuth & Permissions**
2. Update **Redirect URLs** to:
   ```
   https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/slack
   ```
3. Copy **Client ID** and **Client Secret** to `.env`:
   ```bash
   SLACK_CLIENT_ID=123456789.123456789
   SLACK_CLIENT_SECRET=your-secret-here
   ```
4. Copy **Signing Secret** from **Basic Information**:
   ```bash
   SLACK_SIGNING_SECRET=your-signing-secret
   ```
5. Restart: `docker-compose restart oauth-service`

---

## Jira OAuth Errors

**Symptom:** "callback_uri_mismatch" error.

**Fix:**
1. Go to https://developer.atlassian.com/console/myapps/
2. Select your app → **Authorization** → **OAuth 2.0 (3LO)**
3. Update **Callback URL**:
   ```
   https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/jira
   ```
4. Copy **Client ID** and **Secret** to `.env`:
   ```bash
   JIRA_CLIENT_ID=your-client-id
   JIRA_CLIENT_SECRET=your-secret
   ```
5. Restart: `docker-compose restart oauth-service`

---

## ngrok Not Working

**Symptom:** "Unable to connect" or timeout errors.

**Check if ngrok is running:**
```bash
ps aux | grep ngrok
```

**Restart ngrok:**
```bash
cd /Users/romo/projects/agents-prod/agent-bot/oauth-service
./start-ngrok.sh
```

**Verify ngrok URL matches `.env`:**
```bash
# Check what ngrok says
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'

# Should match:
# https://unabating-unoverdrawn-veronique.ngrok-free.dev
```

---

## Database Connection Errors

**Symptom:** "Connection refused" or "database does not exist".

**Check database is running:**
```bash
docker-compose ps postgres
```

**Restart database:**
```bash
docker-compose restart postgres
```

**Run migrations:**
```bash
cd /Users/romo/projects/agents-prod/agent-bot
make db-upgrade
```

---

## Quick Health Checks

**Check all services:**
```bash
# OAuth service
curl http://localhost:8010/health

# Database
docker-compose exec postgres pg_isready

# ngrok
curl http://localhost:4040/api/tunnels
```

**View logs:**
```bash
# OAuth service logs
docker-compose logs -f oauth-service

# All services
docker-compose logs -f
```

**Restart everything:**
```bash
cd /Users/romo/projects/agents-prod/agent-bot
docker-compose restart
```

---

## Common .env Mistakes

❌ **Wrong:**
```bash
# Missing quotes
GITHUB_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----...

# Wrong newline format
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
actual newlines here
-----END RSA PRIVATE KEY-----"

# Extra spaces
GITHUB_CLIENT_ID = Ov23li4BvabOA0K0teML
```

✅ **Correct:**
```bash
# Quotes + \n for newlines
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAI...\n-----END RSA PRIVATE KEY-----"

# No spaces around =
GITHUB_CLIENT_ID=Ov23li4BvabOA0K0teML
GITHUB_CLIENT_SECRET=e4628eb0c48086207814215f04173672bfefba5d
```

---

## Test OAuth Flow End-to-End

1. **Start all services:**
   ```bash
   cd /Users/romo/projects/agents-prod/agent-bot
   docker-compose up -d
   ```

2. **Check health:**
   ```bash
   curl http://localhost:8010/health
   # Should return: {"status": "healthy"}
   ```

3. **Test GitHub OAuth:**
   ```bash
   open https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/install/github
   ```
   - Should redirect to GitHub App installation page
   - Click **Install** → Select repo → **Install**
   - Should redirect back to success page

4. **Verify installation:**
   ```bash
   curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/installations | jq
   ```
   - Should show your GitHub installation with status: "ACTIVE"

---

## Still Not Working?

1. **Enable debug logs:**
   ```bash
   # Add to .env
   LOG_LEVEL=DEBUG
   ```

2. **Restart with logs:**
   ```bash
   docker-compose restart oauth-service
   docker-compose logs -f oauth-service
   ```

3. **Check the exact error:**
   - Look for `ERROR` or `CRITICAL` in logs
   - Check GitHub App settings match `.env` exactly
   - Verify ngrok domain hasn't changed

4. **Reset everything:**
   ```bash
   cd /Users/romo/projects/agents-prod/agent-bot
   docker-compose down
   docker-compose up -d
   make db-upgrade
   ```
