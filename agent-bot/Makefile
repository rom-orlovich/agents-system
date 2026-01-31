.PHONY: help init build up down logs test test-all test-unit test-api-gateway test-agent-engine test-dashboard test-logger test-services test-cov lint format clean health cli-down cli-logs cli-claude cli-cursor

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
	@echo "Testing:"
	@echo "  make test-all           Run all tests (265 tests)"
	@echo "  make test-unit          Run unit tests only"
	@echo "  make test-api-gateway   Run API Gateway tests (92)"
	@echo "  make test-agent-engine  Run Agent Engine tests (64)"
	@echo "  make test-dashboard     Run Dashboard API tests (38)"
	@echo "  make test-logger        Run Task Logger tests (27)"
	@echo "  make test-services      Run API Services tests (33)"
	@echo "  make test-cov           Run tests with coverage"
	@echo ""
	@echo "Dev:"
	@echo "  make lint / format"

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

test-all:
	@echo "Running all 265 tests..."
	@PYTHONPATH=tests:$$PYTHONPATH uv run pytest tests/test_factories.py -v --tb=short
	@PYTHONPATH=tests:api-gateway:$$PYTHONPATH uv run pytest api-gateway/tests/ -v --tb=short
	@PYTHONPATH=tests:dashboard-api:$$PYTHONPATH uv run pytest dashboard-api/tests/ -v --tb=short
	@PYTHONPATH=tests:agent-engine:$$PYTHONPATH uv run pytest agent-engine/tests/ -v --tb=short
	@PYTHONPATH=tests:task-logger:$$PYTHONPATH uv run pytest task-logger/tests/ -v --tb=short
	@uv run pytest api-services/github-api/tests/ -v --tb=short
	@uv run pytest api-services/jira-api/tests/ -v --tb=short
	@uv run pytest api-services/slack-api/tests/ -v --tb=short
	@uv run pytest api-services/sentry-api/tests/ -v --tb=short
	@echo "✅ All tests passed!"

test-unit:
	@echo "Running unit tests..."
	@PYTHONPATH=tests:$$PYTHONPATH uv run pytest tests/test_factories.py -v --tb=short

test-api-gateway:
	@echo "Running API Gateway tests (92)..."
	@PYTHONPATH=tests:api-gateway:$$PYTHONPATH uv run pytest api-gateway/tests/ -v --tb=short

test-agent-engine:
	@echo "Running Agent Engine tests (64)..."
	@PYTHONPATH=tests:agent-engine:$$PYTHONPATH uv run pytest agent-engine/tests/ -v --tb=short

test-dashboard:
	@echo "Running Dashboard API tests (38)..."
	@PYTHONPATH=tests:dashboard-api:$$PYTHONPATH uv run pytest dashboard-api/tests/ -v --tb=short

test-logger:
	@echo "Running Task Logger tests (27)..."
	@PYTHONPATH=tests:task-logger:$$PYTHONPATH uv run pytest task-logger/tests/ -v --tb=short

test-services:
	@echo "Running API Services tests (33)..."
	@uv run pytest api-services/github-api/tests/ api-services/jira-api/tests/ api-services/slack-api/tests/ api-services/sentry-api/tests/ -v --tb=short

test-cov:
	@echo "Running tests with coverage..."
	@PYTHONPATH=tests:api-gateway:agent-engine:dashboard-api:task-logger:$$PYTHONPATH uv run pytest \
		tests/test_factories.py \
		api-gateway/tests/ \
		agent-engine/tests/ \
		dashboard-api/tests/ \
		task-logger/tests/ \
		--cov=. --cov-report=html --cov-report=term-missing -v --tb=short
	@echo "✅ Coverage report: htmlcov/index.html"

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
