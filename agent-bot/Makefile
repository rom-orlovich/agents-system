.PHONY: help init build up down restart logs test lint format clean

help:
	@echo "Agent Bot - Containerized Multi-Agent System"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  init              Initialize project (install dependencies, create dirs)"
	@echo "  build             Build all Docker containers"
	@echo "  build-dashboard   Build dashboard services only"
	@echo ""
	@echo "Docker:"
	@echo "  up                Start all services"
	@echo "  up-infra          Start infrastructure only (Redis, PostgreSQL)"
	@echo "  up-dashboard      Start dashboard services only"
	@echo "  down              Stop all services"
	@echo "  restart           Restart all services"
	@echo "  restart-dashboard Restart dashboard services"
	@echo "  logs              View logs (all services)"
	@echo "  logs-gateway      View api-gateway logs"
	@echo "  logs-dashboard    View dashboard-api logs"
	@echo "  logs-ui           View external-dashboard logs"
	@echo "  logs-task-logger  View task-logger logs"
	@echo ""
	@echo "CLI Agent:"
	@echo "  cli-up            Start CLI (PROVIDER=claude|cursor SCALE=1)"
	@echo "  cli-down          Stop CLI (PROVIDER=claude|cursor)"
	@echo "  cli-logs          View CLI logs (PROVIDER=claude|cursor)"
	@echo "  cli-status        Check CLI status (PROVIDER=claude|cursor)"
	@echo "  cli-active        Show active CLI instances in database"
	@echo ""
	@echo "Testing:"
	@echo "  test              Run all tests"
	@echo "  test-unit         Run unit tests"
	@echo "  test-integration  Run integration tests"
	@echo "  test-cli          Run CLI test (Claude/Cursor)"
	@echo "  test-task-logger  Run task-logger tests"
	@echo "  coverage          Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint              Run linting"
	@echo "  format            Auto-format code"
	@echo "  typecheck         Run type checking"
	@echo ""
	@echo "Database:"
	@echo "  db-migrate MSG=x  Create new migration"
	@echo "  db-upgrade        Apply migrations"
	@echo "  db-downgrade      Rollback last migration"
	@echo "  db-shell          Open database shell"
	@echo ""
	@echo "Utilities:"
	@echo "  clean             Remove build artifacts"
	@echo "  redis-cli         Open Redis CLI"
	@echo "  shell             Open shell in agent-engine"
	@echo "  shell-dashboard   Open shell in dashboard-api"
	@echo "  health            Check all service health"

# Setup
init:
	@echo "Initializing project..."
	cp -n .env.example .env 2>/dev/null || true
	cd agent-engine-package && pip install -e ".[dev]"
	@echo "Done. Update .env with your API keys."

build:
	docker-compose build

build-dashboard:
	docker-compose build dashboard-api external-dashboard

# Docker
up:
	docker-compose up -d

up-infra:
	docker-compose up -d redis postgres

up-dashboard:
	docker-compose up -d dashboard-api external-dashboard

up-scale:
	docker-compose up -d --scale agent-engine=$(N)

up-engine:
	@echo "Starting $(or $(PROVIDER),claude) CLI..."
	@echo "   Provider: $(or $(PROVIDER),claude)"
	@echo "   Replicas: $(or $(SCALE),1)"
	@echo ""
	@docker-compose -p $(or $(PROVIDER),claude) up -d redis postgres
	@echo "Waiting for infrastructure to be healthy..."
	@sleep 5
	@CLI_PROVIDER=$(or $(PROVIDER),claude) docker-compose -p $(or $(PROVIDER),claude) up -d --scale cli=$(or $(SCALE),1) cli
	@echo ""
	@echo "✅ $(or $(PROVIDER),claude) CLI started"
	@echo ""
	@docker-compose -p $(or $(PROVIDER),claude) ps cli
	@echo ""
	@echo "View logs: make cli-logs PROVIDER=$(or $(PROVIDER),claude)"
	@echo "Stop: make cli-down PROVIDER=$(or $(PROVIDER),claude)"

cli-up: up-engine

cli-down:
	@echo "Stopping $(or $(PROVIDER),claude) CLI..."
	@docker-compose -p $(or $(PROVIDER),claude) down

cli-logs:
	@docker-compose -p $(or $(PROVIDER),claude) logs -f cli

cli-status:
	@docker-compose -p $(or $(PROVIDER),claude) ps cli

cli-active:
	@echo "Active CLI instances in database:"
	@docker-compose exec -T postgres psql -U agent -d agent_system -c "\
		SELECT provider, version, hostname, active, \
		       started_at, last_heartbeat, \
		       EXTRACT(EPOCH FROM (NOW() - last_heartbeat)) as seconds_since_heartbeat \
		FROM cli_instances \
		WHERE active = true \
		ORDER BY provider, started_at DESC;" || echo "⚠️  Database not available"

down:
	docker-compose down

restart:
	docker-compose restart

restart-dashboard:
	docker-compose restart dashboard-api external-dashboard

logs:
	docker-compose logs -f

logs-engine:
	docker-compose logs -f cli

logs-gateway:
	docker-compose logs -f api-gateway

logs-dashboard:
	docker-compose logs -f dashboard-api

logs-ui:
	docker-compose logs -f external-dashboard

logs-task-logger:
	docker-compose logs -f task-logger

# Testing
test:
	cd agent-engine-package && pytest

test-unit:
	cd agent-engine-package && pytest tests/unit/

test-integration:
	cd agent-engine-package && pytest tests/integration/

test-cli:
	@echo "🧪 Running CLI test in agent-engine container..."
	@docker-compose exec -T agent-engine python scripts/test_cli_after_build.py || true
	@echo "✅ CLI test completed"

test-task-logger:
	@echo "🧪 Running task-logger tests..."
	@docker-compose exec -T task-logger pytest -v tests/
	@echo "✅ Task-logger tests completed"

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

db-downgrade:
	cd agent-engine-package && alembic downgrade -1

db-shell:
	docker-compose exec postgres psql -U agent -d agent_system

# Utilities
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

redis-cli:
	docker-compose exec redis redis-cli

shell:
	docker-compose exec agent-engine bash

shell-dashboard:
	docker-compose exec dashboard-api bash

# Health checks
health:
	@echo "🔍 Checking services health..."
	@echo ""
	@echo -n "API Gateway (8000):      "
	@curl -sf http://localhost:8000/health > /dev/null && echo "✅ UP" || echo "❌ DOWN"
	@echo -n "Agent Engine (8080):     "
	@curl -sf http://localhost:8080/health > /dev/null && echo "✅ UP" || echo "❌ DOWN"
	@echo -n "Dashboard API (5000):    "
	@curl -sf http://localhost:5000/api/health > /dev/null && echo "✅ UP" || echo "❌ DOWN"
	@echo -n "External Dashboard (3005): "
	@curl -sf http://localhost:3005/ > /dev/null && echo "✅ UP" || echo "❌ DOWN"
	@echo -n "Task Logger (8090):      "
	@curl -sf http://localhost:8090/health > /dev/null && echo "✅ UP" || echo "❌ DOWN"
	@echo -n "Redis:                   "
	@docker-compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo "✅ UP" || echo "❌ DOWN"
	@echo -n "PostgreSQL:              "
	@docker-compose exec -T postgres pg_isready -U agent > /dev/null 2>&1 && echo "✅ UP" || echo "❌ DOWN"
