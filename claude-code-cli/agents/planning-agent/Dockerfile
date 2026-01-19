FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for MCP servers
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Install MCP servers
RUN npm install -g @sentry/mcp-server@latest \
    @modelcontextprotocol/server-filesystem

# Set up workspace
WORKDIR /app

# Copy requirements first for better caching
COPY agents/planning-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agents/planning-agent/worker.py .
COPY agents/planning-agent/skills/ ./skills/

# Copy shared utilities
COPY shared /shared

# Create workspace directory
RUN mkdir -p /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CLAUDE_CONFIG_DIR=/root/.claude

# Run worker
CMD ["python", "worker.py"]
