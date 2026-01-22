---
name: subagent-management
description: Spawn, stop, and monitor sub-agents
target: brain
---

# Sub-Agent Management Skill

## Purpose
This skill allows the Brain to manage sub-agents - spawning them for specific tasks, monitoring their progress, and stopping them when needed.

## Usage

Use this skill when the user wants to:
- Start a new sub-agent task
- Check status of running sub-agents
- Stop a running sub-agent
- List available sub-agents
- View sub-agent capabilities

## Available Agents

### Planning Agent
- **Location:** `.claude/agents/planning.md`
- **Purpose:** Analyze bugs and create fix plans
- **Skills:** discovery, jira-enrichment, plan-creation
- **Use when:** User asks for analysis, planning, or understanding of issues

### Executor Agent
- **Location:** `.claude/agents/executor.md`
- **Purpose:** Implement code changes and fixes
- **Skills:** code-implementation, tdd-workflow, pr-management
- **Use when:** User asks for code changes, bug fixes, or feature implementation

## How to Use

### Spawn a Sub-Agent

To spawn a sub-agent, you need to create a task via the API. The system automatically:
1. Creates a task record in the database
2. Pushes it to the Redis queue
3. Worker picks it up and spawns Claude CLI from the agent's directory

**Note:** You cannot spawn agents directly via bash commands. The system manages the lifecycle.

### Check Agent Status

```bash
# Check running tasks in Redis
redis-cli llen task_queue

# Check database for recent tasks
sqlite3 /data/db/machine.db "SELECT task_id, status, assigned_agent FROM tasks ORDER BY created_at DESC LIMIT 10"
```

### Stop a Sub-Agent

Use the API to stop a running task:
```
POST /api/tasks/{task_id}/stop
```

## Task Routing

When you receive a user request, decide which agent should handle it:

### Route to Planning Agent when:
- User asks "analyze this bug"
- User asks "create a plan for..."
- User asks "what's causing this error?"
- User provides an issue to investigate
- User asks for analysis or understanding

### Route to Executor Agent when:
- User asks "fix this bug"
- User asks "implement this feature"
- User provides a PLAN.md to execute
- User asks for code changes
- User asks to run tests

### Handle Yourself when:
- User asks about system status
- User asks to create new agents/webhooks
- User asks to install packages
- User asks for information about the machine
- Simple questions that don't require code analysis or changes

## Example Conversations

**User:** "Analyze why users can't login"
**You:** Create task for planning agent with the issue description

**User:** "Implement the password reset fix"
**You:** Create task for executor agent (assumes plan exists)

**User:** "What agents are available?"
**You:** List agents from /data/registry/agents.yaml (handle yourself)

**User:** "Install pytest"
**You:** Use container-management skill (handle yourself)

## Integration with Dashboard

When users interact through the dashboard:
1. Messages create tasks via `/api/chat`
2. Tasks are automatically routed to agents
3. Progress streams back via WebSocket
4. Results are displayed in the dashboard

## Monitoring

Check agent health:
```bash
# Check worker status
ps aux | grep claude

# Check task queue
redis-cli llen task_queue

# Check recent task outcomes
sqlite3 /data/db/machine.db "SELECT status, COUNT(*) FROM tasks GROUP BY status"
```

## Troubleshooting

**Agent not starting:**
- Check if CLAUDE.md exists in agent directory
- Check Redis connection
- Check worker logs

**Tasks stuck in queue:**
- Check worker is running
- Check Redis queue: `redis-cli llen task_queue`
- Check for worker errors in logs

**Agent taking too long:**
- Check task timeout settings (default: 3600s)
- Consider stopping and restarting with clearer instructions
