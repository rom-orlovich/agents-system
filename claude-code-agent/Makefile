.PHONY: help install dev test lint format clean build up down logs restart

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies with uv
	uv sync

dev: ## Install dev dependencies
	uv sync --all-extras

test: ## Run tests
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=. --cov-report=html --cov-report=term

lint: ## Run linting
	uv run ruff check .

format: ## Format code
	uv run ruff format .

type-check: ## Run type checking
	uv run mypy .

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache

# Docker commands
build: ## Build Docker containers
	docker-compose build

up: ## Start services
	docker-compose up -d

down: ## Stop services
	docker-compose down

logs: ## View logs
	docker-compose logs -f

restart: ## Restart services
	docker-compose restart

ps: ## Show running containers
	docker-compose ps

# Database commands
db-shell: ## Open SQLite shell
	docker-compose exec app sqlite3 /data/db/machine.db

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

# Development
run-local: ## Run locally (no Docker)
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

shell: ## Open shell in container
	docker-compose exec app /bin/bash

# Initialization
init: ## Initialize project (first time setup)
	cp .env.example .env
	uv sync
	@echo "Project initialized! Edit .env and run 'make up'"
