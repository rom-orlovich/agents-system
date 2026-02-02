# GitHub App Setup

> **Note:** This system uses **GitHub App** (not OAuth App) for better permissions and webhook support.

## Step 1: Create GitHub App

Go to https://github.com/settings/apps/new and fill in:

| Field | Value |
|-------|-------|
| **GitHub App name** | `agent-bot-oauth` (or any unique name) |
| **Homepage URL** | `https://unabating-unoverdrawn-veronique.ngrok-free.dev` |
| **Callback URL** | `https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/github` |
| **Webhook URL** | `https://unabating-unoverdrawn-veronique.ngrok-free.dev/webhooks/github` |
| **Webhook secret** | Generate: `openssl rand -hex 32` |

**Permissions:**
- Repository: Contents (R/W), Pull requests (R/W), Issues (R/W), Metadata (R)
- Organization: Members (R)

**Events:**
- ☑️ Push, Pull request, Issues, Issue comment

**Install:**
- Select "Any account"

Click **Create GitHub App**.

## Step 2: Get Credentials

After creation, on your app's settings page:

1. **App ID** - Note this (shown at top)
2. **Client ID** - Copy it (starts with `Iv1.`)
3. **Client Secret** - Click "Generate a new client secret" → Copy it
4. **Private Key** - Scroll to "Private keys" → "Generate a private key" → Download `.pem` file

## Step 3: Update .env

Convert the `.pem` file to `.env` format:

```bash
cat ~/Downloads/agent-bot-oauth.*.private-key.pem | \
  awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}'
```

Copy the output and update `/Users/romo/projects/agents-prod/agent-bot/oauth-service/.env`:

```bash
GITHUB_APP_ID=123456                      # From step 2.1
GITHUB_APP_NAME=agent-bot-oauth           # The name you chose
GITHUB_CLIENT_ID=Iv1.xxxxxxxxxxxxx        # From step 2.2
GITHUB_CLIENT_SECRET=your_secret_here     # From step 2.3
GITHUB_WEBHOOK_SECRET=your_webhook_secret # From step 1
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAI...\n-----END RSA PRIVATE KEY-----"  # Output from command above
```

**Important:** Keep quotes around `GITHUB_PRIVATE_KEY`, and keep the `\n` characters (they're correct).

## Step 4: Restart Service

```bash
cd /Users/romo/projects/agents-prod/agent-bot
docker-compose restart oauth-service
```

## Step 5: Test Installation

**Option A - Via web UI:**
```bash
open https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/install/github
```

**Option B - Via GitHub settings:**
1. Go to https://github.com/settings/apps/agent-bot-oauth
2. Click **Install App** (left sidebar)
3. Select your organization/account
4. Choose repositories → Click **Install**

**Verify it worked:**
```bash
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/installations | jq
```

Should return:
```json
[{
  "platform": "github",
  "external_org_name": "your-org",
  "status": "ACTIVE"
}]
```

---

## Troubleshooting

**Getting a 404 error?** See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md#github-404-error---page-not-found)

**Common issues:**
- Private key not set → Run step 3 again
- ngrok not running → `cd oauth-service && ./start-ngrok.sh`
- Service not running → `docker-compose up -d oauth-service`

**Debug logs:**
```bash
docker-compose logs -f oauth-service
```

---

## Production Checklist

- [ ] Update URLs in GitHub App to `https://oauth.yourdomain.com`
- [ ] Set `BASE_URL=https://oauth.yourdomain.com` in .env
- [ ] Move secrets to AWS Secrets Manager / Vault
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Set up monitoring and alerts

---

## Next Steps

- Set up [Slack OAuth](./SLACK-SETUP.md)
- Set up [Jira OAuth](./JIRA-SETUP.md)
- Configure webhook handlers in agent-engine
