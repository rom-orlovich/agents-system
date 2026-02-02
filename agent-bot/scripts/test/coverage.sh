#!/bin/bash
set -e

echo "Running tests with coverage..."

PYTHONPATH=api-gateway:agent-engine:dashboard-api:task-logger:$PYTHONPATH uv run pytest \
    api-gateway/tests/ \
    agent-engine/tests/ \
    dashboard-api/tests/ \
    task-logger/tests/ \
    --cov=. --cov-report=html --cov-report=term-missing -v --tb=short

echo ""
echo "✅ Coverage report generated: htmlcov/index.html"
