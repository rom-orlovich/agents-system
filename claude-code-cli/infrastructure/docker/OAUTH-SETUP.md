# Authentication Setup for Claude Code CLI in Docker

This guide explains how to authenticate Claude Code CLI in Docker containers for headless operation.

## 📋 Table of Contents

1. [Why OAuth Instead of API Key?](#why-oauth-instead-of-api-key)
2. [The Keychain Problem](#the-keychain-problem)
3. [Solution Overview](#solution-overview)
4. [Quick Setup](#quick-setup)
5. [Architecture Changes](#architecture-changes)
6. [Troubleshooting](#troubleshooting)

---

## Why OAuth Instead of API Key?

### Cost Difference

| Method | Billing | Approximate Cost |
|--------|---------|------------------|
| **API Key** (`ANTHROPIC_API_KEY`) | Pay-per-token | ~$15-50+ per complex task |
| **OAuth** (Claude subscription) | Fixed monthly fee | $20/month Pro, $30/month Team |

**If you have a Claude Pro or Team subscription**, using OAuth means your Docker containers use your **subscription credits** instead of charging per API call.

### Example Scenario
- **With API Key:** Running 100 tasks/month × $15/task = **$1,500/month**
- **With OAuth:** 100 tasks/month using your $20 Pro subscription = **$20/month**

---

## The Keychain Problem

### Claude CLI v2.1.12+ Change

**Before v2.1.12:**
```
~/.claude/.credentials.json  ← OAuth tokens stored in file (easy to mount in Docker)
```

**After v2.1.12:**
```
macOS Keychain  ← OAuth tokens stored securely in Keychain (NOT accessible in Docker)
```

### The Problem

When you run `claude login`, the CLI stores your OAuth tokens in the **macOS Keychain**, not in a file. Docker containers **cannot access the macOS Keychain** because:

1. Keychain is a macOS-specific secure storage
2. Docker containers run Linux and don't have access to host Keychain
3. There's no API to bridge Keychain to Docker

### The Solution

We need to **extract** OAuth tokens from the Keychain and save them to a file that Docker can mount:

```
┌─────────────────────────────────────────────────────────────────┐
│  macOS Host                                                     │
│                                                                 │
│  ┌─────────────┐    extract-oauth.sh    ┌──────────────────┐   │
│  │  Keychain   │ ────────────────────► │ ~/.claude/        │   │
│  │  (secure)   │                        │ .credentials.json │   │
│  └─────────────┘                        └─────────┬────────┘   │
│                                                   │             │
└───────────────────────────────────────────────────│─────────────┘
                                                    │ Docker mount
                                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Docker Container                                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  /home/claude/.claude/.credentials.json                   │  │
│  │  → Claude CLI reads OAuth token                           │  │
│  │  → Uses your Claude subscription (no extra cost)          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Solution Overview

### What We Built

| Component | Purpose |
|-----------|---------|
| `extract-oauth.sh` | Script that extracts OAuth from Keychain to file |
| Non-root user in Dockerfile | Required for `--dangerously-skip-permissions` flag |
| Docker volume mounts | Mount credentials file into container |
| Entrypoint script | Validates authentication before starting worker |

### Files Changed

```
infrastructure/docker/
├── extract-oauth.sh         # NEW: Keychain → file extraction
├── docker-compose.yml        # UPDATED: Mount credentials + non-root user
├── OAUTH-SETUP.md           # This documentation
└── .env                      # Add ANTHROPIC_API_KEY as fallback

agents/planning-agent/
├── Dockerfile               # UPDATED: Non-root 'claude' user
├── entrypoint.sh            # UPDATED: Check OAuth or API key
└── worker.py                # Uses claude CLI which reads credentials
```

---

## Quick Setup

### Option 1: OAuth (Recommended - Uses Your Subscription)

**Step 1: Login to Claude (if not already done)**
```bash
claude login
# Follow browser authentication
```

**Step 2: Extract credentials from Keychain**
```bash
cd infrastructure/docker
./extract-oauth.sh
```

This creates `~/.claude/.credentials.json` with your OAuth tokens.

**Step 3: Start Docker containers**
```bash
docker-compose up -d
```

The containers will mount your credentials file and use your subscription.

### Option 2: API Key (Pay-per-use)

**Step 1: Get API Key**
1. Go to https://console.anthropic.com/settings/keys
2. Create a new API key

**Step 2: Add to .env**
```bash
cd infrastructure/docker
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." >> .env
```

**Step 3: Start Docker containers**
```bash
docker-compose up -d
```

---

## Architecture Changes

### Problem 1: Root User + `--dangerously-skip-permissions`

**The Error:**
```
--dangerously-skip-permissions cannot be used with root/sudo privileges for security reasons
```

**Why This Happens:**
- Docker containers run as `root` by default
- Claude CLI blocks `--dangerously-skip-permissions` when running as root (security measure)
- Our worker.py uses this flag for headless operation

**Solution:**
We created a non-root user `claude` in the Dockerfile:

```dockerfile
# Create non-root user for Claude CLI
RUN useradd -m -s /bin/bash claude \
    && usermod -aG docker claude

# Set up directories for the new user
RUN mkdir -p /home/claude/.claude \
    && chown -R claude:claude /app /workspace /home/claude

# Switch to non-root user
USER claude
```

### Problem 2: Keychain Not Accessible in Docker

**Solution:**
The `extract-oauth.sh` script uses macOS `security` command to read from Keychain:

```bash
# Extract credentials from Keychain
CREDS=$(security find-generic-password -s "Claude Code-credentials" -a "$USER" -w)

# Save to file for Docker mounting
echo "$CREDS" > ~/.claude/.credentials.json
```

### Problem 3: Container Needs Credentials

**Solution:**
Docker Compose mounts the credentials file (read-only):

```yaml
volumes:
  # Mount OAuth credentials (extracted from Keychain)
  - ~/.claude/.credentials.json:/home/claude/.claude/.credentials.json:ro
  # Mount MCP config for tool access  
  - ~/.claude/mcp.json:/home/claude/.claude/mcp.json:ro
```

### Authentication Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Container Startup Flow                          │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │    entrypoint.sh starts      │
               └──────────────┬───────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │ Check: credentials.json      │
               │ exists?                       │
               └──────────────┬───────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │ YES                               │ NO
            ▼                                   ▼
┌───────────────────────┐          ┌───────────────────────┐
│ Use OAuth             │          │ Check: ANTHROPIC_     │
│ (subscription)        │          │ API_KEY set?          │
└───────────────────────┘          └───────────┬───────────┘
                                               │
                           ┌───────────────────┴───────────────────┐
                           │ YES                                   │ NO
                           ▼                                       ▼
              ┌───────────────────────┐           ┌───────────────────────┐
              │ Use API Key           │           │ ERROR: No auth        │
              │ (pay-per-use)         │           │ Container exits       │
              └───────────────────────┘           └───────────────────────┘
```

---

## Troubleshooting

### Error: `--dangerously-skip-permissions cannot be used with root/sudo`

**Cause:** Container is running as root user.

**Fix:** Ensure Dockerfile has:
```dockerfile
USER claude  # Must be non-root user
```

And worker.py runs Claude CLI without sudo:
```python
cmd = ["claude", "-p", "--dangerously-skip-permissions", ...]  # No sudo
```

### Error: `No authentication found`

**Cause:** Neither OAuth credentials file nor API key is available.

**Fix:**
1. Run `./extract-oauth.sh` to extract credentials from Keychain, OR
2. Add `ANTHROPIC_API_KEY` to `.env` file

### Error: `Claude authentication failed`

**Cause:** OAuth token expired or credentials file is corrupted.

**Fix:**
1. Re-run `claude login` on host machine
2. Run `./extract-oauth.sh` again
3. Restart containers

### Error: Credentials file not found in container

**Check:**
```bash
docker exec planning-agent-1 ls -la /home/claude/.claude/
```

**Fix:** Ensure docker-compose.yml has correct mount:
```yaml
volumes:
  - ~/.claude/.credentials.json:/home/claude/.claude/.credentials.json:ro
```

### Token Expiration

OAuth tokens expire periodically. To refresh:
1. Run `claude login` on host (or just run `./extract-oauth.sh` which auto-runs login if needed)
2. Restart containers to pick up new credentials

---

## Summary: Why These Changes Were Made

| Problem | Solution | File Changed |
|---------|----------|--------------|
| Claude CLI v2.1.12 stores OAuth in Keychain | Extract script to copy to file | `extract-oauth.sh` |
| Docker can't access macOS Keychain | Mount credentials file into container | `docker-compose.yml` |
| `--dangerously-skip-permissions` blocked as root | Run container as non-root `claude` user | `Dockerfile` |
| Need fallback if OAuth not available | Support both OAuth and API key | `entrypoint.sh` |
| Save money vs pay-per-use API | Use OAuth with subscription | This whole setup! |

---

## Quick Reference

```bash
# One-time setup (extracts OAuth from Keychain)
cd infrastructure/docker
./extract-oauth.sh

# Start containers
docker-compose up -d

# Check authentication in container
docker exec planning-agent-1 cat /home/claude/.claude/.credentials.json

# View logs
docker-compose logs -f planning-agent

# Restart after changes
docker-compose down && docker-compose up -d
```

---

## Cost Comparison Table

| Authentication | Monthly Cost (100 tasks) | Notes |
|----------------|--------------------------|-------|
| API Key | ~$1,500/month | $15 average per task |
| OAuth (Pro) | $20/month | Unlimited within subscription |
| OAuth (Team) | $30/user/month | Better for teams |

**Bottom Line:** If you have a Claude subscription, using OAuth saves significant money!
