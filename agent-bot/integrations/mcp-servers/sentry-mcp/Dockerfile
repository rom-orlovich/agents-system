FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastmcp httpx

COPY sentry_mcp.py .

EXPOSE 9004

ENV SENTRY_AUTH_TOKEN=""
ENV PORT=9004

CMD ["python", "sentry_mcp.py"]
