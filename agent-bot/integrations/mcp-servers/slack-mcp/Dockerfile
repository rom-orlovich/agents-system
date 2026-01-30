FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastmcp httpx

COPY slack_mcp.py .

EXPOSE 9003

ENV SLACK_BOT_TOKEN=""
ENV PORT=9003

CMD ["python", "slack_mcp.py"]
