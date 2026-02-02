# OAuth Service Setup Guide

## Overview

This guide covers setting up OAuth integrations for GitHub, Slack, and Jira.

**📚 Detailed Setup Guides:**

- [GitHub OAuth Setup](./GITHUB-SETUP.md) - OAuth App or GitHub App configuration
- [Slack OAuth Setup](./SLACK-SETUP.md) - Slack app and permissions
- [Jira OAuth Setup](./JIRA-SETUP.md) - Atlassian OAuth 2.0 (3LO)

---

## Quick Start

### 1. Setup ngrok (Required for local development)

```bash
cd oauth-service

# Start ngrok with fixed domain
./start-ngrok.sh
```

Your OAuth callbacks will be:

- GitHub: `https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/github`
- Slack: `https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/slack`
- Jira: `https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/jira`

### 2. Configure OAuth Apps

Follow the detailed guides:

1. [GitHub Setup](./GITHUB-SETUP.md) - Get GitHub credentials
2. [Slack Setup](./SLACK-SETUP.md) - Get Slack credentials
3. [Jira Setup](./JIRA-SETUP.md) - Get Jira credentials

### 3. Generate Secrets

```bash
# Slack state secret
python3 -c "import secrets; print('SLACK_STATE_SECRET=' + secrets.token_urlsafe(32))"

# Token encryption key
python3 -c "from cryptography.fernet import Fernet; print('TOKEN_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

### 4. Update .env

Your `.env` file should look like:

```bash
# OAuth Service Configuration
PORT=8010
BASE_URL=https://unabating-unoverdrawn-veronique.ngrok-free.dev
NGROK_DOMAIN=unabating-unoverdrawn-veronique.ngrok-free.dev

# Database
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system

# GitHub App Credentials
GITHUB_APP_ID=123456
GITHUB_APP_NAME=agent-bot-oauth
GITHUB_CLIENT_ID=Iv1.xxxxxxxxxxxxx
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Slack App Credentials
SLACK_CLIENT_ID=123456789.123456789
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_SIGNING_SECRET=your_slack_signing_secret
SLACK_STATE_SECRET=generated_state_secret

# Jira OAuth Credentials
JIRA_CLIENT_ID=your_jira_client_id
JIRA_CLIENT_SECRET=your_jira_client_secret

# Token Encryption
TOKEN_ENCRYPTION_KEY=generated_fernet_key
```

### 5. Start Service

```bash
# From agent-bot directory
docker-compose up -d oauth-service postgres

# Check health
curl http://localhost:8010/health
```

---

## Testing

### Test OAuth Flows

```bash
# GitHub
open https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/install/github

# Slack
open https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/install/slack

# Jira
open https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/install/jira
```

### Verify Installations

```bash
# List all installations
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/installations

# List by platform
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/installations?platform=github
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/installations?platform=slack
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/installations?platform=jira
```

### Get Tokens

```bash
# GitHub token
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/token/github?org_id=your-org

# Slack token
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/token/slack?org_id=T01234567

# Jira token
curl https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/token/jira?org_id=your-site-id
```

---

## Troubleshooting

### ngrok not working

**Error:** Connection timeout or refused

**Fix:**

```bash
# Check if ngrok is running
ps aux | grep ngrok

# Start ngrok
cd oauth-service && ./start-ngrok.sh
```

### Service not starting

**Error:** oauth-service container unhealthy

**Fix:**

```bash
# Check logs
docker-compose logs oauth-service

# Common issues:
# - Missing .env variables
# - Database not running
# - Port 8010 already in use

# Restart service
docker-compose restart oauth-service
```

### Callback URL mismatch

**Error:** "redirect_uri does not match"

**Fix:** Ensure callback URLs in OAuth app settings match exactly:

- `https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/github`
- `https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/slack`
- `https://unabating-unoverdrawn-veronique.ngrok-free.dev/oauth/callback/jira`

### Database connection failed

**Error:** "could not connect to database"

**Fix:**

```bash
# Start postgres
docker-compose up -d postgres

# Check if running
docker-compose ps postgres

# Check logs
docker-compose logs postgres
```

---

## Production Deployment

See detailed guides for production setup:

- [GitHub Production Setup](./GITHUB-SETUP.md#production-deployment)
- [Slack Production Setup](./SLACK-SETUP.md#production-deployment)
- [Jira Production Setup](./JIRA-SETUP.md#production-deployment)

## Production Deployment

### Infrastructure

**Kubernetes:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oauth-service
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: oauth-service
          image: your-registry/oauth-service:latest
          ports:
            - containerPort: 8010
          envFrom:
            - secretRef:
                name: oauth-secrets
          env:
            - name: BASE_URL
              value: "https://oauth.yourdomain.com"
          livenessProbe:
            httpGet:
              path: /health
              port: 8010
```

**Docker Compose:**

```yaml
services:
  oauth-service:
    build: ./oauth-service
    restart: always
    environment:
      - BASE_URL=https://oauth.yourdomain.com
    env_file:
      - .env.production
    deploy:
      replicas: 2
```

### Configuration

**Secrets Management:**

```bash
# AWS Secrets Manager
aws secretsmanager create-secret --name oauth-service/production --secret-string file://secrets.json

# Kubernetes
kubectl create secret generic oauth-secrets --from-literal=GITHUB_CLIENT_ID=xxx
```

**OAuth App Callbacks (Production):**

- GitHub: `https://oauth.yourdomain.com/oauth/callback/github`
- Slack: `https://oauth.yourdomain.com/oauth/callback/slack`
- Jira: `https://oauth.yourdomain.com/oauth/callback/jira`

**Environment Variables:**

```bash
BASE_URL=https://oauth.yourdomain.com
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/agent_system
# ... OAuth credentials from secrets manager
```

### Security & Monitoring

- [ ] HTTPS (TLS 1.2+)
- [ ] Secrets in secrets manager (not code)
- [ ] Rate limiting (100 req/min per IP)
- [ ] Health checks: `curl https://oauth.yourdomain.com/health`
- [ ] Monitoring alerts for service down/errors

### Deployment

```bash
docker build -t your-registry/oauth-service:v1.0.0 ./oauth-service
docker push your-registry/oauth-service:v1.0.0
kubectl set image deployment/oauth-service oauth-service=your-registry/oauth-service:v1.0.0
```

See [README.md](../README.md) for API documentation.
