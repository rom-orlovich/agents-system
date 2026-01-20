# Claude Code CLI - Context & Guidelines

## 🧠 System Context
This project connects **Claude Code CLI** with **MCP** (Model Context Protocol) to create an autonomous bug-fixing system. 
- **Two-Agent Architecture**: `planning-agent` (Analysis & Plan) + `executor-agent` (TDD Implementation).
- **Tech Stack**: Python 3.12 (uv), FastAPI, Redis, Docker, Go (Dashboard).

## 🛠️ Main Commands
**Development (Makefile)**
- `make start`   : First-time setup (Build + Up + OAuth)
- `make up`      : Start all services
- `make down`    : Stop all services
- `make rebuild` : Rebuild Docker images (Run after updating `pyproject.toml`)
- `make restart` : Fast restart (stop + up)
- `make logs`    : Tail logs
- `make tunnel`  : Expose webhooks via ngrok

**Agent Commands (GitHub/Slack)**
- `@agent approve` : Approve plan execution
- `@agent reject [reason]` : Reject plan
- `@agent improve <feedback>` : Request changes to plan
- `@agent status` : Check task status

## 🏗️ Architecture Helpers
- **Agents**: located in `agents/`. Use `worker.py` for queue logic.
- **Skills**: located in `agents/*/skills/`. Defined by `SKILL.md`.
- **Services**: `webhook-server` (FastAPI), `dashboard` (Go).
- **Shared**: `shared/` contains database models, Redis queue, and config.

## 📝 Coding Guidelines
1. **Package Management**:
   - ALWAY use `uv` for Python dependencies.
   - Dependencies are in `pyproject.toml`.
   - **NO** `requirements.txt` files allowed.
   - Dockerfiles use `uv pip install .`.

2. **Data Models**:
   - Use **Pydantic** models (v2) for all data structures (see `shared/models.py`).
   - Avoid raw dictionaries for complex data.

3. **Dashboard**:
   - Dashboard is a Go binary (`services/dashboard`).
   - Frontend is vanilla HTML/JS in `services/dashboard/static`.

4. **Testing**:
   - `pytest` for Python tests.
   - TDD validation is strictly enforced by the Executor Agent.

## 🐛 Troubleshooting
- **Streaming Limit Error**: Check `shared/claude_runner.py` for buffer limit handling.
- **Redis Error**: Verify `hset` vs `hmset` usage in `shared/task_queue.py`.
- **Webhook Issues**: Use `make tunnel` and check ngrok inspector.
- **Dependency Issues**: Run `make rebuild` to refresh `uv` environment in Docker.
