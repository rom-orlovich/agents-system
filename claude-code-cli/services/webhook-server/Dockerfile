FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv pip install --no-cache --system -r pyproject.toml

# Copy application code
COPY services/webhook-server/main.py .
COPY services/webhook-server/routes/ ./routes/

# Copy shared utilities
COPY shared /shared

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
