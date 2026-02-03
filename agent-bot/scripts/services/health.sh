#!/bin/bash

DC="docker-compose"

echo "Service Health:"

curl -sf http://localhost:8000/health >/dev/null 2>&1 && echo "  ✅ API Gateway (8000)" || echo "  ❌ API Gateway (8000)"
curl -sf http://localhost:8080/health >/dev/null 2>&1 && echo "  ✅ Agent Engine (8080)" || echo "  ❌ Agent Engine (8080)"
curl -sf http://localhost:5000/api/health >/dev/null 2>&1 && echo "  ✅ Dashboard API (5000)" || echo "  ❌ Dashboard API (5000)"
curl -sf http://localhost:8010/health >/dev/null 2>&1 && echo "  ✅ OAuth Service (8010)" || echo "  ❌ OAuth Service (8010)"
curl -sf http://localhost:8001/api/v1/heartbeat >/dev/null 2>&1 && echo "  ✅ ChromaDB (8001)" || echo "  ❌ ChromaDB (8001)"

$DC exec -T redis redis-cli ping >/dev/null 2>&1 && echo "  ✅ Redis (6379)" || echo "  ❌ Redis (6379)"
$DC exec -T postgres pg_isready -U agent >/dev/null 2>&1 && echo "  ✅ PostgreSQL (5432)" || echo "  ❌ PostgreSQL (5432)"
