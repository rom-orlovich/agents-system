.PHONY: help start install dev test test-unit test-integration test-e2e test-cov test-all lint format type-check clean clean-all build up down logs restart ps db-shell redis-cli run-local shell init health oauth env rebuild tunnel

# Load environment variables if they exist
-include .env
export

# ngrok static domain - set this in your CLI or .env!
# Example: NGROK_DOMAIN=unabating-unoverdrawn-veronique.ngrok-free.dev
NGROK_DOMAIN ?= unabating-unoverdrawn-veronique.ngrok-free.dev

# =============================================================================
# HELP
# =============================================================================

help:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║        🤖 Claude Code Agent System                           ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 MAIN COMMANDS"
	@echo "───────────────────────────────────────────────────────────────"
	@echo "  make start     - 🎯 Setup + Build + Start (one command!)"
	@echo "  make up        - Start services"
	@echo "  make down      - Stop services"
	@echo "  make restart   - Restart services"
	@echo "  make logs      - View logs"
	@echo ""
	@echo "🧪 TESTING"
	@echo "───────────────────────────────────────────────────────────────"
	@echo "  make test      - Run all tests"
	@echo "  make test-unit - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-e2e  - Run end-to-end tests"
	@echo "  make test-fake - Run fake CLI tests (no API calls)"
	@echo "  make test-real - Run real CLI tests (requires auth)"
	@echo "  make test-cov  - Run tests with coverage report"
	@echo "  make test-all  - Run all test suites sequentially"
	@echo ""
	@echo "🔧 DEVELOPMENT"
	@echo "───────────────────────────────────────────────────────────────"
	@echo "  make install   - Install dependencies"
	@echo "  make dev       - Install dev dependencies"
	@echo "  make lint      - Run linting"
	@echo "  make format    - Format code"
	@echo "  make type-check - Run type checking"
	@echo "  make run-local - Run locally (no Docker)"
	@echo ""
	@echo "🔧 UTILITIES"
	@echo "───────────────────────────────────────────────────────────────"
	@echo "  make oauth     - Extract OAuth credentials"
	@echo "  make env       - Edit .env file"
	@echo "  make health    - Health check"
	@echo "  make tunnel    - 📡 Setup webhook tunnel (ngrok/cloudflared)"
	@echo "  make clean     - Clean build cache (preserves data)"
	@echo "  make clean-all - ⚠️  Clean everything including data volumes"
	@echo "  make rebuild   - Full rebuild (preserves data volumes)"
	@echo ""

# =============================================================================
# 🚀 MAIN COMMANDS
# =============================================================================

# 🎯 ONE COMMAND TO RULE THEM ALL
start:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║        🚀 Starting Claude Code Agent System                  ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@# Prerequisites
	@echo "📋 Checking prerequisites..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker required. Get it from https://docker.com"; exit 1; }
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	@echo "✅ Prerequisites OK"
	@echo ""
	@# Environment
	@test -f .env || { echo "📄 Creating .env..."; cp .env.example .env; }
	@# OAuth (optional - will use API key if this fails)
	@echo "🔑 Checking Claude CLI credentials..."
	@test -d ~/.claude && echo "✅ Claude CLI configured" || echo "⚠️  Claude CLI not configured (will use API key if set in .env)"
	@echo ""
	@# Build & Start
	@echo "🔨 Building containers..."
	@docker-compose build --quiet
	@echo "🚀 Starting services..."
	@docker-compose up -d
	@sleep 5
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║        ✅ System Ready!                                      ║"
	@echo "╠══════════════════════════════════════════════════════════════╣"
	@echo "║  🔗 API:       http://localhost:8000                         ║"
	@echo "║  📊 Dashboard: http://localhost:8000/dashboard               ║"
	@echo "║  💚 Health:    http://localhost:8000/health                  ║"
	@echo "║  🔌 WebSocket: ws://localhost:8000/ws                        ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  make logs    - View logs"`
	@echo "  make health  - Check system health"
	@echo "  make test    - Run tests"
	@echo ""

up:
	@echo "🚀 Starting services..."
	@docker-compose up -d
	@sleep 3
	@echo "✅ Running at http://localhost:8000"

down:
	@echo "🛑 Stopping services..."
	@docker-compose down
	@echo "✅ Stopped"

restart: down up

logs:
	@docker-compose logs -f

ps:
	@docker-compose ps

# =============================================================================
# 🧪 TESTING
# =============================================================================

test:
	@echo "🧪 Running all tests..."
	@uv run pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	@uv run pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	@uv run pytest tests/integration/ -v

test-e2e:
	@echo "🧪 Running end-to-end tests..."
	@uv run pytest tests/e2e/ -v

test-fake:
	@echo "🧪 Running fake CLI tests (no API calls)..."
	@uv run pytest tests/integration/ -v -m fake_cli

test-real:
	@echo "🧪 Running real CLI tests (requires auth, makes API calls)..."
	@uv run pytest tests/integration/ -v -m real_cli

test-cov:
	@echo "🧪 Running tests with coverage..."
	@uv run pytest tests/ -v --cov=. --cov-report=html --cov-report=term
	@echo ""
	@echo "📊 Coverage report generated: htmlcov/index.html"

test-all:
	@echo "🧪 Running complete test suite..."
	@echo ""
	@echo "1️⃣ Unit Tests"
	@echo "───────────────────────────────────────────────────────────────"
	@uv run pytest tests/unit/ -v || true
	@echo ""
	@echo "2️⃣ Integration Tests"
	@echo "───────────────────────────────────────────────────────────────"
	@uv run pytest tests/integration/ -v || true
	@echo ""
	@echo "3️⃣ End-to-End Tests"
	@echo "───────────────────────────────────────────────────────────────"
	@uv run pytest tests/e2e/ -v || true
	@echo ""
	@echo "✅ Test suite complete"

# =============================================================================
# 🔧 DEVELOPMENT
# =============================================================================

install:
	@echo "📦 Installing dependencies..."
	@uv sync
	@echo "✅ Dependencies installed"

dev:
	@echo "📦 Installing dev dependencies..."
	@uv sync --all-extras
	@echo "✅ Dev dependencies installed"

lint:
	@echo "🔍 Running linter..."
	@uv run ruff check .

format:
	@echo "✨ Formatting code..."
	@uv run ruff format .

type-check:
	@echo "🔍 Running type checker..."
	@uv run mypy .

run-local:
	@echo "🚀 Running locally (no Docker)..."
	@uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# =============================================================================
# 🔧 UTILITIES
# =============================================================================

oauth:
	@echo "🔑 Checking Claude CLI OAuth..."
	@test -d ~/.claude && echo "✅ Claude CLI configured at ~/.claude" || echo "❌ Run 'claude login' first"
	@test -f ~/.claude/config.json && echo "✅ Config found" || echo "⚠️  No config.json"

env:
	@test -f .env || cp .env.example .env
	@nano .env

health:
	@echo "💚 Checking system health..."
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Service not responding"

build:
	@echo "🔨 Building Docker containers..."
	@docker-compose build

rebuild: down build up
	@echo "✅ Rebuild complete"
	@echo "💾 Data volumes preserved"

tunnel:
	@command -v ngrok >/dev/null 2>&1 || { echo "📦 Installing ngrok via Homebrew..."; brew install ngrok; }
	@if [ -z "$(NGROK_DOMAIN)" ]; then \
		echo "❌ NGROK_DOMAIN is not set!"; \
		echo "Please set it: make tunnel NGROK_DOMAIN=your-name.ngrok-free.dev"; \
		echo "Or add it to your .env: NGROK_DOMAIN=your-name.ngrok-free.dev"; \
		exit 1; \
	fi
	@echo ""
	@echo "🌐 Webhook URLs (Permanent!):"
	@echo "  GitHub:  https://$(NGROK_DOMAIN)/webhooks/github"
	@echo "  Jira:    https://$(NGROK_DOMAIN)/webhooks/jira"
	@echo "  Sentry:  https://$(NGROK_DOMAIN)/webhooks/sentry"
	@echo "  Slack:   https://$(NGROK_DOMAIN)/webhooks/slack"
	@echo "  GitLab:  https://$(NGROK_DOMAIN)/webhooks/gitlab"
	@echo "  Custom:  https://$(NGROK_DOMAIN)/webhooks/custom/{id}"
	@echo ""
	@echo "💡 Dashboard will show these URLs automatically"
	@echo "📖 WEBHOOK_PUBLIC_DOMAIN is set to: $(NGROK_DOMAIN)"
	@echo ""
	@ngrok http --url https://$(NGROK_DOMAIN) 8000

clean:
	@echo "🧹 Cleaning build cache..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf .coverage 2>/dev/null || true
	@rm -rf htmlcov 2>/dev/null || true
	@rm -rf .mypy_cache 2>/dev/null || true
	@rm -rf .ruff_cache 2>/dev/null || true
	@echo "✅ Build cache cleaned (data volumes preserved)"

clean-all:
	@echo "⚠️  WARNING: This will delete ALL data including tasks, webhooks, and credentials!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@echo "🧹 Cleaning everything including data volumes..."
	@docker-compose down -v --remove-orphans 2>/dev/null || true
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf .coverage 2>/dev/null || true
	@rm -rf htmlcov 2>/dev/null || true
	@rm -rf .mypy_cache 2>/dev/null || true
	@rm -rf .ruff_cache 2>/dev/null || true
	@echo "✅ Everything cleaned (including data volumes)"

# =============================================================================
# 🗄️ DATABASE COMMANDS
# =============================================================================

db-shell:
	@docker-compose exec app sqlite3 /data/db/machine.db

redis-cli:
	@docker-compose exec redis redis-cli

shell:
	@docker-compose exec app /bin/bash

# =============================================================================
# 🎬 INITIALIZATION
# =============================================================================

init:
	@echo "🎬 Initializing project..."
	@test -f .env || cp .env.example .env
	@uv sync
	@echo ""
	@echo "✅ Project initialized!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run 'make start' to launch the system"
	@echo ""
