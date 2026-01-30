FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /workspace

COPY packages/slack_client ./packages/slack_client
COPY packages/slack_mcp_server ./packages/slack_mcp_server

WORKDIR /workspace/packages/slack_client
RUN uv sync --frozen

WORKDIR /workspace/packages/slack_mcp_server
RUN uv sync --frozen

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /workspace/packages/slack_client /app/packages/slack_client
COPY --from=builder /workspace/packages/slack_mcp_server /app/packages/slack_mcp_server
COPY --from=builder /root/.local /root/.local

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app/packages/slack_mcp_server

CMD ["uv", "run", "python", "-m", "slack_mcp_server"]
