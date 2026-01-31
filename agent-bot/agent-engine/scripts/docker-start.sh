#!/bin/bash
set -e

echo "Starting agent-engine container..."

# Install dependencies if needed
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
fi

# Run CLI test if credentials exist
if [ -f "$HOME/.claude/.credentials.json" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "Testing CLI access..."
    python scripts/test_cli_after_build.py || echo "Warning: CLI test failed"
fi

# Setup repositories if configured
if [ -n "$GITHUB_REPOS" ]; then
    echo "Setting up repositories..."
    ./scripts/setup_repos.sh
fi

# Start the main application
echo "Starting main application..."
exec python main.py
