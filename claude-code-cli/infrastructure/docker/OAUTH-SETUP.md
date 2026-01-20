# OAuth Setup for Claude Code CLI in Docker

Guide for authenticating Claude Code CLI in Docker containers using OAuth credentials.

---

## 📋 Quick Reference

**Problem**: Claude CLI v2.1.12+ stores OAuth in macOS Keychain, which Docker can't access.

**Solution**: Extract credentials from Keychain to a file that Docker can mount.

**Commands**:
```bash
# Extract OAuth from Keychain
./extract-oauth.sh

# Start containers (credentials auto-mounted)
docker-compose up -d
```

---

## 💰 Why OAuth vs API Key?

| Method | Billing | Cost |
|--------|---------|------|
| **OAuth** (Claude subscription) | Fixed monthly | $20/month (Pro) or $30/month (Teams) |
| **API Key** | Pay-per-token | ~$15-50+ per complex task |

**If you have Claude Pro/Teams**, use OAuth to leverage your subscription instead of paying per API call.

---

## 🔧 How It Works

### The Problem

Claude CLI v2.1.12+ stores OAuth tokens in macOS Keychain:
```
Before: ~/.claude/.credentials.json  ✅ (Docker can mount)
After:  macOS Keychain               ❌ (Docker can't access)
```

### The Solution

```
┌─────────────────────────────────────────────────────────┐
│  macOS Host                                             │
│  ┌──────────┐  extract-oauth.sh  ┌──────────────────┐  │
│  │ Keychain │ ─────────────────→ │ ~/.claude/       │  │
│  │          │                     │ .credentials.json│  │
│  └──────────┘                     └────────┬─────────┘  │
└─────────────────────────────────────────────│───────────┘
                                              │ Docker mount
                                              ▼
┌─────────────────────────────────────────────────────────┐
│  Docker Container                                       │
│  /home/claude/.claude/.credentials.json                 │
│  → Claude CLI reads OAuth token                         │
│  → Uses your subscription (no extra cost)               │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Setup

### Option 1: OAuth (Recommended)

**Step 1: Login to Claude**
```bash
claude login
# Follow browser authentication
```

**Step 2: Extract credentials**
```bash
cd infrastructure/docker
./extract-oauth.sh
```

This creates `~/.claude/.credentials.json` from your Keychain.

**Step 3: Start containers**
```bash
docker-compose up -d
```

Credentials are automatically mounted via `docker-compose.yml`:
```yaml
volumes:
  - ~/.claude/.credentials.json:/home/claude/.claude/.credentials.json:ro
  - ~/.claude/mcp.json:/home/claude/.claude/mcp.json:ro
```

### Option 2: API Key

**Step 1: Get API key**
1. Visit https://console.anthropic.com/settings/keys
2. Create new API key

**Step 2: Add to .env**
```bash
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." >> infrastructure/docker/.env
```

**Step 3: Start containers**
```bash
docker-compose up -d
```

---

## 🔍 Authentication Flow

```
Container Startup
       │
       ▼
Check: .credentials.json exists?
       │
   ┌───┴───┐
  YES     NO
   │       │
   ▼       ▼
Use OAuth  Check: ANTHROPIC_API_KEY set?
           │
       ┌───┴───┐
      YES     NO
       │       │
       ▼       ▼
   Use API   ERROR
    Key      Exit
```

---

## 🐛 Troubleshooting

### Error: `--dangerously-skip-permissions cannot be used with root/sudo`

**Cause**: Container running as root.

**Fix**: Ensure Dockerfile has:
```dockerfile
USER claude  # Non-root user
```

### Error: `No authentication found`

**Cause**: Neither OAuth nor API key available.

**Fix**:
```bash
# Option 1: Extract OAuth
./extract-oauth.sh

# Option 2: Add API key
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### Error: `Claude authentication failed`

**Cause**: OAuth token expired.

**Fix**:
```bash
claude login
./extract-oauth.sh
docker-compose restart
```

### Token Expiration

OAuth tokens expire periodically. To refresh:
```bash
./extract-oauth.sh  # Auto-runs 'claude login' if needed
docker-compose restart
```

---

## 📝 What Changed

| Problem | Solution | File |
|---------|----------|------|
| Keychain not accessible in Docker | Extract to file | `extract-oauth.sh` |
| Docker can't read Keychain | Mount credentials file | `docker-compose.yml` |
| `--dangerously-skip-permissions` blocked as root | Non-root `claude` user | `Dockerfile` |
| Need fallback auth | Support OAuth + API key | `entrypoint.sh` |

---

## 💡 Cost Comparison

| Authentication | Monthly Cost (100 tasks) | Notes |
|----------------|--------------------------|-------|
| API Key | ~$1,500 | $15 average per task |
| OAuth (Pro) | $20 | Unlimited within subscription |
| OAuth (Teams) | $30/user | Better for teams |

**Bottom Line**: If you have a Claude subscription, OAuth saves significant money!

---

## 🔗 Quick Commands

```bash
# Extract OAuth (one-time setup)
cd infrastructure/docker && ./extract-oauth.sh

# Start containers
docker-compose up -d

# Verify authentication in container
docker exec planning-agent-1 cat /home/claude/.claude/.credentials.json

# View logs
docker-compose logs -f planning-agent

# Restart after changes
docker-compose restart
```
