.PHONY: help init build up down logs test lint format clean health cli cli-up cli-down cli-logs cli-claude cli-cursor

# Variables
PROVIDER ?= claude
SCALE ?= 1
DC = docker-compose
DC_CLI = $(DC) -f docker-compose.cli.yml -p $(PROVIDER)-cli --env-file .env

help:
	@echo "Agent Bot Commands"
	@echo ""
	@echo "CLI (recommended):"
	@echo "  make cli-claude         Start Claude CLI"
	@echo "  make cli-cursor         Start Cursor CLI"
	@echo "  make cli-down P=claude  Stop CLI (P=claude|cursor)"
	@echo "  make cli-logs P=claude  View logs (P=claude|cursor)"
	@echo ""
	@echo "Services:"
	@echo "  make start              Start full system"
	@echo "  make up / down          Start/stop all services"
	@echo "  make health             Check service health"
	@echo ""
	@echo "Development:"
	@echo "  make test               Run tests"
	@echo "  make lint / format      Code quality"
	@echo "  make db-migrate MSG=x   Create migration"

# Setup
init:
	@cp -n .env.example .env 2>/dev/null || true
	@cd agent-engine-package && pip install -e ".[dev]"
	@echo "✅ Done. Update .env with your API keys."

build:
	@$(DC) build

# Docker
up:
	@$(DC) up -d

down:
	@$(DC) down

# CLI - Unified target
define start_cli
	@echo "Starting $(1) CLI..."
	@$(DC) up -d redis postgres 2>/dev/null || true
	@docker network create agent-network 2>/dev/null || true
	@CLI_PROVIDER=$(1) $(DC) -f docker-compose.cli.yml -p $(1)-cli --env-file .env build cli
	@CLI_PROVIDER=$(1) $(DC) -f docker-compose.cli.yml -p $(1)-cli --env-file .env up -d --scale cli=$(2) cli
	@echo "✅ $(1) CLI started (scale: $(2))"
	@$(DC) -f docker-compose.cli.yml -p $(1)-cli ps cli
endef

cli-claude:
	$(call start_cli,claude,$(SCALE))

cli-cursor:
	$(call start_cli,cursor,$(SCALE))

cli-down:
	@P=$${P:-$(PROVIDER)}; \
	echo "Stopping $$P CLI..."; \
	$(DC) -f docker-compose.cli.yml -p $$P-cli down 2>/dev/null || echo "No $$P CLI found"

cli-logs:
	@P=$${P:-$(PROVIDER)}; \
	$(DC) -f docker-compose.cli.yml -p $$P-cli logs -f cli

# Start full system
start:
	@echo "🚀 Starting Agent Bot..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker required"; exit 1; }
	@docker ps >/dev/null 2>&1 || { echo "❌ Start Docker Desktop"; exit 1; }
	@test -f .env || cp .env.example .env
	@$(DC) build --quiet
	@$(DC) up -d
	@sleep 5
	@echo ""
	@$(MAKE) health
	@echo ""
	@echo "✅ System ready: http://localhost:8000"

# Health check
health:
	@echo "Service Status:"
	@curl -sf http://localhost:8000/health >/dev/null && echo "  ✅ API Gateway" || echo "  ❌ API Gateway"
	@curl -sf http://localhost:8080/health >/dev/null && echo "  ✅ Agent Engine" || echo "  ❌ Agent Engine"
	@curl -sf http://localhost:5000/api/health >/dev/null && echo "  ✅ Dashboard" || echo "  ❌ Dashboard"
	@$(DC) exec -T redis redis-cli ping >/dev/null 2>&1 && echo "  ✅ Redis" || echo "  ❌ Redis"
	@$(DC) exec -T postgres pg_isready -U agent >/dev/null 2>&1 && echo "  ✅ PostgreSQL" || echo "  ❌ PostgreSQL"

# Testing
test:
	@cd agent-engine-package && pytest

coverage:
	@cd agent-engine-package && pytest --cov=agent_engine --cov-report=html

# Code Quality
lint:
	@cd agent-engine-package && ruff check .

format:
	@cd agent-engine-package && ruff format .

typecheck:
	@cd agent-engine-package && mypy .

# Database
db-migrate:
	@cd agent-engine-package && alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	@cd agent-engine-package && alembic upgrade head

# Cleanup
clean:
	@find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name "*.egg-info" \) -exec rm -rf {} + 2>/dev/null || true
