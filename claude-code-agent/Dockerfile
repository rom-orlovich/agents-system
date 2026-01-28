FROM python:3.12-slim

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    git \
    curl \
    jq \
    build-essential \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI via npm (required for headless operation)
# Using @latest to ensure we get the most recent version
RUN npm install -g @anthropic-ai/claude-code@latest

# Install uv
RUN pip install --no-cache-dir uv

# Create non-root user (required: Claude CLI doesn't allow --dangerously-skip-permissions as root)
RUN groupadd -r claude && useradd -r -g claude -m -s /bin/bash claude

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY uv.lock* ./
COPY README.md ./

# Install dependencies using uv
RUN uv sync --frozen || uv sync

# Copy application code
COPY . .

# Ensure all shell scripts are executable
RUN find .claude/skills -name "*.sh" -type f -exec chmod +x {} \; || true

# Create data directory structure with correct permissions
RUN mkdir -p /data/db /data/config/{webhooks,agents,skills} /data/credentials /data/registry \
    && chown -R claude:claude /data /app

# Create .claude directory for credentials
RUN mkdir -p /home/claude/.claude && chown -R claude:claude /home/claude

# Switch to non-root user
USER claude

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["sh", "-c", "uv sync && uv run uvicorn main:app --host 0.0.0.0 --port 8000"]
