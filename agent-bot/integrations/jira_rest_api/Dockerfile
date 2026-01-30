FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /workspace

COPY packages/jira_client ./packages/jira_client
COPY packages/jira_rest_api ./packages/jira_rest_api

WORKDIR /workspace/packages/jira_client
RUN uv sync --frozen

WORKDIR /workspace/packages/jira_rest_api
RUN uv sync --frozen

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /workspace/packages/jira_client /app/packages/jira_client
COPY --from=builder /workspace/packages/jira_rest_api /app/packages/jira_rest_api
COPY --from=builder /root/.local /root/.local

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app/packages/jira_rest_api

EXPOSE 8082

CMD ["uv", "run", "python", "-m", "jira_rest_api"]
