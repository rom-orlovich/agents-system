#!/bin/bash
set -e

PROVIDER="${1:-claude}"
SCALE="${2:-1}"
DC="docker-compose"

echo "Starting $PROVIDER CLI..."

$DC up -d redis postgres 2>/dev/null || true
docker network create agent-network 2>/dev/null || true

CLI_PROVIDER="$PROVIDER" $DC -f docker-compose.cli.yml -p "$PROVIDER-cli" --env-file .env build cli

EXISTING=$(docker ps --filter "name=$PROVIDER-cli-cli" -q | wc -l | tr -d ' ')
TARGET="${SCALE:-$((EXISTING + 1))}"
[ "$TARGET" -lt 1 ] && TARGET=1

echo "Scaling to $TARGET instance(s)..."
CLI_PROVIDER="$PROVIDER" $DC -f docker-compose.cli.yml -p "$PROVIDER-cli" --env-file .env up -d --scale cli="$TARGET" cli

echo "✅ $PROVIDER CLI started"
$DC -f docker-compose.cli.yml -p "$PROVIDER-cli" ps cli
