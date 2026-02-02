.PHONY: help init build up down logs test test-all test-api-gateway test-agent-engine test-dashboard test-logger test-services test-cov lint format clean health cli-down cli-logs cli-claude cli-cursor tunnel service-up service-down service-restart service-logs service-build service-shell

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
	@echo "  make tunnel   Start ngrok tunnel for OAuth service"
	@echo ""
	@echo "Service Management:"
	@echo "  make service-up S=oauth-service      Start a service"
	@echo "  make service-down S=oauth-service    Stop a service"
	@echo "  make service-restart S=oauth-service  Restart a service"
	@echo "  make service-logs S=oauth-service     View service logs"
	@echo "  make service-build S=oauth-service   Build a service"
	@echo "  make service-shell S=oauth-service   Open shell in container"
	@echo ""
	@echo "Testing:"
	@echo "  make test-all           Run all tests"
	@echo "  make test-api-gateway   Run API Gateway tests"
	@echo "  make test-agent-engine  Run Agent Engine tests"
	@echo "  make test-dashboard     Run Dashboard API tests"
	@echo "  make test-logger        Run Task Logger tests"
	@echo "  make test-services      Run API Services tests"
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
	@curl -sf http://localhost:8010/health >/dev/null && echo "  ✅ OAuth Service" || echo "  ❌ OAuth Service"
	@$(DC) exec -T redis redis-cli ping >/dev/null 2>&1 && echo "  ✅ Redis" || echo "  ❌ Redis"
	@$(DC) exec -T postgres pg_isready -U agent >/dev/null 2>&1 && echo "  ✅ PostgreSQL" || echo "  ❌ PostgreSQL"

tunnel:
	@echo "Starting ngrok tunnel for OAuth service..."
	@bash oauth-service/start-ngrok.sh

service-up:
	@bash scripts/docker-service.sh $(S) up

service-down:
	@bash scripts/docker-service.sh $(S) down

service-restart:
	@bash scripts/docker-service.sh $(S) restart

service-logs:
	@bash scripts/docker-service.sh $(S) logs

service-build:
	@bash scripts/docker-service.sh $(S) build

service-shell:
	@bash scripts/docker-service.sh $(S) shell

test:
	@cd agent-engine-package && pytest

test-all:
	@echo "Running all tests..."
	@PYTHONPATH=api-gateway:$$PYTHONPATH uv run pytest api-gateway/tests/ -v --tb=short
	@PYTHONPATH=dashboard-api:$$PYTHONPATH uv run pytest dashboard-api/tests/ -v --tb=short
	@PYTHONPATH=agent-engine:$$PYTHONPATH uv run pytest agent-engine/tests/ -v --tb=short
	@PYTHONPATH=task-logger:$$PYTHONPATH uv run pytest task-logger/tests/ -v --tb=short
	@uv run pytest api-services/github-api/tests/ -v --tb=short
	@uv run pytest api-services/jira-api/tests/ -v --tb=short
	@uv run pytest api-services/slack-api/tests/ -v --tb=short
	@uv run pytest api-services/sentry-api/tests/ -v --tb=short
	@echo "✅ All tests passed!"

test-api-gateway:
	@echo "Running API Gateway tests..."
	@PYTHONPATH=api-gateway:$$PYTHONPATH uv run pytest api-gateway/tests/ -v --tb=short

test-agent-engine:
	@echo "Running Agent Engine tests..."
	@PYTHONPATH=agent-engine:$$PYTHONPATH uv run pytest agent-engine/tests/ -v --tb=short

test-dashboard:
	@echo "Running Dashboard API tests..."
	@PYTHONPATH=dashboard-api:$$PYTHONPATH uv run pytest dashboard-api/tests/ -v --tb=short

test-logger:
	@echo "Running Task Logger tests..."
	@PYTHONPATH=task-logger:$$PYTHONPATH uv run pytest task-logger/tests/ -v --tb=short

test-services:
	@echo "Running API Services tests..."
	@uv run pytest api-services/github-api/tests/ api-services/jira-api/tests/ api-services/slack-api/tests/ api-services/sentry-api/tests/ -v --tb=short

test-cov:
	@echo "Running tests with coverage..."
	@PYTHONPATH=api-gateway:agent-engine:dashboard-api:task-logger:$$PYTHONPATH uv run pytest \
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
