#!/bin/bash
set -e

PROVIDER="${1:-claude}"
DC="docker-compose"

echo "Stopping $PROVIDER CLI..."
$DC -f docker-compose.cli.yml -p "$PROVIDER-cli" down 2>/dev/null || true
echo "✅ $PROVIDER CLI stopped"
