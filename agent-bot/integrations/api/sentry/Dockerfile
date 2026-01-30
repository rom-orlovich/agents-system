FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /workspace

COPY packages/sentry_client ./packages/sentry_client
COPY packages/sentry_rest_api ./packages/sentry_rest_api

WORKDIR /workspace/packages/sentry_client
RUN uv sync --frozen

WORKDIR /workspace/packages/sentry_rest_api
RUN uv sync --frozen

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /workspace/packages/sentry_client /app/packages/sentry_client
COPY --from=builder /workspace/packages/sentry_rest_api /app/packages/sentry_rest_api
COPY --from=builder /root/.local /root/.local

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app/packages/sentry_rest_api

EXPOSE 8084

CMD ["uv", "run", "python", "-m", "sentry_rest_api"]
