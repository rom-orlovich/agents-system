#!/bin/bash
set -e

DC="docker-compose"

echo "Starting Agent Bot services..."

test -f .env || cp .env.example .env

$DC build --quiet
$DC up -d

sleep 5

echo "Checking services..."
./scripts/services/health.sh

echo ""
echo "✅ Agent Bot ready"
echo "   API Gateway: http://localhost:8000"
echo "   Dashboard:   http://localhost:3005"
echo "   Dashboard API: http://localhost:5000"
