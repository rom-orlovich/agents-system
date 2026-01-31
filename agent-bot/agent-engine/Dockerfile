FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    bash \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

RUN useradd -m -u 1000 agent && chown -R agent:agent /app

# Set PATH for agent user in .bashrc
RUN echo 'export PATH="$HOME/.local/bin:$PATH"' >> /home/agent/.bashrc && \
    chown agent:agent /home/agent/.bashrc

ENV PATH="/home/agent/.local/bin:${PATH}"

RUN claude --version

# Ensure claude is accessible system-wide
RUN ln -sf /usr/bin/claude /usr/local/bin/claude 2>/dev/null || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=agent:agent . .

RUN mkdir -p /app/repos && chown -R agent:agent /app/repos

ENV PORT=8080
ENV CLI_PROVIDER=claude
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV MAX_CONCURRENT_TASKS=5
ENV TASK_TIMEOUT_SECONDS=3600
ENV CLAUDE_CODE_ENABLE_TASKS=true

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/bin/bash"]
CMD ["scripts/docker-start.sh"]
