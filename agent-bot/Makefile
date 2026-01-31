.PHONY: help init build up down restart logs test lint format clean

help:
	@echo "Agent Bot - Quick Commands"
	@echo ""
	@echo "Start:"
	@echo "  make start             Start system (checks prerequisites)"
	@echo "  make cli-claude        Start Claude CLI"
	@echo "  make cli-cursor        Start Cursor CLI"
	@echo ""
	@echo "Services:"
	@echo "  make up                Start all services"
	@echo "  make down              Stop all services"
	@echo "  make health            Check service health"
	@echo ""
	@echo "Development:"
	@echo "  make test              Run tests"
	@echo "  make lint              Run linting"
	@echo "  make format            Auto-format code"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate MSG=x  Create migration"
	@echo "  make db-upgrade        Apply migrations"

# Setup
init:
	@echo "Initializing project..."
	cp -n .env.example .env 2>/dev/null || true
	cd agent-engine-package && pip install -e ".[dev]"
	@echo "Done. Update .env with your API keys."

build:
	docker-compose build

# Start (with checks)
start:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║        🚀 Starting Agent Bot System                          ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📋 Checking prerequisites..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker required. Get it from https://docker.com"; exit 1; }
	@docker ps >/dev/null 2>&1 || { echo "❌ Docker daemon not running. Start Docker Desktop."; exit 1; }
	@echo "✅ Docker OK"
	@echo ""
	@echo "📄 Checking environment..."
	@test -f .env || { echo "📄 Creating .env..."; cp .env.example .env; }
	@echo "✅ Environment file ready"
	@echo ""
	@echo "🔑 Checking CLI credentials..."
	@if [ -d ~/.claude ] || grep -q "^ANTHROPIC_API_KEY=" .env 2>/dev/null; then \
		echo "✅ Claude CLI credentials found"; \
	else \
		echo "⚠️  Claude CLI not configured (set ANTHROPIC_API_KEY in .env)"; \
	fi
	@if grep -q "^CURSOR_API_KEY=" .env 2>/dev/null; then \
		echo "✅ Cursor API key found"; \
	else \
		echo "⚠️  Cursor API key not set (set CURSOR_API_KEY in .env)"; \
	fi
	@echo ""
	@echo "🔨 Building containers..."
	@docker-compose build --quiet
	@echo "🚀 Starting services..."
	@docker-compose up -d redis postgres
	@sleep 5
	@docker-compose up -d
	@sleep 5
	@echo ""
	@echo "🧪 Verifying services..."
	@curl -sf http://localhost:8000/health > /dev/null && echo "✅ API Gateway" || echo "⚠️  API Gateway not ready"
	@curl -sf http://localhost:5000/api/health > /dev/null && echo "✅ Dashboard API" || echo "⚠️  Dashboard API not ready"
	@docker-compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo "✅ Redis" || echo "⚠️  Redis not ready"
	@docker-compose exec -T postgres pg_isready -U agent > /dev/null 2>&1 && echo "✅ PostgreSQL" || echo "⚠️  PostgreSQL not ready"
	@echo ""
	@echo "🧪 Testing CLI and logging to database..."
	@PROVIDER=$${CLI_PROVIDER:-claude}; \
	if [ "$$PROVIDER" = "claude" ]; then \
		if [ -f $$HOME/.claude/.credentials.json ]; then \
			docker-compose run --rm \
				-e DATABASE_URL=postgresql+asyncpg://agent:$${POSTGRES_PASSWORD:-agent}@postgres:5432/agent_system \
				-e CLI_PROVIDER=claude \
				-v $$HOME/.claude/.credentials.json:/root/.claude/.credentials.json:ro \
				cli python scripts/test_cli.py 2>/dev/null || echo "⚠️  CLI test skipped (no credentials)"; \
		elif grep -q "^ANTHROPIC_API_KEY=" .env 2>/dev/null; then \
			docker-compose run --rm \
				-e DATABASE_URL=postgresql+asyncpg://agent:$${POSTGRES_PASSWORD:-agent}@postgres:5432/agent_system \
				-e CLI_PROVIDER=claude \
				-e ANTHROPIC_API_KEY=$$(grep "^ANTHROPIC_API_KEY=" .env | cut -d'=' -f2-) \
				cli python scripts/test_cli.py 2>/dev/null || echo "⚠️  CLI test skipped"; \
		else \
			echo "⚠️  CLI test skipped (no credentials found)"; \
		fi; \
	elif [ "$$PROVIDER" = "cursor" ] && grep -q "^CURSOR_API_KEY=" .env 2>/dev/null; then \
		docker-compose run --rm \
			-e DATABASE_URL=postgresql+asyncpg://agent:$${POSTGRES_PASSWORD:-agent}@postgres:5432/agent_system \
			-e CLI_PROVIDER=cursor \
			-e CURSOR_API_KEY=$$(grep "^CURSOR_API_KEY=" .env | cut -d'=' -f2-) \
			cli python scripts/test_cli.py 2>/dev/null || echo "⚠️  CLI test skipped"; \
	fi
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║        ✅ System Ready!                                      ║"
	@echo "╠══════════════════════════════════════════════════════════════╣"
	@echo "║  🔗 API Gateway:   http://localhost:8000                     ║"
	@echo "║  📊 Dashboard:     http://localhost:5000                     ║"
	@echo "║  💚 Health:        http://localhost:8000/health             ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Next steps:"
	@echo "  make cli-claude        Start Claude CLI"
	@echo "  make cli-cursor        Start Cursor CLI"
	@echo "  make health            Check all services"
	@echo ""

# Docker
up:
	docker-compose up -d

down:
	docker-compose down

# CLI Agent
cli-claude:
	@echo "Starting Claude CLI..."
	@echo "Ensuring shared Redis and PostgreSQL are running..."
	@docker-compose up -d redis postgres 2>/dev/null || true
	@sleep 3
	@echo "Ensuring shared network exists..."
	@docker network create agent-network 2>/dev/null || docker network inspect agent-network >/dev/null 2>&1 || docker-compose network create agent-network 2>/dev/null || true
	@echo "Building CLI container..."
	@CLI_PROVIDER=claude docker-compose -f docker-compose.cli.yml -p claude-cli --env-file .env build cli
	@echo "Calculating scale..."
	@EXISTING=$$(docker ps -a --filter "name=claude-cli-cli" --format "{{.Names}}" | wc -l | tr -d ' '); \
	if [ -n "$$SCALE" ]; then \
		TARGET_SCALE=$$SCALE; \
	elif [ "$$EXISTING" -gt 0 ]; then \
		TARGET_SCALE=$$((EXISTING + 1)); \
		echo "Found $$EXISTING existing container(s), scaling to $$TARGET_SCALE"; \
	else \
		TARGET_SCALE=1; \
	fi; \
	echo "Starting Claude CLI container(s) (scale: $$TARGET_SCALE)..."; \
	echo "Note: CLI test will run automatically in container entrypoint"; \
	CLI_PROVIDER=claude docker-compose -f docker-compose.cli.yml -p claude-cli --env-file .env up -d --scale cli=$$TARGET_SCALE cli
	@echo "✅ Claude CLI started"
	@docker-compose -f docker-compose.cli.yml -p claude-cli ps cli
	@echo ""
	@echo "To view logs: make cli-claude-logs"

cli-cursor:
	@echo "Starting Cursor CLI..."
	@echo "Ensuring shared Redis and PostgreSQL are running..."
	@docker-compose up -d redis postgres 2>/dev/null || true
	@sleep 3
	@echo "Ensuring shared network exists..."
	@docker network create agent-network 2>/dev/null || docker network inspect agent-network >/dev/null 2>&1 || docker-compose network create agent-network 2>/dev/null || true
	@echo "Building CLI container..."
	@CLI_PROVIDER=cursor docker-compose -f docker-compose.cli.yml -p cursor-cli --env-file .env build cli
	@echo "Calculating scale..."
	@EXISTING=$$(docker ps -a --filter "name=cursor-cli-cli" --format "{{.Names}}" | wc -l | tr -d ' '); \
	if [ -n "$$SCALE" ]; then \
		TARGET_SCALE=$$SCALE; \
	elif [ "$$EXISTING" -gt 0 ]; then \
		TARGET_SCALE=$$((EXISTING + 1)); \
		echo "Found $$EXISTING existing container(s), scaling to $$TARGET_SCALE"; \
	else \
		TARGET_SCALE=1; \
	fi; \
	echo "Starting Cursor CLI container(s) (scale: $$TARGET_SCALE)..."; \
	echo "Note: CLI test will run automatically in container entrypoint"; \
	CLI_PROVIDER=cursor docker-compose -f docker-compose.cli.yml -p cursor-cli --env-file .env up -d --scale cli=$$TARGET_SCALE cli
	@echo "✅ Cursor CLI started"
	@docker-compose -f docker-compose.cli.yml -p cursor-cli ps cli
	@echo ""
	@echo "To view logs: make cli-cursor-logs"

cli-claude-down:
	@echo "Stopping Claude CLI containers..."
	@if docker ps --format '{{.Names}}' | grep -q '^claude-cli-cli'; then \
		docker-compose -f docker-compose.cli.yml -p claude-cli down; \
	elif docker ps --format '{{.Names}}' | grep -q '^claude.*cli'; then \
		docker-compose -p claude down; \
	else \
		echo "No Claude CLI containers found"; \
	fi

cli-cursor-down:
	@echo "Stopping Cursor CLI containers..."
	@if docker ps --format '{{.Names}}' | grep -q '^cursor-cli-cli'; then \
		docker-compose -f docker-compose.cli.yml -p cursor-cli down; \
	elif docker ps --format '{{.Names}}' | grep -q '^cursor.*cli'; then \
		docker-compose -p cursor down; \
	else \
		echo "No Cursor CLI containers found"; \
	fi

cli-claude-logs:
	@docker-compose -f docker-compose.cli.yml -p claude-cli logs -f cli

cli-cursor-logs:
	@docker-compose -f docker-compose.cli.yml -p cursor-cli logs -f cli


# Testing
test:
	cd agent-engine-package && pytest

coverage:
	cd agent-engine-package && pytest --cov=agent_engine --cov-report=html

# Code Quality
lint:
	cd agent-engine-package && ruff check .

format:
	cd agent-engine-package && ruff format .

typecheck:
	cd agent-engine-package && mypy .

# Database
db-migrate:
	cd agent-engine-package && alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	cd agent-engine-package && alembic upgrade head

# Utilities
clean:
	find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name "*.egg-info" \) -exec rm -rf {} + 2>/dev/null || true

health:
	@echo "🔍 Checking services..."
	@curl -sf http://localhost:8000/health > /dev/null && echo "✅ API Gateway" || echo "❌ API Gateway"
	@curl -sf http://localhost:8080/health > /dev/null && echo "✅ Agent Engine" || echo "❌ Agent Engine"
	@curl -sf http://localhost:5000/api/health > /dev/null && echo "✅ Dashboard API" || echo "❌ Dashboard API"
	@curl -sf http://localhost:8090/health > /dev/null && echo "✅ Task Logger" || echo "❌ Task Logger"
	@docker-compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo "✅ Redis" || echo "❌ Redis"
	@docker-compose exec -T postgres pg_isready -U agent > /dev/null 2>&1 && echo "✅ PostgreSQL" || echo "❌ PostgreSQL"
