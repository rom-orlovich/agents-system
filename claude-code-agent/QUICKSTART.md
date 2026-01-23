# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites

- Docker & Docker Compose installed
- Git installed

### Step 1: Clone and Navigate

```bash
git clone <repository-url>
cd claude-code-agent
```

### Step 2: Initialize Project

```bash
# Install dependencies and setup
make init
```

This will:
- Copy `.env.example` to `.env` if it doesn't exist
- Install dependencies using `uv`

**Optional**: Edit `.env` to customize configuration

### Step 3: Start Services

**Option A: One Command (Recommended)**
```bash
make start
```

**Option B: Manual Steps**
```bash
# Build the containers
make build

# Start all services
make up
```

**This will start:**
- FastAPI server on port 8000
- Redis on port 6379
- Task worker processing queue

### Step 4: Access Dashboard

Open your browser:
```
http://localhost:8000
```

You should see the Claude Machine Dashboard!

### Step 5: Test the System

1. **Send a test message** in the chat:
   ```
   What agents are available?
   ```

2. **Check the logs**:
   ```bash
   make logs
   ```

3. **Monitor tasks**:
   ```bash
   # Check Redis queue
   make redis-cli
   > LLEN task_queue
   > EXIT

   # Check database
   make db-shell
   > SELECT * FROM tasks;
   > .exit
   ```

## 🎯 What You Get

### 1. Dashboard Interface
- Real-time chat with Brain
- Persistent conversations with context awareness
- Task monitoring and execution logs
- Cost tracking (per-task and per-session)
- Agent and webhook management

### 2. Specialized Agents
- **Brain**: Main orchestrator (opus)
- **Planning**: Analysis and planning (opus)
- **Executor**: Implementation with TDD (sonnet)
- **Service Integrator**: Cross-service workflows (sonnet)
- **Self-Improvement**: Code analysis and refactoring (sonnet)
- **Agent Creator**: Create new agents (sonnet)
- **Skill Creator**: Create new skills (sonnet)

### 3. Webhook Endpoints
- `POST /webhooks/github` - GitHub events
- `POST /webhooks/jira` - Jira events
- `POST /webhooks/sentry` - Sentry events
- `POST /webhooks/slack` - Slack events
- `POST /webhooks/custom/{id}` - Custom webhooks

### 4. API Endpoints
- `GET /api/status` - System status
- `GET /api/tasks` - List tasks
- `GET /api/agents` - List agents
- `POST /api/chat` - Send message
- `GET /api/conversations` - List conversations
- `GET /api/webhooks` - List webhooks

### 5. WebSocket
- `WS /ws/{session_id}` - Real-time updates

## 📝 Common Tasks

### View Logs

```bash
make logs
```

### Stop Services

```bash
make down
```

### Restart Services

```bash
make restart
```

### Run Tests

```bash
make test
```

### Check Health

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "machine_id": "claude-agent-001",
  "queue_length": 0,
  "sessions": 1,
  "connections": 1
}
```

## 🔧 Development Mode

### Run Locally (without Docker)

```bash
# Install dependencies
make install

# Run locally
make run-local
```

### Run Tests

```bash
# All tests
make test

# With coverage
make test-cov

# Specific tests
pytest tests/unit/ -v
```

### Code Quality

```bash
# Lint
make lint

# Format
make format

# Type check
make type-check
```

## 📊 Example Workflow

### 1. Chat with Brain

Open dashboard → Type message:
```
Analyze the login bug in auth.py
```

### 2. Monitor Task

Watch as:
1. Task is created
2. Planning agent spawns
3. Output streams in real-time
4. Result is displayed

### 3. View Task Details

Click "View" on any task to see:
- Full input/output
- Cost breakdown
- Token usage
- Timing information

## 🎭 Agent Types

### Brain (Main Orchestrator)
- Handles simple queries
- Routes to specialized agents
- Manages system and webhooks
- Model: opus

### Planning Agent
- Analyzes bugs and issues
- Creates detailed fix plans (PLAN.md)
- No code implementation
- Model: opus

### Executor Agent
- Implements fixes following TDD workflow
- Runs tests (unit, integration, E2E)
- Creates PRs
- Model: sonnet
- Skills: testing

### Service Integrator Agent
- Integrates with GitHub, Jira, Slack, Sentry
- Orchestrates cross-service workflows
- Model: sonnet

### Self-Improvement Agent
- Analyzes codebase patterns
- Identifies refactoring opportunities
- Model: sonnet

### Agent Creator & Skill Creator
- Creates new agents and skills
- Validates structure and configuration
- Model: sonnet

## 🔌 Webhook Setup

### GitHub Webhook

1. Go to your GitHub repo settings
2. Add webhook:
   - URL: `https://your-domain.com/webhooks/github`
   - Content type: `application/json`
   - Events: Issues, Pull requests, Issue comments

3. Test it:
   - Create an issue
   - Add comment with `@agent plan this issue`
   - Watch task appear in dashboard

### Jira Webhook

1. Go to Jira settings → Webhooks
2. Add webhook:
   - URL: `https://your-domain.com/webhooks/jira`
   - Events: Issue created, Issue updated

### Sentry Webhook

1. Go to Sentry project settings
2. Add webhook:
   - URL: `https://your-domain.com/webhooks/sentry`
   - Alert rule: Error created

## 📈 Monitoring

### Check System Status

```bash
# API health
curl http://localhost:8000/api/health

# Redis status
make redis-cli
> INFO

# Database
make db-shell
> SELECT status, COUNT(*) FROM tasks GROUP BY status;
```

### View Metrics

Dashboard shows:
- Queue length
- Active sessions
- Total connections
- Per-task costs

## 🐛 Troubleshooting

### Services won't start

```bash
# Check Docker
docker-compose ps

# Check logs
make logs

# Restart
make restart
```

### Tasks not processing

```bash
# Check queue
make redis-cli
> LLEN task_queue

# Check worker logs
docker-compose logs app | grep "Task worker"
```

### Database errors

```bash
# Check database exists
docker-compose exec app ls -la /data/db/

# Reset database
docker-compose down -v
make up
```

### WebSocket not connecting

1. Check browser console for errors
2. Verify CORS settings in `.env`
3. Check firewall rules

## 🎓 Learn More

- **README.md**: Complete documentation
- **docs/CONVERSATION-QUICKSTART.md**: Conversation management guide
- **docs/WEBHOOK-SETUP.md**: Webhook configuration guide
- **docs/TDD-APPROACH.md**: Test-driven development workflow
- **.claude/CLAUDE.md**: Main brain configuration
- **.claude/agents/*.md**: Agent definitions
- **.claude/skills/*/SKILL.md**: Skill documentation

## 🆘 Need Help?

Common issues:
1. Port 8000 already in use → Change port in docker-compose.yml
2. Redis connection failed → Check Redis is running
3. Database locked → Stop all containers and restart

## 🎉 Success!

If you see the dashboard and can send messages, you're all set!

**Next steps:**
1. Explore the dashboard
2. Send test messages
3. Configure webhooks
4. Deploy to production

---

**Built with ❤️ using Claude Code CLI**
