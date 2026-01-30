#!/bin/bash

set -e

echo "=================================================="
echo "Agent Bot Production Deployment Validation"
echo "=================================================="
echo ""

FAILED_CHECKS=0

check_command() {
    if command -v "$1" &> /dev/null; then
        echo "✅ $1 is installed"
        return 0
    else
        echo "❌ $1 is not installed"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_service() {
    SERVICE=$1
    echo -n "Checking $SERVICE... "

    if docker compose ps | grep -q "$SERVICE.*running"; then
        echo "✅ Running"
        return 0
    else
        echo "❌ Not running"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_health() {
    SERVICE=$1
    URL=$2
    echo -n "Checking $SERVICE health endpoint... "

    if curl -s -f "$URL" > /dev/null; then
        echo "✅ Healthy"
        return 0
    else
        echo "❌ Unhealthy"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

echo "Step 1: Checking Prerequisites"
echo "--------------------------------"
check_command "docker"
check_command "docker compose" || check_command "docker-compose"
check_command "psql"
check_command "redis-cli"
echo ""

echo "Step 2: Checking Docker Services"
echo "--------------------------------"
check_service "postgres"
check_service "redis"
check_service "api-gateway"
check_service "agent-container"
echo ""

echo "Step 3: Checking Health Endpoints"
echo "--------------------------------"
check_health "API Gateway" "http://localhost:8080/health"
check_health "OAuth" "http://localhost:8080/oauth/health"
check_health "Webhooks" "http://localhost:8080/webhooks/health"
echo ""

echo "Step 4: Checking Database Schema"
echo "--------------------------------"
echo -n "Checking installations table... "
if docker compose exec -T postgres psql -U agent -d agent_bot -c "\dt installations" | grep -q "installations"; then
    echo "✅ Exists"
else
    echo "❌ Missing"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo -n "Checking tasks table... "
if docker compose exec -T postgres psql -U agent -d agent_bot -c "\dt tasks" | grep -q "tasks"; then
    echo "✅ Exists"
else
    echo "❌ Missing"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
echo ""

echo "Step 5: Checking Redis Connection"
echo "--------------------------------"
echo -n "Redis ping... "
if docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Connected"
else
    echo "❌ Failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo -n "Queue exists... "
if docker compose exec -T redis redis-cli EXISTS "agent:tasks" > /dev/null; then
    echo "✅ Queue ready"
else
    echo "⚠️  Queue not initialized (will be created on first use)"
fi
echo ""

echo "Step 6: Checking Logs for Errors"
echo "--------------------------------"
echo "API Gateway last 10 logs:"
docker compose logs --tail=10 api-gateway
echo ""
echo "Agent Container last 10 logs:"
docker compose logs --tail=10 agent-container
echo ""

echo "Step 7: Testing Webhook Endpoint"
echo "--------------------------------"
echo -n "Testing GitHub webhook signature validation... "
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8080/webhooks/github \
    -H "Content-Type: application/json" \
    -d '{"test": "data"}')

if [ "$RESPONSE" == "401" ]; then
    echo "✅ Signature validation working"
else
    echo "⚠️  Got response code: $RESPONSE (expected 401)"
fi
echo ""

echo "=================================================="
echo "Validation Summary"
echo "=================================================="
if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✅ All checks passed! System is production ready."
    exit 0
else
    echo "❌ $FAILED_CHECKS check(s) failed. Please review and fix issues."
    exit 1
fi
