FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (for Claude CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Configure git
RUN git config --global user.name "Claude Agent" \
    && git config --global user.email "claude-agent@automated.dev"

# Copy project files
COPY pyproject.toml .
COPY planning-agent/ ./planning_agent/
COPY shared/ ./shared/
COPY webhook-server/queue.py ./webhook_server/queue.py

# Copy CLAUDE.md to workspace
RUN mkdir -p /workspace
COPY planning-agent/CLAUDE.md /workspace/CLAUDE.md

# Install dependencies
RUN uv pip install --system -e .

# Set working directory for Claude
WORKDIR /workspace

CMD ["python", "/app/planning_agent/worker.py"]
