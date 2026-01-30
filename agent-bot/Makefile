.PHONY: help build up down logs test clean

help:
	@echo "Agent Bot System - Makefile Commands"
	@echo "======================================"
	@echo "build          - Build all Docker containers"
	@echo "up             - Start all services"
	@echo "down           - Stop all services"
	@echo "logs           - View logs from all services"
	@echo "test           - Run all tests"
	@echo "clean          - Clean up volumes and containers"
	@echo "test-gateway   - Run API Gateway tests"
	@echo "test-github    - Run GitHub Service tests"
	@echo "test-jira      - Run Jira Service tests"
	@echo "test-slack     - Run Slack Service tests"
	@echo "test-sentry    - Run Sentry Service tests"
	@echo "test-agent     - Run Agent Container tests"
	@echo "test-dashboard - Run Dashboard API tests"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test: test-gateway test-github test-jira test-slack test-sentry test-agent test-dashboard

test-gateway:
	cd api-gateway && pytest -v

test-github:
	cd github-service && pytest -v

test-jira:
	cd jira-service && pytest -v

test-slack:
	cd slack-service && pytest -v

test-sentry:
	cd sentry-service && pytest -v

test-agent:
	cd agent-container && pytest -v

test-dashboard:
	cd dashboard-api-container && pytest -v

clean:
	docker-compose down -v
	docker system prune -f
