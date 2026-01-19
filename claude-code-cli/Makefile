.PHONY: help setup env up down logs test clean ngrok

help:
	@echo "AI Agent System - Claude Code CLI"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup    - Initial setup (install dependencies)"
	@echo "  make env      - Edit environment variables (.env)"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - View logs"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Clean up volumes and images"
	@echo "  make ngrok    - Expose webhook server to the internet via ngrok"
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
	@test -f infrastructure/docker/.env || { echo "Creating .env from example..."; cp infrastructure/docker/.env.example infrastructure/docker/.env; echo "⚠️  Please edit infrastructure/docker/.env with your credentials"; exit 0; }
	@echo "✅ Setup complete!"

up:
	@echo "🚀 Starting AI Agent System..."
	cd infrastructure/docker && docker-compose up -d
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo ""
	@echo "✅ System is running!"
	@echo ""
	@echo "📊 Dashboard:      http://localhost:3000 (not yet implemented)"
	@echo "🔗 Webhook Server: http://localhost:8000"
	@echo "📈 Metrics:        http://localhost:8000/metrics"
	@echo ""
	@echo "View logs with: make logs"

down:
	@echo "🛑 Stopping AI Agent System..."
	cd infrastructure/docker && docker-compose down
	@echo "✅ System stopped"

logs:
	@cd infrastructure/docker && docker-compose logs -f

test:
	@echo "🧪 Running tests..."
	pytest tests/ -v

clean:
	@echo "🧹 Cleaning up..."
	cd infrastructure/docker && docker-compose down -v
	@echo "✅ Cleaned up volumes"

ngrok:
	@echo "🌐 Exposing port 8000 via ngrok..."
	ngrok http 8000

