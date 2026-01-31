.PHONY: help init build up down restart logs test lint format clean

help:
	@echo "Agent Bot - Containerized Multi-Agent System"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  init              Initialize project (install dependencies, create dirs)"
	@echo "  build             Build all Docker containers"
	@echo ""
	@echo "Docker:"
	@echo "  up                Start all services"
	@echo "  up-infra          Start infrastructure only (Redis, PostgreSQL)"
	@echo "  up-scale N=3      Start with N agent-engine replicas"
	@echo "  down              Stop all services"
	@echo "  restart           Restart all services"
	@echo "  logs              View logs (all services)"
	@echo "  logs-engine       View agent-engine logs"
	@echo "  logs-gateway      View api-gateway logs"
	@echo ""
	@echo "Testing:"
	@echo "  test              Run all tests"
	@echo "  test-unit         Run unit tests"
	@echo "  test-integration  Run integration tests"
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

# Setup
init:
	@echo "Initializing project..."
	cp -n .env.example .env 2>/dev/null || true
	cd agent-engine-package && pip install -e ".[dev]"
	@echo "Done. Update .env with your API keys."

build:
	docker-compose build

# Docker
up:
	docker-compose up -d

up-infra:
	docker-compose up -d redis postgres

up-scale:
	docker-compose up -d --scale agent-engine=$(N)

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-engine:
	docker-compose logs -f agent-engine

logs-gateway:
	docker-compose logs -f api-gateway

# Testing
test:
	cd agent-engine-package && pytest

test-unit:
	cd agent-engine-package && pytest tests/unit/

test-integration:
	cd agent-engine-package && pytest tests/integration/

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

# Health checks
health:
	@echo "Checking services..."
	@curl -s http://localhost:8000/health || echo "API Gateway: DOWN"
	@curl -s http://localhost:8080/health || echo "Agent Engine: DOWN"
	@curl -s http://localhost:5000/health || echo "Dashboard API: DOWN"
	@docker-compose exec redis redis-cli ping || echo "Redis: DOWN"
