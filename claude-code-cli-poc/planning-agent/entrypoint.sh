#!/bin/bash
# Planning Agent Entry Point

set -e

echo "Starting Planning Agent..."
echo "Workspace: /workspace"
echo "Claude Config: ${CLAUDE_CONFIG_DIR:-/root/.claude}"

# Verify Claude CLI is available
if ! command -v claude &> /dev/null; then
    echo "ERROR: Claude CLI not found"
    exit 1
fi

# Verify authentication
if [ ! -f "${CLAUDE_CONFIG_DIR:-/root/.claude}/config.json" ]; then
    echo "WARNING: Claude CLI not authenticated"
    echo "Please mount ~/.claude volume or run 'claude login'"
fi

# Run the worker
exec python /app/planning_agent/worker.py
