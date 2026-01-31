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

# Install dependencies if needed
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
fi

# Test CLI access based on provider and log to database
if [ "$CLI_PROVIDER" = "claude" ]; then
    if [ -f "$HOME/.claude/.credentials.json" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "Testing Claude CLI access..."
        python scripts/test_cli_after_build.py || echo "⚠️  Warning: Claude CLI test failed"
        # Log status to database
        python scripts/log_cli_status.py || echo "⚠️  Warning: Failed to log CLI status"
    else
        echo "⚠️  Warning: ANTHROPIC_API_KEY not set"
    fi
elif [ "$CLI_PROVIDER" = "cursor" ]; then
    if [ -n "$CURSOR_API_KEY" ]; then
        echo "Testing Cursor CLI access..."
        if runuser -l agent -c 'agent --version' >/dev/null 2>&1; then
            CURSOR_VERSION=$(runuser -l agent -c 'agent --version')
            echo "✅ Cursor CLI available: $CURSOR_VERSION"
            # Log status to database
            python scripts/log_cli_status.py || echo "⚠️  Warning: Failed to log CLI status"
        else
            echo "⚠️  Warning: Cursor CLI not working"
        fi
    else
        echo "⚠️  Warning: CURSOR_API_KEY not set"
    fi
fi

# Setup repositories if configured
if [ -n "$GITHUB_REPOS" ]; then
    echo "Setting up repositories..."
    ./scripts/setup_repos.sh
fi

# Start the main application as agent user
echo "Starting main application as agent user..."
exec runuser -l agent -c 'cd /app && python main.py'
