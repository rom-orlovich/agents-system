.PHONY: help init build up down restart logs logs-follow test test-unit test-integration coverage format lint db-migrate db-upgrade db-downgrade db-shell redis-cli clean health oauth-setup build-services up-services down-services health-services build-all up-all down-all health-all

help:
	@echo "Agent Bot - Makefile Commands"
	@echo "=============================="
	@echo "Setup:"
	@echo "  make init              - Initialize project (create .env, install deps)"
	@echo "  make oauth-setup       - Setup OAuth for integrations"
	@echo ""
	@echo "Docker (Infrastructure):"
	@echo "  make build             - Build infrastructure containers"
	@echo "  make up                - Start infrastructure services"
	@echo "  make down              - Stop all services"
	@echo "  make restart           - Restart all services"
	@echo "  make logs              - View all logs"
	@echo "  make logs-follow       - Follow logs in real-time"
	@echo ""
	@echo "Docker (API Services):"
	@echo "  make build-services    - Build API service containers"
	@echo "  make up-services       - Start API services"
	@echo "  make down-services     - Stop API services"
	@echo "  make health-services   - Check API service health"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate        - Create new migration"
	@echo "  make db-upgrade        - Apply migrations"
	@echo "  make db-downgrade      - Rollback migration"
	@echo "  make db-shell          - Open database shell"
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run unit tests"
	@echo "  make test-integration  - Run integration tests"
	@echo "  make coverage          - Generate coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format            - Format code with black/isort"
	@echo "  make lint              - Run linting"
	@echo ""
	@echo "Monitoring:"
	@echo "  make health            - Check service health"
	@echo "  make redis-cli         - Open Redis CLI"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Remove containers, volumes, and cache"
	@echo ""
	@echo "Complete System:"
	@echo "  make build-all         - Build all containers"
	@echo "  make up-all            - Start complete system"
	@echo "  make down-all          - Stop complete system"
	@echo "  make health-all        - Check all services"

init:
	@echo "Initializing Agent Bot..."
	@cp -n .env.example .env 2>/dev/null || true
	@echo ".env file created (if it didn't exist)"
	@echo "Please edit .env with your configuration"

oauth-setup:
	@echo "Starting OAuth setup..."
	@bash scripts/oauth-setup.sh

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services started. API Gateway: http://localhost:8000"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs

logs-follow:
	docker-compose logs -f

test:
	pytest -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

coverage:
	pytest --cov=. --cov-report=html --cov-report=term

format:
	@echo "Formatting code..."
	black .
	isort .

lint:
	@echo "Running linters..."
	flake8 .
	mypy .

db-migrate:
	@read -p "Migration message: " msg; \
	docker-compose exec api-gateway alembic revision --autogenerate -m "$$msg"

db-upgrade:
	docker-compose exec api-gateway alembic upgrade head

db-downgrade:
	docker-compose exec api-gateway alembic downgrade -1

db-shell:
	docker-compose exec postgres psql -U agentbot -d agentbot

redis-cli:
	docker-compose exec redis redis-cli

build-services:
	@echo "Building API services..."
	cd integrations/api && docker-compose -f docker-compose.services.yml build

up-services:
	@echo "Starting API services..."
	cd integrations/api && docker-compose -f docker-compose.services.yml up -d
	@echo "API Services started:"
	@echo "  GitHub API: http://localhost:3001"
	@echo "  Jira API: http://localhost:3002"
	@echo "  Slack API: http://localhost:3003"
	@echo "  Sentry API: http://localhost:3004"

down-services:
	cd integrations/api && docker-compose -f docker-compose.services.yml down

health:
	@echo "Checking infrastructure health..."
	@curl -s http://localhost:8000/health || echo "API Gateway: DOWN"

health-services:
	@echo "Checking API service health..."
	@curl -s http://localhost:3001/health || echo "GitHub API: DOWN"
	@curl -s http://localhost:3002/health || echo "Jira API: DOWN"
	@curl -s http://localhost:3003/health || echo "Slack API: DOWN"
	@curl -s http://localhost:3004/health || echo "Sentry API: DOWN"

build-all:
	@echo "Building complete system..."
	docker-compose -f docker-compose.complete.yml build

up-all:
	@echo "Starting complete system..."
	docker-compose -f docker-compose.complete.yml up -d
	@echo "Complete system started:"
	@echo "  API Gateway: http://localhost:8000"
	@echo "  Dashboard API: http://localhost:8090"
	@echo "  External Dashboard: http://localhost:3005"
	@echo "  Knowledge Graph: http://localhost:4000"

down-all:
	docker-compose -f docker-compose.complete.yml down

health-all:
	@echo "Checking all services..."
	@curl -s http://localhost:8000/health || echo "API Gateway: DOWN"
	@curl -s http://localhost:3001/health || echo "GitHub API: DOWN"
	@curl -s http://localhost:3002/health || echo "Jira API: DOWN"
	@curl -s http://localhost:3003/health || echo "Slack API: DOWN"
	@curl -s http://localhost:3004/health || echo "Sentry API: DOWN"
	@curl -s http://localhost:8090/health || echo "Dashboard API: DOWN"
	@curl -s http://localhost:4000/health || echo "Knowledge Graph: DOWN"

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker-compose -f docker-compose.complete.yml down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"
