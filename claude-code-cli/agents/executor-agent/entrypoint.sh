#!/bin/bash
set -e

# Fix workspace permissions if needed (volume may be owned by root)
if [ -d "/workspace" ] && [ ! -w "/workspace" ]; then
    echo "🔧 Fixing /workspace permissions..."
    sudo chown -R claude:claude /workspace 2>/dev/null || true
fi

echo "🔐 Checking Claude OAuth credentials..."

CREDS_FILE="/home/claude/.claude/.credentials.json"

# Check for OAuth credentials file (uses Claude Pro/Team subscription - no extra cost)
if [ -f "$CREDS_FILE" ] && [ -s "$CREDS_FILE" ]; then
    echo "✅ OAuth credentials file found (uses your Claude subscription)"
# Fall back to API key (pay-per-use)
elif [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✅ ANTHROPIC_API_KEY is set (pay-per-use)"
else
    echo "❌ No authentication found"
    echo ""
    echo "Option 1 (Recommended - uses your Claude Pro/Team subscription):"
    echo "  Run on host machine: ./extract-oauth.sh"
    echo "  This extracts OAuth from macOS Keychain to ~/.claude/.credentials.json"
    echo ""
    echo "Option 2 (Pay-per-use API):"
    echo "  Set ANTHROPIC_API_KEY in your .env file"
    echo "  Get key from: https://console.anthropic.com/settings/keys"
    echo ""
    exit 1
fi

echo "🔄 Testing Claude CLI authentication (will auto-refresh if needed)..."

if claude -p "test" --max-turns 1 > /dev/null 2>&1; then
    echo "✅ Claude authentication OK"
else
    echo "❌ Claude authentication failed"
    echo "Error details:"
    claude -p "test" --max-turns 1 2>&1 || true
    exit 1
fi

echo "🚀 Starting Executor Agent Worker..."
exec python worker.py
