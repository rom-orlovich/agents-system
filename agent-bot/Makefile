.PHONY: help init build up down logs test test-all test-api-gateway test-agent-engine test-dashboard test-logger test-services test-cov lint format clean health cli cli-down cli-logs cli-claude cli-cursor db-migrate db-upgrade env-validate knowledge-up knowledge-down knowledge-logs knowledge-build up-full

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
# KNOWLEDGE SERVICES (Advanced Features)
# ============================================
knowledge-up:
	@echo "🧠 Starting knowledge services (LlamaIndex, GKG, Indexer)..."
	@$(DC) --profile knowledge up -d llamaindex-service llamaindex-mcp gkg-service gkg-mcp indexer-worker
	@echo "✅ Knowledge services started"

knowledge-down:
	@echo "🛑 Stopping knowledge services..."
	@$(DC) --profile knowledge stop llamaindex-service llamaindex-mcp gkg-service gkg-mcp indexer-worker
	@echo "✅ Knowledge services stopped"

knowledge-logs:
	@$(DC) --profile knowledge logs -f llamaindex-service gkg-service indexer-worker

knowledge-build:
	@echo "🔨 Building knowledge services..."
	@$(DC) --profile knowledge build llamaindex-service llamaindex-mcp gkg-service gkg-mcp indexer-worker
	@echo "✅ Knowledge services built"

# Start all services including knowledge
up-full:
	@./scripts/services/start.sh
	@$(DC) --profile knowledge up -d
	@echo "✅ All services including knowledge started"

# ============================================
# CLEANUP
# ============================================
clean:
	@./scripts/utils/clean.sh
