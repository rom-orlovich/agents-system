.PHONY: help start up down restart logs test clean tunnel oauth health build rebuild env

# Load environment variables if they exist
-include infrastructure/docker/.env
export


# ngrok static domain - set this in your CLI or .env!
# Example: NGROK_DOMAIN=your-name.ngrok-free.app
NGROK_DOMAIN ?= 

# =============================================================================
# HELP
# =============================================================================

help:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║        🤖 AI Agent System - Claude Code CLI                  ║"
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
	@echo "🔧 UTILITIES"
	@echo "───────────────────────────────────────────────────────────────"
	@echo "  make oauth     - Refresh OAuth credentials"
	@echo "  make env       - Edit .env file"
	@echo "  make health    - Health check"
	@echo "  make tunnel    - Start ngrok tunnel (Permanent URL!)"
	@echo "  make clean     - Cleanup everything"
	@echo ""

# =============================================================================
# 🚀 MAIN COMMANDS
# =============================================================================

# 🎯 ONE COMMAND TO RULE THEM ALL
start:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║        🚀 Starting AI Agent System                           ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@# Prerequisites
	@echo " Checking prerequisites..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker required. Get it from https://docker.com"; exit 1; }
	@command -v claude >/dev/null 2>&1 || { echo "⚠️  Installing Claude CLI..."; npm install -g @anthropic-ai/claude-code; }
	@test -d ~/.claude || { echo "❌ Run 'claude login' first"; exit 1; }
	@echo "✅ Prerequisites OK"
	@echo ""
	@# Environment
	@test -f infrastructure/docker/.env || { echo "📄 Creating .env..."; cp infrastructure/docker/.env.example infrastructure/docker/.env; }
	@# OAuth
	@echo "🔑 Extracting OAuth credentials..."
	@./infrastructure/docker/extract-oauth.sh 2>/dev/null || echo "⚠️  OAuth failed, using API key if set"
	@echo ""
	@# Build & Start
	@echo "� Building containers..."
	@cd infrastructure/docker && docker-compose build --quiet
	@echo "🚀 Starting services..."
	@cd infrastructure/docker && docker-compose up -d
	@sleep 8
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║        ✅ System Ready!                                      ║"
	@echo "╠══════════════════════════════════════════════════════════════╣"
	@echo "║  🔗 Webhook:  http://localhost:8000                          ║"
	@echo "║  � Health:   http://localhost:8000/health                   ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  make logs    - View logs"
	@echo "  make tunnel  - Enable external webhooks"
	@echo ""

up:
	@echo "🔑 Refreshing OAuth..."
	@./infrastructure/docker/extract-oauth.sh 2>/dev/null || true
	@echo "🚀 Starting services..."
	@cd infrastructure/docker && docker-compose up -d
	@sleep 5
	@echo "✅ Running at http://localhost:8000"

down:
	@echo "🛑 Stopping..."
	@cd infrastructure/docker && docker-compose down
	@echo "✅ Stopped"

restart: down up

logs:
	@cd infrastructure/docker && docker-compose logs -f

# =============================================================================
# � UTILITIES
# =============================================================================

oauth:
	@echo "� Extracting OAuth from Keychain..."
	@./infrastructure/docker/extract-oauth.sh

env:
	@test -f infrastructure/docker/.env || cp infrastructure/docker/.env.example infrastructure/docker/.env
	@nano infrastructure/docker/.env

health:
	@./scripts/health-check.sh

build:
	@cd infrastructure/docker && docker-compose build

rebuild: down clean build up

tunnel:
	@command -v ngrok >/dev/null 2>&1 || { echo "📦 Installing ngrok via Homebrew..."; brew install ngrok; }
	@if [ -z "$(NGROK_DOMAIN)" ]; then \
		echo "❌ NGROK_DOMAIN is not set!"; \
		echo "Please set it: make tunnel NGROK_DOMAIN=your-name.ngrok-free.app"; \
		exit 1; \
	fi
	@echo ""
	@echo "🌐 Webhook URLs (Permanent!):"
	@echo "  GitHub: https://$(NGROK_DOMAIN)/webhooks/github"
	@echo "  Jira:   https://$(NGROK_DOMAIN)/webhooks/jira"
	@echo "  Sentry: https://$(NGROK_DOMAIN)/webhooks/sentry"
	@echo ""
	@ngrok http --url $(NGROK_DOMAIN) 8000

test:
	@pytest tests/ -v

clean:
	@echo "🧹 Cleaning..."
	@cd infrastructure/docker && docker-compose down -v --remove-orphans 2>/dev/null || true
	@docker system prune -f 2>/dev/null || true
	@find . -name "__pycache__" -type d -delete 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Clean"
