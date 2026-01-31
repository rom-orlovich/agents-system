#!/bin/bash
set -e

echo "Starting agent-engine..."

# Copy Claude credentials from mounted volume (if exists)
if [ -d "/tmp/.claude-host" ] && [ -f "/tmp/.claude-host/.credentials.json" ]; then
    echo "Copying Claude credentials..."
    cp /tmp/.claude-host/.credentials.json "$HOME/.claude/.credentials.json"
    cp /tmp/.claude-host/.claude.json "$HOME/.claude/.claude.json" 2>/dev/null || true
    cp /tmp/.claude-host/settings.json "$HOME/.claude/settings.json" 2>/dev/null || true
    chmod 600 "$HOME/.claude/.credentials.json"
    echo "✅ Credentials copied"
fi

# Install Cursor CLI if needed
if [ "$CLI_PROVIDER" = "cursor" ] && [ ! -f "$HOME/.local/bin/agent" ]; then
    echo "Installing Cursor CLI..."
    curl -fsSL https://cursor.com/install | bash
    chmod +x "$HOME/.local/bin/agent" 2>/dev/null || true
    mkdir -p "$HOME/.cursor"
    echo '{"permissions":{"allow":["*"],"deny":[]}}' > "$HOME/.cursor/cli-config.json"
    echo "✅ Cursor CLI installed"
fi

# Check credentials
check_credentials() {
    if [ "$CLI_PROVIDER" = "claude" ]; then
        if [ -f "$HOME/.claude/.credentials.json" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
            return 0
        fi
    elif [ "$CLI_PROVIDER" = "cursor" ]; then
        if [ -n "$CURSOR_API_KEY" ]; then
            return 0
        fi
    fi
    return 1
}

if ! check_credentials; then
    echo "❌ No credentials found for $CLI_PROVIDER"
    exit 1
fi

# Run CLI test
echo "🧪 Testing $CLI_PROVIDER CLI..."
python scripts/test_cli.py || {
    echo "❌ CLI test failed"
    exit 1
}
echo "✅ CLI test passed"

# Start heartbeat in background
python scripts/heartbeat.py &

# Start main application
echo "Starting main application..."
exec python main.py
