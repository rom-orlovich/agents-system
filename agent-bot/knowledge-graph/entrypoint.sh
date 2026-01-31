#!/bin/bash
set -e

echo "Starting Knowledge Graph Service..."

if [ -f "/app/scripts/sync-repos.sh" ]; then
    echo "Running initial repository sync..."
    /app/scripts/sync-repos.sh || echo "Initial sync skipped (no repos configured)"
fi

echo "Starting Rust API server on port ${PORT:-4000}..."
exec /app/knowledge-graph &
API_PID=$!

sleep 2

if [ "${ENABLE_GKG_SERVER:-false}" = "true" ]; then
    echo "Starting gkg web interface on port ${GKG_WEB_PORT:-4001}..."
    cd "${GKG_DATA_DIR:-/data/graphs}"
    gkg server start --port "${GKG_WEB_PORT:-4001}" &
    GKG_PID=$!
fi

wait $API_PID
