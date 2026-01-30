FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-cli

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml

COPY . .

ENV CLI_PROVIDER=claude-code-cli
ENV REDIS_URL=redis://redis:6379/0
ENV LOG_LEVEL=INFO

CMD ["python", "main.py"]
