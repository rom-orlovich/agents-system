# Docker Data Persistence Guide

**Date**: January 22, 2026
**Status**: Production Configuration
**Project**: Claude Code Agent System

---

## TL;DR - What Persists After Container Restart?

| Data Type | Location | Persisted? | Notes |
|-----------|----------|------------|-------|
| **Database** | `/data/db/machine.db` | ✅ YES | Named volume `machine_data` |
| **Credentials** | `/data/credentials/claude.json` | ✅ YES | Named volume `machine_data` |
| **User Agents** | `/data/config/agents/` | ✅ YES | Named volume `machine_data` |
| **User Skills** | `/data/config/skills/` | ✅ YES | Named volume `machine_data` |
| **Webhooks Config** | `/data/config/webhooks/` | ✅ YES | Named volume `machine_data` |
| **Registry** | `/data/registry/` | ✅ YES | Named volume `machine_data` |
| **Built-in Agents** | `/app/agents/` | ❌ NO | Read-only from image |
| **Built-in Skills** | `/app/skills/` | ❌ NO | Read-only from image |
| **Built-in CLAUDE.md** | `/app/.claude/` | ❌ NO | Read-only from image |

---

## Docker Volume Configuration

### Named Volumes (Persisted)

```yaml
# docker-compose.yml
volumes:
  machine_data:           # ✅ PERSISTS across container restarts
    driver: local
  redis_data:             # ✅ PERSISTS across container restarts
    driver: local
```

### Volume Mounts

```yaml
services:
  app:
    volumes:
      # PERSISTENT - Named volume
      - machine_data:/data                  # ✅ All data here persists

      # READ-ONLY - Bind mounts from host (for built-in resources)
      - ./agents:/app/agents:ro             # ❌ Image-provided agents (immutable)
      - ./skills:/app/skills:ro             # ❌ Image-provided skills (immutable)
      - ./.claude:/app/.claude:ro           # ❌ Image-provided CLAUDE.md (immutable)
```

---

## Directory Structure

### Container Filesystem Layout

```
Container Root
├── /app/                                   # Application directory
│   ├── .claude/                           # ❌ READ-ONLY (from image)
│   │   └── CLAUDE.md                      # Brain's instruction file
│   ├── agents/                            # ❌ READ-ONLY (from image)
│   │   ├── planning/                      # Built-in planning agent
│   │   │   └── CLAUDE.md
│   │   └── executor/                      # Built-in executor agent
│   │       └── CLAUDE.md
│   ├── skills/                            # ❌ READ-ONLY (from image)
│   │   ├── code-review/
│   │   └── test-runner/
│   ├── api/                               # Application code
│   ├── core/
│   ├── workers/
│   └── main.py
│
└── /data/                                  # ✅ PERSISTENT VOLUME (survives container restarts)
    ├── db/                                # Database storage
    │   └── machine.db                     # SQLite database
    ├── credentials/                       # API credentials
    │   └── claude.json                    # Claude API key
    ├── config/                            # User-uploaded configuration
    │   ├── agents/                        # ✅ USER-UPLOADED AGENTS (persisted)
    │   │   ├── custom-agent-1/
    │   │   │   ├── CLAUDE.md
    │   │   │   └── skills/
    │   │   └── custom-agent-2/
    │   ├── skills/                        # ✅ USER-UPLOADED SKILLS (persisted)
    │   │   ├── custom-skill-1/
    │   │   └── custom-skill-2/
    │   └── webhooks/                      # Webhook configurations
    │       ├── github.json
    │       └── jira.json
    └── registry/                          # Registry files
        └── agents.json
```

---

## How Agent Directory Resolution Works

### Priority Order (Code: `workers/task_worker.py`)

```python
def _get_agent_dir(self, agent_name: str | None) -> Path:
    """
    Get directory for agent with priority:
    1. User-uploaded agents (/data/config/agents) - PERSISTED
    2. Built-in agents (/app/agents) - from Docker image
    3. Brain (/app) - default
    """

    # Priority 1: Check user-uploaded agents (persisted)
    user_agent_dir = settings.user_agents_dir / agent_name  # /data/config/agents/custom
    if user_agent_dir.exists():
        return user_agent_dir  # ✅ WILL PERSIST

    # Priority 2: Check built-in agents (from image)
    builtin_agent_dir = settings.agents_dir / agent_name  # /app/agents/planning
    if builtin_agent_dir.exists():
        return builtin_agent_dir  # ❌ READ-ONLY

    # Priority 3: Default to brain
    return settings.app_dir  # /app
```

---

## Upload Scenarios

### Scenario 1: User Uploads Custom Agent via API ✅

```python
# API call: POST /api/agents/upload
{
  "name": "my-custom-agent",
  "claude_md": "...",
  "skills": [...]
}

# Backend saves to:
/data/config/agents/my-custom-agent/CLAUDE.md  # ✅ PERSISTED

# After container restart:
# - Custom agent still exists ✅
# - Tasks can use "my-custom-agent" ✅
```

### Scenario 2: User Uploads Credentials ✅

```python
# API call: POST /api/credentials
{
  "api_key": "sk-ant-..."
}

# Backend saves to:
/data/credentials/claude.json  # ✅ PERSISTED

# After container restart:
# - Credentials still valid ✅
# - No re-authentication needed ✅
```

### Scenario 3: Container Restart

```bash
# User uploads agent
docker exec claude-agent curl -X POST http://localhost:8000/api/agents/upload \
  -d '{"name":"my-agent","claude_md":"..."}'
# ✅ Saved to /data/config/agents/my-agent/

# Container restarts
docker restart claude-agent

# Agent still exists?
docker exec claude-agent ls /data/config/agents/
# Output: my-agent  ✅ STILL THERE
```

---

## Database Persistence

### SQLite Database Location

```python
# core/config.py
database_url: str = "sqlite+aiosqlite:////data/db/machine.db"
                                      # ^^^^^^ Persistent volume
```

### What's Stored in Database?

1. **Sessions** - All user sessions with connection history
2. **Tasks** - Complete task history (prompts, results, costs)
3. **Logs** - Task execution logs
4. **Metrics** - Usage metrics, token counts, costs

### Database Survival

```bash
# Before container stop
docker exec claude-agent sqlite3 /data/db/machine.db "SELECT COUNT(*) FROM tasks;"
# Output: 150

# Stop and remove container
docker stop claude-agent
docker rm claude-agent

# Recreate container
docker-compose up -d

# Check database
docker exec claude-agent sqlite3 /data/db/machine.db "SELECT COUNT(*) FROM tasks;"
# Output: 150  ✅ DATA PRESERVED
```

---

## Redis Persistence

### Configuration

```yaml
# docker-compose.yml
redis:
  volumes:
    - redis_data:/data                    # ✅ PERSISTED
  command: redis-server --appendonly yes  # AOF persistence enabled
```

### What's Stored in Redis?

1. **Task Queue** - Pending tasks waiting for workers
2. **Task Status** - Real-time task status (QUEUED, RUNNING, COMPLETED)
3. **Output Buffers** - Streaming output chunks
4. **Session Data** - Active WebSocket sessions

### Redis Survival

```bash
# Add task to queue
docker exec claude-agent redis-cli RPUSH task_queue "task-123"

# Restart Redis
docker restart claude-agent-redis

# Check queue
docker exec claude-agent redis-cli LLEN task_queue
# Output: 1  ✅ QUEUE PRESERVED (because of AOF)
```

---

## Common Pitfalls

### ❌ **WRONG**: Trying to Modify Read-Only Directories

```python
# This will FAIL:
agent_file = Path("/app/agents/new-agent/CLAUDE.md")
agent_file.write_text("...")
# PermissionError: /app/agents is read-only!
```

### ✅ **CORRECT**: Use Persistent Directories

```python
# This works:
agent_file = Path("/data/config/agents/new-agent/CLAUDE.md")
agent_file.parent.mkdir(parents=True, exist_ok=True)
agent_file.write_text("...")
# ✅ Saved to persistent volume
```

---

## Volume Management Commands

### Inspect Volume

```bash
# Check volume details
docker volume inspect claude-code-agent_machine_data

# Output:
[
    {
        "Name": "claude-code-agent_machine_data",
        "Driver": "local",
        "Mountpoint": "/var/lib/docker/volumes/claude-code-agent_machine_data/_data"
    }
]
```

### Backup Volume

```bash
# Backup persistent data
docker run --rm \
  -v claude-code-agent_machine_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/machine-data-backup.tar.gz -C /data .

# Result: machine-data-backup.tar.gz contains all persistent data
```

### Restore Volume

```bash
# Restore from backup
docker run --rm \
  -v claude-code-agent_machine_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/machine-data-backup.tar.gz"
```

### Delete Volume (DANGER!)

```bash
# ⚠️ WARNING: This PERMANENTLY deletes all data
docker-compose down -v

# Removes:
# - machine_data volume (database, credentials, user agents)
# - redis_data volume (queue, cache)
```

---

## Production Best Practices

### 1. Regular Backups

```bash
# Cron job for daily backups
0 2 * * * docker run --rm \
  -v claude-code-agent_machine_data:/data \
  -v /backups:/backup \
  alpine tar czf /backup/machine-data-$(date +\%Y\%m\%d).tar.gz -C /data .
```

### 2. Use External Database (Production)

```yaml
# For production, replace SQLite with PostgreSQL
environment:
  - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/claude_db
```

### 3. Use Redis Cluster (High Availability)

```yaml
# For production, use Redis Sentinel or Cluster
environment:
  - REDIS_URL=redis-sentinel://sentinel1:26379,sentinel2:26379/mymaster
```

### 4. Monitor Volume Usage

```bash
# Check volume disk usage
docker system df -v

# Check specific volume
docker run --rm -v claude-code-agent_machine_data:/data alpine du -sh /data
```

---

## Configuration Reference

### Settings (core/config.py)

```python
class Settings(BaseSettings):
    # Persistent directories (in /data volume)
    data_dir: Path = Path("/data")                    # ✅ PERSISTED
    database_url: str = "sqlite+aiosqlite:////data/db/machine.db"

    # Property methods
    @property
    def user_agents_dir(self) -> Path:
        return self.data_dir / "config" / "agents"    # ✅ PERSISTED

    @property
    def user_skills_dir(self) -> Path:
        return self.data_dir / "config" / "skills"    # ✅ PERSISTED

    @property
    def credentials_path(self) -> Path:
        return self.data_dir / "credentials" / "claude.json"  # ✅ PERSISTED

    # Read-only directories (from image)
    app_dir: Path = Path("/app")                      # ❌ FROM IMAGE

    @property
    def agents_dir(self) -> Path:
        return self.app_dir / "agents"                # ❌ READ-ONLY

    @property
    def skills_dir(self) -> Path:
        return self.app_dir / "skills"                # ❌ READ-ONLY
```

---

## Debugging Persistence Issues

### Test 1: Verify Volume Mounts

```bash
docker exec claude-agent df -h
# Should show:
# /dev/vda1  100G  /data  (or similar - indicates volume mount)
```

### Test 2: Create Test File

```bash
# Create file in persistent directory
docker exec claude-agent touch /data/test-persistence.txt

# Restart container
docker restart claude-agent

# Check if file still exists
docker exec claude-agent ls /data/test-persistence.txt
# Should return: /data/test-persistence.txt  ✅
```

### Test 3: Database Persistence

```bash
# Insert test record
docker exec claude-agent sqlite3 /data/db/machine.db \
  "INSERT INTO tasks (task_id, status) VALUES ('test-123', 'COMPLETED');"

# Restart container
docker restart claude-agent

# Query record
docker exec claude-agent sqlite3 /data/db/machine.db \
  "SELECT task_id FROM tasks WHERE task_id='test-123';"
# Should return: test-123  ✅
```

---

## Summary

### ✅ What WILL Persist
- Database (`/data/db/`)
- Credentials (`/data/credentials/`)
- User-uploaded agents (`/data/config/agents/`)
- User-uploaded skills (`/data/config/skills/`)
- Webhook configurations (`/data/config/webhooks/`)
- Registry files (`/data/registry/`)

### ❌ What Will NOT Persist (By Design)
- Built-in agents in `/app/agents` (immutable, from Docker image)
- Built-in skills in `/app/skills` (immutable, from Docker image)
- Application code in `/app` (updated via Docker image rebuild)

### 🔑 Key Principle
**User-generated data** → `/data/` → ✅ Persisted
**Built-in resources** → `/app/` → ❌ Immutable (from image)

---

**Last Updated**: 2026-01-22
**Reviewed By**: Claude Code Agent
**Version**: 1.0.0
