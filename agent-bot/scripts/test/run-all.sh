#!/bin/bash
set -e

echo "Running all tests..."
echo ""

echo "=== API Gateway Tests ==="
PYTHONPATH=api-gateway:$PYTHONPATH uv run pytest api-gateway/tests/ -v --tb=short

echo ""
echo "=== Dashboard API Tests ==="
PYTHONPATH=dashboard-api:$PYTHONPATH uv run pytest dashboard-api/tests/ -v --tb=short

echo ""
echo "=== Agent Engine Tests ==="
PYTHONPATH=agent-engine:$PYTHONPATH uv run pytest agent-engine/tests/ -v --tb=short

echo ""
echo "=== Task Logger Tests ==="
PYTHONPATH=task-logger:$PYTHONPATH uv run pytest task-logger/tests/ -v --tb=short

echo ""
echo "=== API Services Tests ==="
uv run pytest api-services/github-api/tests/ -v --tb=short
uv run pytest api-services/jira-api/tests/ -v --tb=short
uv run pytest api-services/slack-api/tests/ -v --tb=short
uv run pytest api-services/sentry-api/tests/ -v --tb=short

echo ""
echo "✅ All tests passed!"
