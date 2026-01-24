#!/bin/bash
set -e

# Fix workspace permissions if needed (volume may be owned by root)
if [ -d "/workspace" ] && [ ! -w "/workspace" ]; then
    echo "🔧 Fixing /workspace permissions..."
    sudo chown -R claude:claude /workspace 2>/dev/null || true
fi

# =============================================================================
# OAuth Token Auto-Refresh
# =============================================================================
# =============================================================================
# OAuth Token Auto-Refresh
# =============================================================================
# Sync credentials from host mount (Hybrid Architecture)
if [ -d "/host_claude_config" ]; then
    echo "🔐 Syncing credentials from host..."
    mkdir -p /home/claude/.claude
    cp -r /host_claude_config/. /home/claude/.claude/ 2>/dev/null || true
fi

if [ -f "/host_claude.json" ]; then
    cp /host_claude.json /home/claude/.claude.json 2>/dev/null || true
fi

# Enforce status line settings
echo '{"statusLine": {"type": "command", "command": "/shared/scripts/status_monitor.py"}}' > /home/claude/.claude/settings.json
chown -R claude:claude /home/claude 2>/dev/null || true

# Uses TokenManager to check and auto-refresh expired tokens before CLI test

echo "🔐 Checking Claude OAuth credentials (with auto-refresh)..."

# Call Python script to check/refresh OAuth tokens
AUTH_EXIT_CODE=0
python -c "from shared.ensure_auth import main; exit(main())" || AUTH_EXIT_CODE=$?

case $AUTH_EXIT_CODE in
    0)
        echo "✅ OAuth authentication ready"
        ;;
    2)
        echo "✅ Using ANTHROPIC_API_KEY (pay-per-use)"
        ;;
    *)
        echo "❌ Authentication failed"
        echo ""
        echo "Option 1 (Recommended - uses your Claude Pro/Team subscription):"
        echo "  Run on host machine: ./infrastructure/docker/extract-oauth.sh"
        echo "  This extracts OAuth from macOS Keychain to ~/.claude/.credentials.json"
        echo ""
        echo "Option 2 (Pay-per-use API):"
        echo "  Set ANTHROPIC_API_KEY in your .env file"
        echo "  Get key from: https://console.anthropic.com/settings/keys"
        echo ""
        exit 1
        ;;
esac

# Quick verification with Claude CLI
echo "🔄 Verifying Claude CLI..."

if timeout 30 claude -p "respond with OK" --max-turns 1 > /dev/null 2>&1; then
    echo "✅ Claude CLI verified"
else
    echo "⚠️  Claude CLI verification failed (might be rate limited), but proceeding anyway..."
fi

echo "🚀 Starting Executor Agent Worker..."
exec python worker.py
