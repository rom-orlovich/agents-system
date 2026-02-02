# Environment Variable Mapping Analysis

## Overview

This document maps all environment variables across agent-bot services, identifies redundancies, and provides a consolidated configuration strategy.

---

## Current State: All .env.example Files

### 1. Root `.env.example` (agent-bot/.env.example)

| Variable | Value | Description |
|----------|-------|-------------|
| CLI_PROVIDER | claude | CLI provider selection |
| MAX_CONCURRENT_TASKS | 5 | Task concurrency |
| TASK_TIMEOUT_SECONDS | 3600 | Task timeout |
| POSTGRES_PASSWORD | agent | DB password |
| POSTGRES_USER | agent | DB user |
| POSTGRES_DB | agent_system | DB name |
| GITHUB_TOKEN | ghp_xxx | GitHub API token |
| JIRA_URL | https://company.atlassian.net | Jira base URL |
| JIRA_EMAIL | agent@company.com | Jira email |
| JIRA_API_TOKEN | xxx | Jira API token |
| SLACK_BOT_TOKEN | xoxb-xxx | Slack bot token |
| SENTRY_DSN | https://xxx@sentry.io/xxx | Sentry DSN |
| SENTRY_AUTH_TOKEN | xxx | Sentry auth token |
| SENTRY_ORG_SLUG | your-org-slug | Sentry org |
| GITHUB_WEBHOOK_SECRET | xxx | GitHub webhook secret |
| JIRA_WEBHOOK_SECRET | xxx | Jira webhook secret |
| SLACK_SIGNING_SECRET | xxx | Slack signing secret |
| SENTRY_CLIENT_SECRET | xxx | Sentry client secret |
| ANTHROPIC_API_KEY | sk-ant-xxx | Anthropic API key |
| CURSOR_API_KEY | cur_xxx | Cursor API key |
| CLAUDE_MODEL_COMPLEX | opus | Complex task model |
| CLAUDE_MODEL_EXECUTION | sonnet | Execution model |
| CURSOR_MODEL_COMPLEX | claude-sonnet-4.5 | Cursor complex model |
| CURSOR_MODEL_EXECUTION | composer-1 | Cursor execution model |
| BASE_URL | https://yourdomain.com | OAuth base URL |
| GITHUB_APP_ID | 123456 | GitHub App ID |
| GITHUB_APP_NAME | my-agent-bot | GitHub App name |
| GITHUB_CLIENT_ID | Iv1.abc123 | GitHub OAuth client |
| GITHUB_CLIENT_SECRET | xxx | GitHub OAuth secret |
| GITHUB_PRIVATE_KEY | "-----BEGIN..." | GitHub App key |
| SLACK_CLIENT_ID | 123456789.xxx | Slack OAuth client |
| SLACK_CLIENT_SECRET | xxx | Slack OAuth secret |
| SLACK_STATE_SECRET | xxx | Slack state secret |
| JIRA_CLIENT_ID | xxx | Jira OAuth client |
| JIRA_CLIENT_SECRET | xxx | Jira OAuth secret |
| TOKEN_ENCRYPTION_KEY | xxx | Fernet encryption key |
| CLAUDE_CODE_ENABLE_TASKS | true | Enable tasks feature |
| LOG_LEVEL | INFO | Logging level |

---

### 2. Agent Engine `.env.example`

| Variable | Value | Redundant? |
|----------|-------|------------|
| PORT | 8080 | No - service-specific |
| CLI_PROVIDER | claude | **YES** - in root |
| MAX_CONCURRENT_TASKS | 5 | **YES** - in root |
| TASK_TIMEOUT_SECONDS | 3600 | **YES** - in root |
| REDIS_URL | redis://redis:6379/0 | No - computed |
| DATABASE_URL | postgresql+asyncpg://... | No - computed |
| KNOWLEDGE_GRAPH_URL | http://knowledge-graph:4000 | No - internal |
| ANTHROPIC_API_KEY | sk-ant-xxx | **YES** - in root |
| CURSOR_API_KEY | cur_xxx | **YES** - in root |
| CLAUDE_MODEL_COMPLEX | opus | **YES** - in root |
| CLAUDE_MODEL_EXECUTION | sonnet | **YES** - in root |
| CURSOR_MODEL_COMPLEX | claude-sonnet-4.5 | **YES** - in root |
| CURSOR_MODEL_EXECUTION | composer-1 | **YES** - in root |
| CLAUDE_CODE_ENABLE_TASKS | true | **YES** - in root |
| LOG_LEVEL | INFO | **YES** - in root |

---

### 3. API Gateway `.env.example`

| Variable | Value | Redundant? |
|----------|-------|------------|
| PORT | 8000 | No - service-specific |
| REDIS_HOST | redis | No - internal |
| REDIS_PORT | 6379 | No - internal |
| REDIS_DB | 0 | No - internal |
| GITHUB_WEBHOOK_SECRET | xxx | **YES** - in root |
| JIRA_WEBHOOK_SECRET | xxx | **YES** - in root |
| SLACK_SIGNING_SECRET | xxx | **YES** - in root |
| SENTRY_CLIENT_SECRET | xxx | **YES** - in root |
| LOG_LEVEL | INFO | **YES** - in root |
| KNOWLEDGE_GRAPH_URL | http://knowledge-graph:4000 | No - internal |
| AGENT_ENGINE_URL | http://agent-engine:8080 | No - internal |

---

### 4. Dashboard API `.env.example`

| Variable | Value | Redundant? |
|----------|-------|------------|
| REDIS_URL | redis://redis:6379/0 | No - computed |
| DATABASE_URL | postgresql+asyncpg://... | No - computed |
| AGENT_ENGINE_URL | http://agent-engine:8080 | No - internal |
| CORS_ORIGINS | http://localhost:3005 | No - service-specific |
| LOG_LEVEL | INFO | **YES** - in root |

---

### 5. OAuth Service `.env.example`

| Variable | Value | Redundant? |
|----------|-------|------------|
| PORT | 8010 | No - service-specific |
| BASE_URL | https://yourdomain.com | **YES** - in root |
| DATABASE_URL | postgresql+asyncpg://... | No - computed |
| GITHUB_APP_ID | 123456 | **YES** - in root |
| GITHUB_APP_NAME | my-agent-bot | **YES** - in root |
| GITHUB_CLIENT_ID | Iv1.abc123 | **YES** - in root |
| GITHUB_CLIENT_SECRET | xxx | **YES** - in root |
| GITHUB_PRIVATE_KEY | "-----BEGIN..." | **YES** - in root |
| GITHUB_WEBHOOK_SECRET | xxx | **YES** - in root |
| SLACK_CLIENT_ID | 123456789.xxx | **YES** - in root |
| SLACK_CLIENT_SECRET | xxx | **YES** - in root |
| SLACK_SIGNING_SECRET | xxx | **YES** - in root |
| SLACK_STATE_SECRET | xxx | **YES** - in root |
| JIRA_CLIENT_ID | xxx | **YES** - in root |
| JIRA_CLIENT_SECRET | xxx | **YES** - in root |
| TOKEN_ENCRYPTION_KEY | xxx | **YES** - in root |

---

### 6. GitHub API `.env.example`

| Variable | Value | Redundant? |
|----------|-------|------------|
| PORT | 3001 | No - service-specific |
| GITHUB_TOKEN | ghp_xxx | **YES** - in root |
| GITHUB_API_BASE_URL | https://api.github.com | No - constant |
| LOG_LEVEL | INFO | **YES** - in root |
| REQUEST_TIMEOUT | 30 | No - service-specific |

---

### 7. Jira API `.env.example`

| Variable | Value | Redundant? |
|----------|-------|------------|
| PORT | 3002 | No - service-specific |
| JIRA_URL | https://xxx.atlassian.net | **YES** - in root |
| JIRA_EMAIL | xxx@example.com | **YES** - in root |
| JIRA_API_TOKEN | xxx | **YES** - in root |
| LOG_LEVEL | INFO | **YES** - in root |
| REQUEST_TIMEOUT | 30 | No - service-specific |

---

### 8. Slack API `.env.example`

| Variable | Value | Redundant? |
|----------|-------|------------|
| PORT | 3003 | No - service-specific |
| SLACK_BOT_TOKEN | xoxb-xxx | **YES** - in root |
| SLACK_API_BASE_URL | https://slack.com/api | No - constant |
| LOG_LEVEL | INFO | **YES** - in root |
| REQUEST_TIMEOUT | 30 | No - service-specific |

---

### 9. Sentry API `.env.example`

| Variable | Value | Redundant? |
|----------|-------|------------|
| PORT | 3004 | No - service-specific |
| SENTRY_AUTH_TOKEN | xxx | **YES** - in root |
| SENTRY_ORG_SLUG | xxx | **YES** - in root |
| SENTRY_API_BASE_URL | https://sentry.io/api/0 | No - constant |
| LOG_LEVEL | INFO | **YES** - in root |
| REQUEST_TIMEOUT | 30 | No - service-specific |

---

### 10. MCP Servers `.env.example` (jira-mcp, slack-mcp, sentry-mcp)

| Variable | Value | Redundant? |
|----------|-------|------------|
| PORT | 9002/9003/9004 | No - service-specific |
| *_API_URL | http://*-api:300x | No - internal |
| REQUEST_TIMEOUT | 30 | No - service-specific |

---

## Redundancy Summary

### Variables Duplicated Across Services

| Variable | Root | agent-engine | api-gateway | oauth-service | github-api | jira-api | slack-api | sentry-api |
|----------|------|-------------|-------------|---------------|------------|----------|----------|------------|
| LOG_LEVEL | ✅ | ✅ | ✅ | - | ✅ | ✅ | ✅ | ✅ |
| GITHUB_TOKEN | ✅ | - | - | - | ✅ | - | - | - |
| JIRA_URL | ✅ | - | - | - | - | ✅ | - | - |
| JIRA_EMAIL | ✅ | - | - | - | - | ✅ | - | - |
| JIRA_API_TOKEN | ✅ | - | - | - | - | ✅ | - | - |
| SLACK_BOT_TOKEN | ✅ | - | - | - | - | - | ✅ | - |
| SENTRY_AUTH_TOKEN | ✅ | - | - | - | - | - | - | ✅ |
| SENTRY_ORG_SLUG | ✅ | - | - | - | - | - | - | ✅ |
| GITHUB_WEBHOOK_SECRET | ✅ | - | ✅ | ✅ | - | - | - | - |
| JIRA_WEBHOOK_SECRET | ✅ | - | ✅ | - | - | - | - | - |
| SLACK_SIGNING_SECRET | ✅ | - | ✅ | ✅ | - | - | - | - |
| SENTRY_CLIENT_SECRET | ✅ | - | ✅ | - | - | - | - | - |
| CLI_PROVIDER | ✅ | ✅ | - | - | - | - | - | - |
| MAX_CONCURRENT_TASKS | ✅ | ✅ | - | - | - | - | - | - |
| CLAUDE_MODEL_* | ✅ | ✅ | - | - | - | - | - | - |
| CURSOR_MODEL_* | ✅ | ✅ | - | - | - | - | - | - |
| All OAuth vars | ✅ | - | - | ✅ | - | - | - | - |

---

## Recommended Solution

### Strategy: Single Root `.env` + docker-compose env passthrough

1. **Keep ONE `.env.example`** at root level
2. **Remove service `.env.example` files** that only duplicate root vars
3. **Use docker-compose `env_file`** to pass root `.env` to all services
4. **Keep service-specific configs** as defaults in the service code (ports, internal URLs)

### Files to Keep

| File | Reason |
|------|--------|
| `agent-bot/.env.example` | Single source of truth |

### Files to Delete (After Migration)

| File | Reason |
|------|--------|
| `agent-engine/.env.example` | All vars in root |
| `api-gateway/.env.example` | All vars in root |
| `dashboard-api/.env.example` | Minimal, can use defaults |
| `oauth-service/.env.example` | All vars in root |
| `api-services/github-api/.env.example` | All vars in root |
| `api-services/jira-api/.env.example` | All vars in root |
| `api-services/slack-api/.env.example` | All vars in root |
| `api-services/sentry-api/.env.example` | All vars in root |

### Files to Keep (Internal References Only)

| File | Reason |
|------|--------|
| `mcp-servers/jira-mcp/.env.example` | Internal API URL ref |
| `mcp-servers/slack-mcp/.env.example` | Internal API URL ref |
| `mcp-servers/sentry-mcp/.env.example` | Internal API URL ref |

---

## Consolidated Root `.env.example`

```bash
# ============================================
# AGENT BOT CONFIGURATION
# ============================================
# This is the SINGLE SOURCE OF TRUTH for all environment variables.
# All services read from this file via docker-compose env_file.

# ============================================
# CORE SETTINGS
# ============================================
CLI_PROVIDER=claude              # Options: claude, cursor
MAX_CONCURRENT_TASKS=5           # Concurrent task limit
TASK_TIMEOUT_SECONDS=3600        # Task timeout (1 hour)
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
BASE_URL=https://yourdomain.com  # Public URL for OAuth callbacks

# ============================================
# DATABASE
# ============================================
POSTGRES_USER=agent
POSTGRES_PASSWORD=agent
POSTGRES_DB=agent_system
# Computed URLs (do not change unless custom setup)
# DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
# REDIS_URL=redis://redis:6379/0

# ============================================
# GITHUB
# ============================================
# API Token (for API service)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Webhook Secret (for signature validation)
GITHUB_WEBHOOK_SECRET=your-github-webhook-secret

# GitHub App OAuth (for multi-tenant)
GITHUB_APP_ID=123456
GITHUB_APP_NAME=my-agent-bot
GITHUB_CLIENT_ID=Iv1.abc123
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# ============================================
# JIRA
# ============================================
# API Credentials
JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=agent@company.com
JIRA_API_TOKEN=your-jira-api-token

# Webhook Secret
JIRA_WEBHOOK_SECRET=your-jira-webhook-secret

# OAuth (for multi-tenant)
JIRA_CLIENT_ID=your-jira-client-id
JIRA_CLIENT_SECRET=your-jira-client-secret

# ============================================
# SLACK
# ============================================
# Bot Token (for API service)
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx

# Signing Secret (for webhook validation)
SLACK_SIGNING_SECRET=your-slack-signing-secret

# OAuth (for multi-tenant)
SLACK_CLIENT_ID=123456789.123456789
SLACK_CLIENT_SECRET=your-slack-client-secret
SLACK_STATE_SECRET=random-state-secret-for-oauth

# ============================================
# SENTRY
# ============================================
# Auth Token (for API service)
SENTRY_AUTH_TOKEN=your-sentry-auth-token
SENTRY_ORG_SLUG=your-organization-slug

# DSN (for error tracking)
SENTRY_DSN=https://xxx@sentry.io/xxx

# Client Secret (for webhook validation)
SENTRY_CLIENT_SECRET=your-sentry-client-secret

# ============================================
# LLM PROVIDERS
# ============================================
# Anthropic (Claude CLI)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# Cursor
CURSOR_API_KEY=cur_xxxxxxxxxxxx

# Claude Model Selection (short names)
CLAUDE_MODEL_COMPLEX=opus        # For planning, brain, complex tasks
CLAUDE_MODEL_EXECUTION=sonnet    # For execution, code implementation

# Cursor Model Selection (full names)
CURSOR_MODEL_COMPLEX=claude-sonnet-4.5
CURSOR_MODEL_EXECUTION=composer-1

# ============================================
# SECURITY
# ============================================
# Fernet encryption key for OAuth tokens
# Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=your-fernet-encryption-key

# ============================================
# FEATURE FLAGS
# ============================================
CLAUDE_CODE_ENABLE_TASKS=true
ENABLE_KNOWLEDGE_GRAPH=false

# ============================================
# CHROMADB (Knowledge Graph)
# ============================================
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_COLLECTION=agent_knowledge

# ============================================
# FRONTEND
# ============================================
CORS_ORIGINS=http://localhost:3005,http://localhost:3000
```

---

## docker-compose.yml Changes

```yaml
# Apply to ALL services:
services:
  api-gateway:
    env_file:
      - .env
    environment:
      # Override only if needed
      - PORT=8000

  agent-engine:
    env_file:
      - .env
    environment:
      - PORT=8080
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

  dashboard-api:
    env_file:
      - .env
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - AGENT_ENGINE_URL=http://agent-engine:8080

  oauth-service:
    env_file:
      - .env
    environment:
      - PORT=8010
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

  github-api:
    env_file:
      - .env
    environment:
      - PORT=3001

  jira-api:
    env_file:
      - .env
    environment:
      - PORT=3002

  slack-api:
    env_file:
      - .env
    environment:
      - PORT=3003

  sentry-api:
    env_file:
      - .env
    environment:
      - PORT=3004
```

---

## Migration Steps

1. **Update root `.env.example`** with consolidated variables
2. **Update `docker-compose.yml`** to use `env_file: .env` for all services
3. **Update service code** to use defaults for internal URLs/ports
4. **Test all services** start correctly with only root `.env`
5. **Delete redundant `.env.example` files**
6. **Update documentation**

---

## Validation Script

Create `scripts/env/validate.sh`:

```bash
#!/bin/bash
# Validates that all required environment variables are set

REQUIRED_VARS=(
    "CLI_PROVIDER"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
    "POSTGRES_DB"
    "GITHUB_TOKEN"
    "JIRA_URL"
    "JIRA_EMAIL"
    "JIRA_API_TOKEN"
    "SLACK_BOT_TOKEN"
    "SENTRY_AUTH_TOKEN"
    "TOKEN_ENCRYPTION_KEY"
)

OAUTH_VARS=(
    "GITHUB_APP_ID"
    "GITHUB_CLIENT_ID"
    "GITHUB_CLIENT_SECRET"
    "SLACK_CLIENT_ID"
    "SLACK_CLIENT_SECRET"
    "JIRA_CLIENT_ID"
    "JIRA_CLIENT_SECRET"
)

WEBHOOK_VARS=(
    "GITHUB_WEBHOOK_SECRET"
    "JIRA_WEBHOOK_SECRET"
    "SLACK_SIGNING_SECRET"
)

missing=0

echo "Checking required variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "  ❌ Missing: $var"
        missing=$((missing + 1))
    else
        echo "  ✅ $var"
    fi
done

echo ""
echo "Checking OAuth variables (optional for basic setup)..."
for var in "${OAUTH_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "  ⚠️  Not set: $var"
    else
        echo "  ✅ $var"
    fi
done

echo ""
echo "Checking webhook secrets..."
for var in "${WEBHOOK_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "  ⚠️  Not set: $var"
    else
        echo "  ✅ $var"
    fi
done

if [ $missing -gt 0 ]; then
    echo ""
    echo "❌ Missing $missing required variables. Please update .env"
    exit 1
fi

echo ""
echo "✅ All required variables are set"
exit 0
```
