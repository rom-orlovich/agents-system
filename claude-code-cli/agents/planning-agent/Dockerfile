FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    docker.io \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for MCP servers
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Install MCP servers
RUN npm install -g @sentry/mcp-server@latest \
    @modelcontextprotocol/server-filesystem \
    @modelcontextprotocol/server-github \
    mcp-remote@latest

# Create non-root user for Claude CLI (required for --dangerously-skip-permissions)
RUN useradd -m -s /bin/bash claude \
    && usermod -aG docker claude \
    && echo "claude ALL=(ALL) NOPASSWD: /bin/chown" >> /etc/sudoers.d/claude

# Set up workspace
WORKDIR /app

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv pip install --no-cache --system -r pyproject.toml

# Copy application code
COPY agents/planning-agent/worker.py .
COPY agents/planning-agent/skills/ ./skills/
COPY agents/planning-agent/.claude/ ./.claude/
COPY agents/planning-agent/entrypoint.sh .

# Copy shared utilities
COPY shared /shared

# Create directories, configure permissions, and setup status line hook
RUN mkdir -p /workspace /home/claude/.claude \
    && echo '{"statusLine": {"type": "command", "command": "/shared/scripts/status_monitor.py"}}' > /home/claude/.claude/settings.json \
    && chmod +x /shared/scripts/status_monitor.py \
    && chown -R claude:claude /app /workspace /home/claude \
    && chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CLAUDE_CONFIG_DIR=/home/claude/.claude
ENV HOME=/home/claude
ENV PYTHONPATH=/

# Switch to non-root user
USER claude

# Run entrypoint (checks/refreshes OAuth, then starts worker)
ENTRYPOINT ["./entrypoint.sh"]
