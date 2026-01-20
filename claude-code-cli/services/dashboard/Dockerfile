FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv pip install --no-cache --system -r pyproject.toml

# Copy application and shared code
COPY shared /shared
COPY services/dashboard/main.py .
COPY services/dashboard/static ./static

# Set python path to include shared directory
ENV PYTHONPATH=/app:/

EXPOSE 8080

CMD ["python", "main.py"]
