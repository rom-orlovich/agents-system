# OAuth Setup for Claude Code CLI in Docker

This guide explains how to use your Claude Pro/Team subscription (OAuth) to run Claude Code CLI headlessly in Docker containers, without needing a separate API key.

## Overview

Claude Code CLI supports two authentication methods:
1. **API Key** (`ANTHROPIC_API_KEY`) - Pay-per-use from console.anthropic.com
2. **OAuth** (Claude Pro/Team subscription) - Use your existing subscription

This guide focuses on using **OAuth credentials** for headless Docker deployments.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  Local Machine (one-time setup)                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  $ claude login                                          │   │
│  │  → Creates ~/.claude/.credentials.json                   │   │
│  │  → Contains OAuth accessToken & refreshToken             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Docker Container (headless)                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Mount: .credentials.json → /root/.claude/               │   │
│  │  Claude CLI reads OAuth token automatically              │   │
│  │  No API key required!                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Local Development Setup

### Step 1: Login on Host Machine

```bash
# Run interactive login (one-time)
claude login

# This creates ~/.claude/.credentials.json with your OAuth tokens
```

### Step 2: Verify Credentials File Exists

```bash
cat ~/.claude/.credentials.json
# Should show: {"claudeAiOauth":{"accessToken":"sk-ant-oat01-...","refreshToken":"sk-ant-ort01-...",...}}
```

### Step 3: Configure Docker Compose

Mount **only** the credentials file, not the entire `~/.claude` directory:

```yaml
# docker-compose.yml
services:
  your-agent:
    volumes:
      # Mount only credentials file (OAuth) - NOT entire ~/.claude directory
      # The full directory mount causes path issues with symlinks
      - ~/.claude/.credentials.json:/root/.claude/.credentials.json:ro
      - ~/.claude/mcp.json:/root/.claude/mcp.json:ro  # Optional: for MCP servers
```

> **Important:** Do NOT mount the entire `~/.claude` directory. It contains symlinks and paths that reference your host machine and will break in the container.

### Step 4: Start Services

```bash
make up
# or
cd infrastructure/docker && docker-compose up -d
```

### Step 5: Verify It Works

```bash
docker exec <container-name> claude -p "Say hello" --max-turns 1
# Should return a response from Claude
```

## Cloud/Production Deployment

For deploying to cloud machines (AWS, GCP, Azure, etc.), you need to securely distribute the OAuth credentials.

### Option 1: Secrets Manager (Recommended)

Store credentials in your cloud provider's secrets manager and inject at runtime.

#### AWS Secrets Manager

```bash
# Store credentials
aws secretsmanager create-secret \
  --name claude-oauth-credentials \
  --secret-string "$(cat ~/.claude/.credentials.json)"

# In your deployment script or entrypoint:
aws secretsmanager get-secret-value \
  --secret-id claude-oauth-credentials \
  --query SecretString \
  --output text > /root/.claude/.credentials.json
```

#### Docker Compose with AWS Secrets

```yaml
services:
  planning-agent:
    environment:
      - AWS_REGION=us-east-1
    entrypoint: |
      sh -c '
        mkdir -p /root/.claude
        aws secretsmanager get-secret-value \
          --secret-id claude-oauth-credentials \
          --query SecretString \
          --output text > /root/.claude/.credentials.json
        exec python worker.py
      '
```

#### GCP Secret Manager

```bash
# Store credentials
gcloud secrets create claude-oauth-credentials \
  --data-file=~/.claude/.credentials.json

# Retrieve in container
gcloud secrets versions access latest \
  --secret=claude-oauth-credentials > /root/.claude/.credentials.json
```

#### Azure Key Vault

```bash
# Store credentials
az keyvault secret set \
  --vault-name your-vault \
  --name claude-oauth-credentials \
  --file ~/.claude/.credentials.json

# Retrieve in container
az keyvault secret show \
  --vault-name your-vault \
  --name claude-oauth-credentials \
  --query value -o tsv > /root/.claude/.credentials.json
```

### Option 2: Kubernetes Secrets

```yaml
# Create secret from credentials file
# kubectl create secret generic claude-credentials --from-file=credentials.json=~/.claude/.credentials.json

apiVersion: v1
kind: Pod
metadata:
  name: planning-agent
spec:
  containers:
    - name: agent
      image: your-agent-image
      volumeMounts:
        - name: claude-credentials
          mountPath: /root/.claude/.credentials.json
          subPath: credentials.json
          readOnly: true
  volumes:
    - name: claude-credentials
      secret:
        secretName: claude-credentials
```

### Option 3: Environment Variable

For simpler setups, you can base64 encode the credentials:

```bash
# Encode credentials
export CLAUDE_CREDENTIALS_B64=$(base64 < ~/.claude/.credentials.json)

# In container entrypoint
echo "$CLAUDE_CREDENTIALS_B64" | base64 -d > /root/.claude/.credentials.json
```

```yaml
# docker-compose.yml
services:
  planning-agent:
    environment:
      - CLAUDE_CREDENTIALS_B64=${CLAUDE_CREDENTIALS_B64}
    entrypoint: |
      sh -c '
        mkdir -p /root/.claude
        echo "$CLAUDE_CREDENTIALS_B64" | base64 -d > /root/.claude/.credentials.json
        exec python worker.py
      '
```

### Option 4: Shared Volume (Multi-Machine)

For multiple machines in the same network, use a shared volume:

```yaml
# NFS or EFS mount
services:
  planning-agent:
    volumes:
      - nfs-credentials:/root/.claude:ro

volumes:
  nfs-credentials:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfs-server.local,ro
      device: ":/claude-credentials"
```

## Token Refresh

OAuth tokens expire periodically. The credentials file contains:

```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-ort01-...",
    "expiresAt": 1768838897263,
    "subscriptionType": "pro"
  }
}
```

### Automatic Refresh

Claude Code CLI automatically refreshes tokens when needed using the `refreshToken`. The refreshed credentials are written back to the file.

> **Note:** For read-only mounts (`:ro`), the container cannot write refreshed tokens. If tokens expire, you'll need to re-run `claude login` on a machine with write access and redistribute the credentials.

### Manual Token Refresh

If tokens expire in production:

1. Run `claude login` on any machine
2. Update the secret/credential store with new credentials
3. Restart containers to pick up new credentials

### Token Expiration Monitoring

Add monitoring to detect token expiration:

```python
import json
import time

def check_token_expiry():
    with open('/root/.claude/.credentials.json') as f:
        creds = json.load(f)

    expires_at = creds['claudeAiOauth']['expiresAt'] / 1000  # Convert to seconds
    days_until_expiry = (expires_at - time.time()) / 86400

    if days_until_expiry < 7:
        alert(f"Claude OAuth token expires in {days_until_expiry:.1f} days!")
```

## Troubleshooting

### "OAuth token check" but no output

**Cause:** Entire `~/.claude` directory mounted instead of just credentials file.

**Fix:** Mount only the credentials file:
```yaml
volumes:
  - ~/.claude/.credentials.json:/root/.claude/.credentials.json:ro
```

### "Authentication required" error

**Cause:** Credentials file not found or invalid.

**Fix:**
1. Check file exists: `ls -la /root/.claude/.credentials.json`
2. Check file contents: `cat /root/.claude/.credentials.json`
3. Re-run `claude login` if needed

### Token expired

**Cause:** OAuth token has expired and couldn't be refreshed.

**Fix:**
1. Run `claude login` on host machine
2. Update credentials in secrets manager
3. Restart containers

### Permission denied

**Cause:** Credentials file has wrong permissions.

**Fix:** Ensure file is readable:
```bash
chmod 600 ~/.claude/.credentials.json
```

## Security Considerations

1. **Never commit credentials to git** - Add `.credentials.json` to `.gitignore`
2. **Use secrets managers in production** - Don't store credentials in plain text
3. **Rotate credentials regularly** - Re-run `claude login` periodically
4. **Limit access** - Only mount credentials to containers that need them
5. **Use read-only mounts** - Prevent containers from modifying credentials

## Comparison: OAuth vs API Key

| Feature | OAuth (Subscription) | API Key |
|---------|---------------------|---------|
| Cost | Included in Pro/Team subscription | Pay-per-use |
| Setup | `claude login` (interactive) | Get key from console |
| Token refresh | Automatic (with write access) | N/A (keys don't expire) |
| Rate limits | Subscription tier limits | API tier limits |
| Best for | Dev/small teams with subscription | Production/high-volume |

## Quick Reference

```bash
# Local setup
claude login                                    # One-time interactive login
cat ~/.claude/.credentials.json                 # Verify credentials

# Docker mount (docker-compose.yml)
volumes:
  - ~/.claude/.credentials.json:/root/.claude/.credentials.json:ro

# Test in container
docker exec <container> claude -p "Hello" --max-turns 1

# Cloud deployment
aws secretsmanager create-secret --name claude-oauth --secret-string "$(cat ~/.claude/.credentials.json)"
```
