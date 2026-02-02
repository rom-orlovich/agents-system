#!/bin/bash

cat << 'EOF'
Agent Bot Commands
==================

CLI:
  make cli PROVIDER=claude SCALE=1    Start Claude CLI
  make cli PROVIDER=cursor SCALE=1    Start Cursor CLI
  make cli-claude                     Start Claude CLI (shortcut)
  make cli-cursor                     Start Cursor CLI (shortcut)
  make cli-down PROVIDER=claude       Stop CLI
  make cli-logs PROVIDER=claude       View CLI logs

Services:
  make up                             Start all services
  make down                           Stop all services
  make health                         Check service health
  make logs SERVICE=api-gateway       View service logs

Testing:
  make test                           Run all tests
  make test-api-gateway               Run API Gateway tests
  make test-agent-engine              Run Agent Engine tests
  make test-dashboard                 Run Dashboard API tests
  make test-logger                    Run Task Logger tests
  make test-services                  Run API Services tests
  make test-cov                       Run tests with coverage

Database:
  make db-migrate MSG="..."           Create migration
  make db-upgrade                     Apply migrations

Code Quality:
  make lint                           Run ruff linter
  make format                         Auto-format with ruff
  make clean                          Clean cache directories

Environment:
  make init                           Initialize project
  make env-validate                   Validate .env file

Ports:
  8000  - API Gateway
  8080  - Agent Engine
  5000  - Dashboard API
  3005  - External Dashboard
  8010  - OAuth Service
  8001  - ChromaDB
  6379  - Redis
  5432  - PostgreSQL
EOF
