#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

SERVICE_NAME="$1"
ACTION="${2:-up}"

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: $0 <service-folder-name> [action]"
    echo ""
    echo "Actions:"
    echo "  up       Start service (default)"
    echo "  down     Stop service"
    echo "  restart  Restart service"
    echo "  logs     Show logs"
    echo "  build    Build service"
    echo "  shell    Open shell in container"
    echo ""
    echo "Available services:"
    echo "  oauth-service"
    echo "  api-gateway"
    echo "  dashboard-api"
    echo "  agent-engine"
    echo "  task-logger"
    echo "  knowledge-graph"
    echo "  external-dashboard"
    exit 1
fi

SERVICE_MAP=(
    "oauth-service:oauth-service"
    "api-gateway:api-gateway"
    "dashboard-api:dashboard-api"
    "agent-engine:cli"
    "task-logger:task-logger"
    "knowledge-graph:knowledge-graph"
    "external-dashboard:external-dashboard"
)

DOCKER_SERVICE=""
for mapping in "${SERVICE_MAP[@]}"; do
    folder="${mapping%%:*}"
    docker="${mapping##*:}"
    if [ "$folder" = "$SERVICE_NAME" ]; then
        DOCKER_SERVICE="$docker"
        break
    fi
done

if [ -z "$DOCKER_SERVICE" ]; then
    echo "❌ Unknown service: $SERVICE_NAME"
    echo "Available services: oauth-service, api-gateway, dashboard-api, agent-engine, task-logger, knowledge-graph, external-dashboard"
    exit 1
fi

case "$ACTION" in
    up)
        echo "🚀 Starting $SERVICE_NAME ($DOCKER_SERVICE)..."
        docker-compose up -d "$DOCKER_SERVICE"
        echo "✅ $SERVICE_NAME started"
        ;;
    down)
        echo "🛑 Stopping $SERVICE_NAME ($DOCKER_SERVICE)..."
        docker-compose stop "$DOCKER_SERVICE"
        echo "✅ $SERVICE_NAME stopped"
        ;;
    restart)
        echo "🔄 Restarting $SERVICE_NAME ($DOCKER_SERVICE)..."
        docker-compose restart "$DOCKER_SERVICE"
        echo "✅ $SERVICE_NAME restarted"
        ;;
    logs)
        echo "📋 Showing logs for $SERVICE_NAME ($DOCKER_SERVICE)..."
        docker-compose logs -f "$DOCKER_SERVICE"
        ;;
    build)
        echo "🔨 Building $SERVICE_NAME ($DOCKER_SERVICE)..."
        docker-compose build "$DOCKER_SERVICE"
        echo "✅ $SERVICE_NAME built"
        ;;
    shell)
        CONTAINER_NAME=$(docker-compose ps -q "$DOCKER_SERVICE" | head -1)
        if [ -z "$CONTAINER_NAME" ]; then
            echo "❌ Container for $SERVICE_NAME is not running"
            exit 1
        fi
        echo "🐚 Opening shell in $SERVICE_NAME container..."
        docker exec -it "$CONTAINER_NAME" /bin/bash || docker exec -it "$CONTAINER_NAME" /bin/sh
        ;;
    *)
        echo "❌ Unknown action: $ACTION"
        echo "Available actions: up, down, restart, logs, build, shell"
        exit 1
        ;;
esac
