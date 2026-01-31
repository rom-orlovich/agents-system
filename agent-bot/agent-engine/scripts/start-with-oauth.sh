#!/bin/bash
# Automated startup script for agent-engine with OAuth credentials
# This script:
# 1. Extracts OAuth credentials from macOS Keychain
# 2. Starts Docker containers with credentials mounted

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_ENGINE_DIR="$(dirname "$SCRIPT_DIR")"
CREDS_FILE="$HOME/.claude/.credentials.json"

echo "🚀 Starting Agent Engine with OAuth credentials..."
echo ""

# Step 1: Extract OAuth credentials
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📋 Step 1: Extracting OAuth credentials from Keychain..."
    "$SCRIPT_DIR/extract_oauth_creds.sh" "$CREDS_FILE"
    echo ""
else
    echo "⚠️  Warning: Not running on macOS, skipping credential extraction"
    echo "   Please ensure ANTHROPIC_API_KEY is set or credentials are available"
    echo ""
fi

# Step 2: Update docker-compose to mount credentials
cd "$AGENT_ENGINE_DIR"

# Check if credentials file exists
if [ -f "$CREDS_FILE" ]; then
    echo "✅ Credentials found at: $CREDS_FILE"
    echo ""
    echo "📦 Step 2: Starting Docker containers with credentials..."

    # Start with credentials mounted
    docker-compose -f docker-compose.agent.yml up -d

    # Wait for health check
    echo ""
    echo "⏳ Waiting for containers to be healthy..."
    sleep 5

    # Test health
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ Agent Engine is healthy!"
        echo ""
        echo "🎉 Setup complete!"
        echo ""
        echo "Useful commands:"
        echo "  docker-compose -f docker-compose.agent.yml logs -f    # View logs"
        echo "  docker-compose -f docker-compose.agent.yml ps         # Check status"
        echo "  docker-compose -f docker-compose.agent.yml down       # Stop services"
    else
        echo "⚠️  Warning: Health check failed"
        echo "   Check logs: docker-compose -f docker-compose.agent.yml logs"
    fi
else
    echo "❌ No credentials found. Please either:"
    echo "   1. Run 'claude login' first, then run this script again"
    echo "   2. Set ANTHROPIC_API_KEY in .env file"
    exit 1
fi
