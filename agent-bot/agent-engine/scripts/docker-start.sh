#!/bin/bash
set -e

echo "Starting agent-engine container..."

# Install Cursor CLI if needed (run as agent user with login shell)
if [ "$CLI_PROVIDER" = "cursor" ] && [ ! -f "/home/agent/.local/bin/agent" ]; then
    echo "Installing Cursor CLI for agent user..."
    runuser -l agent -c 'curl https://cursor.com/install -fsS | bash'

    # Fix permissions on all Cursor CLI binaries
    echo "Setting execute permissions..."
    chmod +x /home/agent/.local/bin/agent 2>/dev/null || true
    chmod +x /home/agent/.local/bin/cursor-agent 2>/dev/null || true
    find /home/agent/.local/share/cursor-agent -type f -name "cursor-agent" -exec chmod +x {} \; 2>/dev/null || true

    # Create CLI config
    runuser -l agent -c 'mkdir -p ~/.cursor && echo "{\"permissions\":{\"allow\":[\"*\"],\"deny\":[]}}" > ~/.cursor/cli-config.json'

    # Verify installation
    if runuser -l agent -c 'agent --version' >/dev/null 2>&1; then
        echo "✅ Cursor CLI installed successfully"
    else
        echo "⚠️  Cursor CLI installed but verification failed"
    fi
fi

# Create wrapper for Cursor CLI so root can use it too
if [ "$CLI_PROVIDER" = "cursor" ] && [ -f "/home/agent/.local/bin/agent" ]; then
    echo "Setting up Cursor CLI wrapper for root access..."
    cat > /usr/local/bin/agent << 'WRAPPER'
#!/bin/bash
if [ "$(id -u)" = "0" ]; then
    exec runuser -l agent -c "cd $(pwd) && /home/agent/.local/bin/agent $*"
else
    exec /home/agent/.local/bin/agent "$@"
fi
WRAPPER
    chmod +x /usr/local/bin/agent
    echo "✅ Cursor CLI accessible as 'agent' command for all users"
fi

# Install dependencies if needed
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
fi

# Ensure Claude credentials are accessible for both root and agent user
# Note: Volume mount at /root/.claude is read-only, so we need writable copies
setup_claude_for_user() {
    local source_dir="$1"
    local target_dir="$2"
    local owner="$3"

    mkdir -p "$target_dir"

    # Copy credentials and config files
    for file in .credentials.json settings.json settings.local.json; do
        if [ -f "$source_dir/$file" ]; then
            cp "$source_dir/$file" "$target_dir/$file"
            chmod 600 "$target_dir/$file"
        fi
    done

    # Copy subdirectories
    for dir in projects todos statsig debug; do
        if [ -d "$source_dir/$dir" ]; then
            cp -r "$source_dir/$dir" "$target_dir/" 2>/dev/null || true
        fi
    done

    # Set ownership
    if [ "$owner" != "root" ]; then
        chown -R "$owner:$owner" "$target_dir"
    fi
}

if [ "$CLI_PROVIDER" = "claude" ]; then
    CREDS_SOURCE=""

    # Find credentials source
    if [ -f "/root/.claude/.credentials.json" ]; then
        CREDS_SOURCE="/root/.claude"
        echo "Claude credentials found in mounted volume"
    elif [ -f "/home/agent/.claude/.credentials.json" ]; then
        CREDS_SOURCE="/home/agent/.claude"
        echo "Claude credentials found in agent home"
    fi

    if [ -n "$CREDS_SOURCE" ]; then
        # Setup for agent user (primary)
        echo "Setting up Claude for agent user..."
        setup_claude_for_user "$CREDS_SOURCE" "/home/agent/.claude" "agent"

        # Setup for root user in /data/.claude (writable location)
        # This avoids conflict with read-only mount at /root/.claude
        echo "Setting up Claude for root user..."
        setup_claude_for_user "$CREDS_SOURCE" "/data/.claude" "root"

        # Create wrapper that runs as agent user when called by root
        # This ensures credentials are always found
        cat > /usr/local/bin/claude-as-agent << 'WRAPPER'
#!/bin/bash
if [ "$(id -u)" = "0" ]; then
    exec runuser -l agent -c "claude $*"
else
    exec /usr/bin/claude "$@"
fi
WRAPPER
        chmod +x /usr/local/bin/claude-as-agent

        # Move original claude and replace with wrapper
        if [ -f "/usr/bin/claude" ] && [ ! -f "/usr/bin/claude-original" ]; then
            mv /usr/bin/claude /usr/bin/claude-original
            cat > /usr/bin/claude << 'WRAPPER'
#!/bin/bash
if [ "$(id -u)" = "0" ]; then
    exec runuser -l agent -c "cd $(pwd) && /usr/bin/claude-original $*"
else
    exec /usr/bin/claude-original "$@"
fi
WRAPPER
            chmod +x /usr/bin/claude
        fi

        echo "✅ Credentials available for both root and agent user"
        echo "   Claude will automatically run as agent user when called by root"
    elif [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "Using ANTHROPIC_API_KEY from environment"
    else
        echo "⚠️  Warning: No Claude credentials found"
    fi
fi

# Test CLI access based on provider - REQUIRED before starting
echo "🧪 Running CLI test before starting application..."
if [ "$CLI_PROVIDER" = "claude" ]; then
    if [ -f "/root/.claude/.credentials.json" ] || [ -f "/home/agent/.claude/.credentials.json" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "Testing Claude CLI access..."
        runuser -l agent -c 'cd /app && python scripts/test_cli.py' || {
            echo "❌ Claude CLI test failed - container will not start"
            exit 1
        }
        runuser -l agent -c 'cd /app && python scripts/log_cli_status.py' || echo "⚠️  Warning: Failed to log CLI status"
        echo "✅ Claude CLI test passed"
    else
        echo "❌ ANTHROPIC_API_KEY not set - container will not start"
        exit 1
    fi
elif [ "$CLI_PROVIDER" = "cursor" ]; then
    if [ -n "$CURSOR_API_KEY" ]; then
        echo "Testing Cursor CLI access..."
        runuser -l agent -c 'cd /app && python scripts/test_cli.py' || {
            echo "❌ Cursor CLI test failed - container will not start"
            exit 1
        }
        runuser -l agent -c 'cd /app && python scripts/log_cli_status.py' || echo "⚠️  Warning: Failed to log CLI status"
        echo "✅ Cursor CLI test passed"
    else
        echo "❌ CURSOR_API_KEY not set - container will not start"
        exit 1
    fi
else
    echo "❌ CLI_PROVIDER not set or invalid - container will not start"
    exit 1
fi

# Setup repositories if configured
if [ -n "$GITHUB_REPOS" ]; then
    echo "Setting up repositories..."
    ./scripts/setup_repos.sh
fi

# Start heartbeat in background
echo "Starting heartbeat monitor..."
python scripts/heartbeat.py &
HEARTBEAT_PID=$!

# Trap signals to cleanup heartbeat on exit
cleanup() {
    echo "Shutting down..."
    if [ ! -z "$HEARTBEAT_PID" ]; then
        kill $HEARTBEAT_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT TERM INT

# Start the main application as agent user
echo "Starting main application as agent user..."
exec runuser -l agent -c 'cd /app && python main.py'
