FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/webhook-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
