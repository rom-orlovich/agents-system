FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    docker.io \
    build-essential \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Install MCP servers
RUN npm install -g @modelcontextprotocol/server-filesystem

# Create non-root user for Claude CLI (required for --dangerously-skip-permissions)
RUN useradd -m -s /bin/bash claude \
    && usermod -aG docker claude \
    && echo "claude ALL=(ALL) NOPASSWD: /bin/chown" >> /etc/sudoers.d/claude

WORKDIR /app

# Copy requirements and install
COPY agents/executor-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agents/executor-agent/worker.py .
COPY agents/executor-agent/skills/ ./skills/
COPY agents/executor-agent/entrypoint.sh .

# Copy shared utilities
COPY shared /shared

# Create directories and set permissions
RUN mkdir -p /workspace /home/claude/.claude \
    && chown -R claude:claude /app /workspace /home/claude \
    && chmod +x entrypoint.sh

# Configure Git for claude user
RUN su claude -c 'git config --global user.email "ai-agent@company.com"' \
    && su claude -c 'git config --global user.name "AI Agent"'

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CLAUDE_CONFIG_DIR=/home/claude/.claude
ENV HOME=/home/claude

# Switch to non-root user
USER claude

# Run entrypoint (checks/refreshes OAuth, then starts worker)
ENTRYPOINT ["./entrypoint.sh"]
