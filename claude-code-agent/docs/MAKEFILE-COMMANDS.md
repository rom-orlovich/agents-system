# Makefile Commands Reference

This document provides a quick reference for all available `make` commands in the Claude Code Agent project.

## 🚀 Main Commands

| Command | Description |
|---------|-------------|
| `make start` | 🎯 **One-command setup** - Checks prerequisites, creates .env, builds containers, and starts all services |
| `make up` | Start Docker services |
| `make down` | Stop Docker services |
| `make restart` | Restart all services (down + up) |
| `make logs` | View live logs from all containers |
| `make ps` | Show running containers |

## 🧪 Testing Commands

| Command | Description |
|---------|-------------|
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only (`tests/unit/`) |
| `make test-integration` | Run integration tests (`tests/integration/`) |
| `make test-e2e` | Run end-to-end tests (`tests/e2e/`) |
| `make test-fake` | Run fake CLI tests (no API calls, uses mock) |
| `make test-real` | Run real CLI tests (requires auth, makes actual API calls) |
| `make test-cov` | Run tests with coverage report (generates `htmlcov/index.html`) |
| `make test-all` | Run complete test suite sequentially (unit → integration → e2e) |

## 🔧 Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Install dependencies with `uv sync` |
| `make dev` | Install dev dependencies with all extras |
| `make lint` | Run ruff linter |
| `make format` | Format code with ruff |
| `make type-check` | Run mypy type checker |
| `make run-local` | Run locally without Docker (uvicorn on port 8000) |

## 🔧 Utility Commands

| Command | Description |
|---------|-------------|
| `make oauth` | Check Claude CLI OAuth credentials at `~/.claude` |
| `make env` | Edit `.env` file with nano |
| `make health` | Check system health via `/health` endpoint |
| `make build` | Build Docker containers |
| `make rebuild` | Full rebuild (down + clean + build + up) |
| `make clean` | Cleanup build artifacts, caches, and Docker volumes |

## 🗄️ Database Commands

| Command | Description |
|---------|-------------|
| `make db-shell` | Open SQLite shell for machine database |
| `make redis-cli` | Open Redis CLI |
| `make shell` | Open bash shell in app container |

## 🎬 Initialization

| Command | Description |
|---------|-------------|
| `make init` | First-time project setup (creates .env, installs dependencies) |

## Quick Start

```bash
# First time setup
make init
# Edit .env with your configuration
make env
# Start everything
make start
```

## Common Workflows

### Development Workflow
```bash
make dev              # Install dev dependencies
make run-local        # Run locally for development
make test-unit        # Run unit tests
make lint             # Check code quality
make format           # Format code
```

### Testing Workflow
```bash
make test-unit        # Quick unit tests
make test-integration # Integration tests
make test-cov         # Full coverage report
```

### Docker Workflow
```bash
make start            # First time or full setup
make logs             # Monitor logs
make restart          # Restart after changes
make down             # Stop services
make clean            # Full cleanup
```

## System URLs (when running)

- **API**: http://localhost:8000
- **Dashboard**: http://localhost:8000/dashboard
- **Health**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/ws
- **Redis**: localhost:6379

## Notes

- The `make start` command is the recommended way to launch the system - it handles all prerequisites and setup automatically
- Test commands use `uv run pytest` to ensure proper virtual environment isolation
- The `make clean` command removes Docker volumes, so use with caution if you have important data
- OAuth credentials are mounted from `~/.claude` if available, otherwise API keys from `.env` are used
