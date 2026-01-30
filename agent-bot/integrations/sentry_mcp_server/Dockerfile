FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /workspace

COPY packages/sentry_client ./packages/sentry_client
COPY packages/sentry_mcp_server ./packages/sentry_mcp_server

WORKDIR /workspace/packages/sentry_client
RUN uv sync --frozen

WORKDIR /workspace/packages/sentry_mcp_server
RUN uv sync --frozen

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /workspace/packages/sentry_client /app/packages/sentry_client
COPY --from=builder /workspace/packages/sentry_mcp_server /app/packages/sentry_mcp_server
COPY --from=builder /root/.local /root/.local

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app/packages/sentry_mcp_server

CMD ["uv", "run", "python", "-m", "sentry_mcp_server"]
