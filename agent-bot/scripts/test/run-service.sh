#!/bin/bash
set -e

SERVICE="$1"

if [ -z "$SERVICE" ]; then
    echo "Usage: $0 <service-name>"
    echo "Available services: api-gateway, agent-engine, dashboard-api, task-logger, github-api, jira-api, slack-api, sentry-api"
    exit 1
fi

case "$SERVICE" in
    api-gateway)
        echo "Running API Gateway tests..."
        PYTHONPATH=api-gateway:$PYTHONPATH uv run pytest api-gateway/tests/ -v --tb=short
        ;;
    agent-engine)
        echo "Running Agent Engine tests..."
        PYTHONPATH=agent-engine:$PYTHONPATH uv run pytest agent-engine/tests/ -v --tb=short
        ;;
    dashboard|dashboard-api)
        echo "Running Dashboard API tests..."
        PYTHONPATH=dashboard-api:$PYTHONPATH uv run pytest dashboard-api/tests/ -v --tb=short
        ;;
    task-logger|logger)
        echo "Running Task Logger tests..."
        PYTHONPATH=task-logger:$PYTHONPATH uv run pytest task-logger/tests/ -v --tb=short
        ;;
    github-api|github)
        echo "Running GitHub API tests..."
        uv run pytest api-services/github-api/tests/ -v --tb=short
        ;;
    jira-api|jira)
        echo "Running Jira API tests..."
        uv run pytest api-services/jira-api/tests/ -v --tb=short
        ;;
    slack-api|slack)
        echo "Running Slack API tests..."
        uv run pytest api-services/slack-api/tests/ -v --tb=short
        ;;
    sentry-api|sentry)
        echo "Running Sentry API tests..."
        uv run pytest api-services/sentry-api/tests/ -v --tb=short
        ;;
    services)
        echo "Running API Services tests..."
        uv run pytest api-services/github-api/tests/ api-services/jira-api/tests/ api-services/slack-api/tests/ api-services/sentry-api/tests/ -v --tb=short
        ;;
    *)
        echo "Unknown service: $SERVICE"
        echo "Available services: api-gateway, agent-engine, dashboard-api, task-logger, github-api, jira-api, slack-api, sentry-api, services"
        exit 1
        ;;
esac

echo ""
echo "✅ Tests passed!"
