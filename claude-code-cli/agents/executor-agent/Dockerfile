FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    docker.io \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Install MCP servers
RUN npm install -g @modelcontextprotocol/server-filesystem

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY worker.py .
COPY skills/ ./skills/

# Copy shared utilities
COPY ../../shared /app/shared

# Create workspace directory
RUN mkdir -p /workspace

# Configure Git
RUN git config --global user.email "ai-agent@company.com" \
    && git config --global user.name "AI Agent"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CLAUDE_CONFIG_DIR=/root/.claude

# Run worker
CMD ["python", "worker.py"]
