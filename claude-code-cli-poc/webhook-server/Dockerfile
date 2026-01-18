FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY webhook-server/ ./webhook_server/
COPY shared/ ./shared/

# Install dependencies
RUN uv pip install --system -e .

EXPOSE 8000

CMD ["python", "-m", "webhook_server.main"]
