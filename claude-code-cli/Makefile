.PHONY: help setup env oauth up down logs test clean tunnel skills health

help:
	@echo "AI Agent System - Claude Code CLI"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup    - Initial setup (prerequisites, env, OAuth, skills)"
	@echo "  make env      - Edit environment variables (.env)"
	@echo "  make oauth    - Extract OAuth from Keychain (uses your Claude subscription)"
	@echo "  make skills   - Setup Claude Code skills (lazy loading)"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - View logs"
	@echo "  make test     - Run tests"
	@echo "  make health   - Run health check"
	@echo "  make tunnel   - Setup Cloudflare Tunnel (FREE persistent webhooks)"
	@echo "  make clean    - Clean up volumes and images"
	@echo ""

env:
	@test -f infrastructure/docker/.env || { echo "Creating .env from example..."; cp infrastructure/docker/.env.example infrastructure/docker/.env; }
	nano infrastructure/docker/.env

setup:
	@echo "🔧 Setting up Claude Code CLI system..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker not installed"; exit 1; }
	@command -v claude >/dev/null 2>&1 || { echo "⚠️  Claude CLI not found, installing..."; npm install -g @anthropic-ai/claude-code; }
	@test -d ~/.claude || { echo "❌ Claude not authenticated. Run 'claude login' first"; exit 1; }
	@echo "✅ Prerequisites OK"
	@echo "📄 Checking environment file..."
	@test -f infrastructure/docker/.env || { echo "Creating .env from example..."; cp infrastructure/docker/.env.example infrastructure/docker/.env; echo "⚠️  Please edit infrastructure/docker/.env with your credentials"; }
	@echo "🔑 Extracting OAuth credentials from Keychain..."
	@./infrastructure/docker/extract-oauth.sh || echo "⚠️  OAuth extraction failed. You can use ANTHROPIC_API_KEY instead."
	@echo "📦 Setting up skills..."
	@./scripts/setup-skills.sh
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env:  make env"
	@echo "  2. Start:      make up"
	@echo "  3. Tunnel:     make tunnel"

oauth:
	@echo "🔑 Extracting OAuth credentials from macOS Keychain..."
	@./infrastructure/docker/extract-oauth.sh

skills:
	@echo "📦 Setting up Claude Code skills..."
	@./scripts/setup-skills.sh

up:
	@echo "🔑 Refreshing OAuth credentials from Keychain..."
	@./infrastructure/docker/extract-oauth.sh || echo "⚠️  OAuth extraction failed. Containers will use ANTHROPIC_API_KEY if set."
	@echo "🚀 Starting AI Agent System..."
	cd infrastructure/docker && docker-compose up -d
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo ""
	@echo "✅ System is running!"
	@echo ""
	@echo "🔗 Webhook Server: http://localhost:8000"
	@echo "📊 Health:         http://localhost:8000/health"
	@echo ""
	@echo "View logs with: make logs"
	@echo "Health check:   make health"

down:
	@echo "🛑 Stopping AI Agent System..."
	cd infrastructure/docker && docker-compose down
	@echo "✅ System stopped"

logs:
	@cd infrastructure/docker && docker-compose logs -f

test:
	@echo "🧪 Running tests..."
	pytest tests/ -v

health:
	@echo "🏥 Running health check..."
	@./scripts/health-check.sh

tunnel:
	@echo "🌐 Setting up Cloudflare Tunnel (FREE)..."
	@./scripts/setup-tunnel.sh

clean:
	@echo "🧹 Cleaning up..."
	cd infrastructure/docker && docker-compose down -v
	rm -rf shared/__pycache__ shared/commands/__pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -delete
	@echo "✅ Cleaned up"
