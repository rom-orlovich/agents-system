FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    nodejs \
    npm \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

RUN useradd -m -u 1000 agent && chown -R agent:agent /app

USER agent

RUN curl https://cursor.com/install -fsS | bash

ENV PATH="/home/agent/.local/bin:${PATH}"

RUN claude --version && agent --version

USER root

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R agent:agent /app

RUN mkdir -p /app/repos && chown -R agent:agent /app/repos

USER agent
ENV PORT=8080
ENV CLI_PROVIDER=claude
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV MAX_CONCURRENT_TASKS=5
ENV TASK_TIMEOUT_SECONDS=3600

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/bin/bash"]
CMD ["scripts/docker-start.sh"]
