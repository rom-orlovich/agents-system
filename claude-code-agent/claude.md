# Claude Code Agent - Complete Documentation

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Architecture & Business Logic](#architecture--business-logic)
4. [Process Flow](#process-flow)
5. [Core Components](#core-components)
6. [Conversation Management](#conversation-management)
7. [Unified Webhook System](#unified-webhook-system)
8. [Testing](#testing)
9. [Development Workflow](#development-workflow)

---

## Overview

The Claude Code Agent is a **self-managing machine** where FastAPI runs as a persistent daemon and Claude Code CLI is spawned on-demand per request. This architecture enables:

- **Brain Orchestrator**: Main Claude CLI instance managing sub-agents
- **Persistent Conversations**: Inbox-style interface with full history and context
- **Dynamic Sub-Agents**: Planning, Executor, and Orchestration agents
- **Unified Webhooks**: User-configurable webhooks for GitHub, Jira, and Slack
- **Real-time Dashboard**: WebSocket-based conversational UI
- **Cost Tracking**: Per-task and per-session monitoring
- **Dual Storage**: Redis (ephemeral queue/cache) + SQLite (persistent data)

### Key Principles

1. **Pydantic Everywhere**: All business logic enforced via Pydantic models
2. **On-Demand CLI**: Claude CLI spawned per request, not always running
3. **Delegation Pattern**: Brain delegates complex tasks to specialized agents
4. **Type Safety**: Full typing with mypy strict mode
5. **Asyncio Native**: All I/O operations are async

---

## Installation

**IMPORTANT**: This project exclusively uses `uv` for dependency management and task execution.

### Prerequisites

- Python 3.11+
- `uv` package manager
- Docker & Docker Compose (for production)
- Git

### Quick Start with uv

```bash
# 1. Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repository
git clone <repository-url>
cd claude-code-agent

# 3. Install dependencies using uv
uv sync

# 4. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 5. Run tests to verify installation
uv run pytest tests/ -v

# 6. Run the application locally
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Using Make Commands (All use uv)

```bash
# Development
make run-local      # Run locally with uv
make test          # Run all tests with uv
make lint          # Run ruff linting
make format        # Format code with ruff

# Docker (for production)
make build         # Build Docker image
make up            # Start services
make down          # Stop services
make logs          # View logs
```

---

## Architecture & Business Logic

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      CONTAINER (Pod)                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────────────────────────────────────────────────────┐    │
│   │         FastAPI Server (DAEMON - always running)     │    │
│   │   • Webhooks  • Dashboard API  • WebSocket          │    │
│   └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│   ┌─────────────────────────────────────────────────────┐    │
│   │              Task Queue (Redis)                      │    │
│   └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│   ┌─────────────────────────────────────────────────────┐    │
│   │              Worker (Python async)                   │    │
│   │   • Processes queue  • Spawns Claude CLI            │    │
│   └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│   ┌─────────────────────────────────────────────────────┐    │
│   │     Claude Code CLI (ON-DEMAND - spawn per task)    │    │
│   │   • Brain: /app/                                     │    │
│   │   • Agents: .claude/agents/*.md                      │    │
│   │     (Planning, Executor, Orchestration)              │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Business Logic: Domain Models

All business rules are enforced in Pydantic models (`shared/machine_models.py`):

#### 1. **Task Model** - Task Lifecycle Management
- Status transitions: `QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED`
- Automatic timing and duration calculation
- Cost and token usage tracking

#### 2. **Conversation Model** - Persistent Chat History
- `ConversationDB`: Title, user_id, updated_at
- `ConversationMessageDB`: Role (user/assistant), content, metadata
- Automatic context retrieval for agent prompts (last 20 messages)

#### 3. **Session Model** - User Session Tracking
- Tracks total cost and active tasks per user session

#### 4. **Webhook Models** - Dynamic Configuration
- `WebhookConfig`: Provider, secret, enabled status
- `WebhookCommand`: Trigger, action, template, priority

---

## Process Flow

### 1. Dashboard Chat Flow
1. User selects/creates a **Conversation**
2. User sends message via Dashboard
3. Message saved to `ConversationMessageDB`
4. **Context** (last 20 messages) retrieved and formatted
5. **Task** created in SQLite (status=QUEUED)
6. Task ID pushed to **Redis Queue**
7. **TaskWorker** pops task, marks as RUNNING
8. Claude CLI spawned in `app_dir`
9. Output streamed real-time via **WebSocket** and buffered in Redis
10. Task completes; results saved; status updated to COMPLETED
11. Response added back to **Conversation**

### 2. Unified Webhook Flow
1. Webhook received (e.g., `/webhooks/github/webhook-123`)
2. HMAC signature verified (if configured)
3. Payload matched against **WebhookCommands**
4. Actions executed in **Priority Order**:
   - `github_reaction`: Add 👀 or 👍
   - `github_label`: Add labels like "bot-processing"
   - `create_task`: Create agent task with template rendering
   - `comment`: Post acknowledgment back to source
5. TaskWorker processes created tasks as usual

---

## Core Components

### 1. Main Application (`main.py`)
FastAPI entry point. Manages lifespan, database initialization, and route registration.

### 2. Task Worker (`workers/task_worker.py`)
Background processor that polls Redis and manages Claude CLI subprocesses. Handles concurrency via semaphores.

### 3. CLI Runner (`core/cli_runner.py`)
Low-level executor for Claude CLI. Handles JSON output parsing, streaming, and metric extraction.

### 4. WebSocket Hub (`core/websocket_hub.py`)
Broadcasts real-time output chunks and status updates to browser clients.

### 5. Conversation Manager (`api/conversations.py`)
Handles CRUD for conversations and messages. Provides context formatting for agents.

### 6. Webhook Engine (`core/webhook_engine.py`)
Processes incoming payloads, matches triggers, and executes actions.

---

## Conversation Management

The machine features a persistent inbox-style conversation system.

### Features
- **Inbox Sidebar**: Create, rename, delete, and switch between multiple conversations.
- **Persistent Context**: The agent automatically remembers the last 20 messages in the thread.
- **Task Linking**: Every message is linked to its underlying task for full traceability.
- **Traceability**: Click on any message to view its execution details and logs.

### UI Usage
- Found in the **Chat** tab.
- Click **➕** to start a new thread.
- Hover over conversation title to **Rename** or **Delete**.

---

## Unified Webhook System

A powerful, user-configurable webhook system that works for GitHub, Jira, Slack, and generic sources.

### Supported Actions
- `create_task`: Queue a task for an agent (Planning, Executor, Brain).
- `comment`: Post a response message back to the provider.
- `github_reaction`: Add reactions (👀, 👍, etc.) to GitHub comments.
- `github_label`: Automatically label GitHub issues/PRs.
- `ask`: Request clarification from a user.
- `forward`: Send event data to another service.

### Templates
Pre-built templates are available for:
- **GitHub Issue Tracking**: Auto-triage, label, and analyze new issues.
- **GitHub PR Review**: Automated code review on PR open.
- **GitHub Mention Bot**: Respond to `@agent` mentions in comments.
- **Jira Sync**: Automatically create agent tasks from Jira tickets.

---

## Testing

Comprehensive testing suite covering all business logic and API endpoints.

```bash
# Run all tests
uv run pytest tests/ -v

# Run unit tests only
uv run pytest tests/unit/ -v

# Run with coverage report
uv run pytest tests/ -v --cov=. --cov-report=html
```

---

## Development Workflow

1. **Define Models**: Update `shared/machine_models.py` with any new rules.
2. **Write Tests**: Create unit tests in `tests/unit/`.
3. **Implement**: Add logic in `core/` or `api/`.
4. **Validate**: Run tests and linting (`make test`, `make lint`).
5. **Dockerize**: Test in container environment (`make rebuild`).

### Key Directories
- `.claude/agents/`: Native agent instruction files.
- `api/`: FastAPI route handlers.
- `core/`: Core business logic and infrastructure.
- `shared/`: Domain models (Pydantic).
- `services/dashboard/static/`: Frontend application code.
- `data/`: Persistent storage (locally mapped to host).

---

**Built with ❤️ using Claude Code CLI**
