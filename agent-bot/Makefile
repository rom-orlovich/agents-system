.PHONY: help init build up down logs test test-all test-api-gateway test-agent-engine test-dashboard test-logger test-services test-cov lint format clean health cli cli-down cli-logs cli-claude cli-cursor db-migrate db-upgrade env-validate

PROVIDER ?= claude
SCALE ?= 1
SERVICE ?=
DC = docker-compose

# ============================================
# HELP
# ============================================
help:
	@./scripts/utils/help.sh

# ============================================
# INITIALIZATION
# ============================================
init:
	@cp -n .env.example .env 2>/dev/null || true
	@cd agent-engine-package && pip install -e ".[dev]"
	@echo "✅ Initialized. Update .env with your credentials."

env-validate:
	@./scripts/env/validate.sh

# ============================================
# SERVICES
# ============================================
build:
	@$(DC) build

up:
	@./scripts/services/start.sh

down:
	@./scripts/services/stop.sh

start: up

health:
	@./scripts/services/health.sh

logs:
	@./scripts/services/logs.sh $(SERVICE)

# ============================================
# CLI AGENTS
# ============================================
cli:
	@./scripts/cli/start.sh $(PROVIDER) $(SCALE)

cli-down:
	@./scripts/cli/stop.sh $(PROVIDER)

cli-logs:
	@./scripts/cli/logs.sh $(PROVIDER)

cli-claude:
	@./scripts/cli/start.sh claude $(SCALE)

cli-cursor:
	@./scripts/cli/start.sh cursor $(SCALE)

# ============================================
# TESTING
# ============================================
test: test-all

test-all:
	@./scripts/test/run-all.sh

test-api-gateway:
	@./scripts/test/run-service.sh api-gateway

test-agent-engine:
	@./scripts/test/run-service.sh agent-engine

test-dashboard:
	@./scripts/test/run-service.sh dashboard-api

test-logger:
	@./scripts/test/run-service.sh task-logger

test-services:
	@./scripts/test/run-service.sh services

test-cov:
	@./scripts/test/coverage.sh

# ============================================
# CODE QUALITY
# ============================================
lint:
	@uv run ruff check .

format:
	@uv run ruff format .

# ============================================
# DATABASE
# ============================================
db-migrate:
	@./scripts/db/migrate.sh "$(MSG)"

db-upgrade:
	@./scripts/db/upgrade.sh

# ============================================
# CLEANUP
# ============================================
clean:
	@./scripts/utils/clean.sh
