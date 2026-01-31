.PHONY: help init build up down logs test lint format clean health cli-down cli-logs cli-claude cli-cursor

PROVIDER ?= claude
SCALE ?= 1
DC = docker-compose

help:
	@echo "Agent Bot Commands"
	@echo ""
	@echo "CLI:"
	@echo "  make cli-claude         Start Claude CLI"
	@echo "  make cli-cursor         Start Cursor CLI"
	@echo "  make cli-down P=claude  Stop CLI"
	@echo "  make cli-logs P=claude  View logs"
	@echo ""
	@echo "Services:"
	@echo "  make start    Start full system"
	@echo "  make health   Check services"
	@echo ""
	@echo "Dev:"
	@echo "  make test / lint / format"

init:
	@cp -n .env.example .env 2>/dev/null || true
	@cd agent-engine-package && pip install -e ".[dev]"
	@echo "Done. Update .env with API keys."

build:
	@$(DC) build

up:
	@$(DC) up -d

down:
	@$(DC) down

cli-claude:
	@echo "Starting Claude CLI..."
	@$(DC) up -d redis postgres 2>/dev/null || true
	@docker network create agent-network 2>/dev/null || true
	@CLI_PROVIDER=claude $(DC) -f docker-compose.cli.yml -p claude-cli --env-file .env build cli
	@EXISTING=$$(docker ps --filter "name=claude-cli-cli" -q | wc -l | tr -d ' '); \
	TARGET=$${SCALE:-$$((EXISTING + 1))}; \
	[ "$$TARGET" -lt 1 ] && TARGET=1; \
	echo "Scaling to $$TARGET instance(s)..."; \
	CLI_PROVIDER=claude $(DC) -f docker-compose.cli.yml -p claude-cli --env-file .env up -d --scale cli=$$TARGET cli
	@echo "✅ Claude CLI started"
	@$(DC) -f docker-compose.cli.yml -p claude-cli ps cli

cli-cursor:
	@echo "Starting Cursor CLI..."
	@$(DC) up -d redis postgres 2>/dev/null || true
	@docker network create agent-network 2>/dev/null || true
	@CLI_PROVIDER=cursor $(DC) -f docker-compose.cli.yml -p cursor-cli --env-file .env build cli
	@EXISTING=$$(docker ps --filter "name=cursor-cli-cli" -q | wc -l | tr -d ' '); \
	TARGET=$${SCALE:-$$((EXISTING + 1))}; \
	[ "$$TARGET" -lt 1 ] && TARGET=1; \
	echo "Scaling to $$TARGET instance(s)..."; \
	CLI_PROVIDER=cursor $(DC) -f docker-compose.cli.yml -p cursor-cli --env-file .env up -d --scale cli=$$TARGET cli
	@echo "✅ Cursor CLI started"
	@$(DC) -f docker-compose.cli.yml -p cursor-cli ps cli

cli-down:
	@P=$${P:-$(PROVIDER)}; echo "Stopping $$P CLI..."; $(DC) -f docker-compose.cli.yml -p $$P-cli down 2>/dev/null || true

cli-logs:
	@P=$${P:-$(PROVIDER)}; $(DC) -f docker-compose.cli.yml -p $$P-cli logs -f cli

start:
	@echo "Starting Agent Bot..."
	@test -f .env || cp .env.example .env
	@$(DC) build --quiet
	@$(DC) up -d
	@sleep 5
	@$(MAKE) health
	@echo "✅ Ready: http://localhost:8000"

health:
	@echo "Services:"
	@curl -sf http://localhost:8000/health >/dev/null && echo "  ✅ API Gateway" || echo "  ❌ API Gateway"
	@curl -sf http://localhost:8080/health >/dev/null && echo "  ✅ Agent Engine" || echo "  ❌ Agent Engine"
	@$(DC) exec -T redis redis-cli ping >/dev/null 2>&1 && echo "  ✅ Redis" || echo "  ❌ Redis"
	@$(DC) exec -T postgres pg_isready -U agent >/dev/null 2>&1 && echo "  ✅ PostgreSQL" || echo "  ❌ PostgreSQL"

test:
	@cd agent-engine-package && pytest

lint:
	@cd agent-engine-package && ruff check .

format:
	@cd agent-engine-package && ruff format .

db-migrate:
	@cd agent-engine-package && alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	@cd agent-engine-package && alembic upgrade head

clean:
	@find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" \) -exec rm -rf {} + 2>/dev/null || true
