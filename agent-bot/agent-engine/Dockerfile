FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git bash ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

# Create non-root user
RUN useradd -m -u 1000 agent && chown -R agent:agent /app

# Setup directories
RUN mkdir -p /home/agent/.claude /home/agent/.local/bin /app/repos \
    && chown -R agent:agent /home/agent /app

ENV PATH="/home/agent/.local/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=agent:agent . .

ENV PORT=8080
ENV CLI_PROVIDER=claude

EXPOSE 8080

# Switch to non-root user
USER agent

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "scripts/start.py"]
