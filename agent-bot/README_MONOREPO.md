# Agent Bot - Monorepo with Shared Clients

Production-ready microservices architecture using monorepo with shared client packages (DRY principle).

## Architecture

This is a **monorepo** where shared API client logic lives in `integrations/` and is used by both:
- **MCP Servers**: Provide tools for agents via stdio
- **REST APIs**: Provide HTTP endpoints for services

```
agent-bot/
├── integrations/
│   ├── jira_client/           # Shared Jira API client
│   ├── slack_client/          # Shared Slack API client
│   ├── sentry_client/         # Shared Sentry API client
│   ├── jira_mcp_server/       # MCP server (uses jira_client)
│   ├── jira_rest_api/         # REST API (uses jira_client)
│   ├── slack_mcp_server/      # MCP server (uses slack_client)
│   ├── slack_rest_api/        # REST API (uses slack_client)
│   ├── sentry_mcp_server/     # MCP server (uses sentry_client)
│   └── sentry_rest_api/       # REST API (uses sentry_client)
├── api-gateway/               # Webhook receiver
├── agent-container/           # Task execution
└── dashboard-api-container/   # Analytics & logs
```

## Key Principles

### DRY with Shared Clients
**ONE implementation of API client logic**:
```
integrations/jira_client/          ← Single source of truth
        ↗              ↖
jira_mcp_server    jira_rest_api
(for agents)       (for HTTP)
```

### Benefits
- ✅ **DRY**: API client code written once, shared everywhere
- ✅ **Modular**: MCP and REST are separate services
- ✅ **Scalable**: Scale MCP servers independently from REST APIs
- ✅ **Testable**: Test shared client once, both consumers benefit
- ✅ **Type-safe**: Pydantic validation in shared client

## Package Structure

### Shared Client Package
```
integrations/jira_client/
├── jira_client/
│   ├── __init__.py
│   ├── client.py              # Core API client
│   ├── models.py              # Pydantic models
│   └── exceptions.py          # Custom exceptions
├── tests/
│   └── test_client.py
├── pyproject.toml             # Package definition
└── README.md
```

### MCP Server Package
```
integrations/jira_mcp_server/
├── jira_mcp_server/
│   ├── __init__.py
│   ├── server.py              # MCP tools
│   └── __main__.py
├── tests/
├── Dockerfile                 # Multi-stage with uv
├── pyproject.toml             # Depends on jira_client
└── uv.lock
```

### REST API Package
```
integrations/jira_rest_api/
├── jira_rest_api/
│   ├── __init__.py
│   ├── routes.py              # FastAPI routes
│   └── __main__.py
├── tests/
├── Dockerfile                 # Multi-stage with uv
├── pyproject.toml             # Depends on jira_client
└── uv.lock
```

## Development Setup

### Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Local Development
```bash
# Install all packages in development mode
cd integrations/jira_client && uv sync
cd integrations/jira_mcp_server && uv sync
cd integrations/jira_rest_api && uv sync

# Run MCP server
cd integrations/jira_mcp_server && uv run python -m jira_mcp_server

# Run REST API
cd integrations/jira_rest_api && uv run python -m jira_rest_api
```

### Docker Compose (Hot Reload)
```bash
docker-compose up -d
```

Volume mounts enable hot reload in development:
- Changes to `integrations/jira_client/` reload both MCP and REST
- Changes to `integrations/jira_mcp_server/` reload only MCP
- Changes to `integrations/jira_rest_api/` reload only REST

## Usage

### From Agent (MCP - stdio)
```python
from mcp import Client

async with Client(host="jira-mcp-server") as client:
    result = await client.call_tool(
        "jira_add_comment",
        {"issue_key": "PROJ-123", "comment": "Agent comment"}
    )
```

### From Service (REST - HTTP)
```bash
curl -X POST http://jira-rest-api:8082/api/v1/jira/issue/PROJ-123/comment \
  -H "Content-Type: application/json" \
  -d '{"issue_key":"PROJ-123","comment":"Service comment"}'
```

## Testing

### Test Shared Client
```bash
cd integrations/jira_client
uv run pytest tests/ -v
```

### Test MCP Server
```bash
cd integrations/jira_mcp_server
uv run pytest tests/ -v
```

### Test REST API
```bash
cd integrations/jira_rest_api
uv run pytest tests/ -v
```

## Building

### Build MCP Server
```bash
docker build -f integrations/jira_mcp_server/Dockerfile -t jira-mcp-server .
```

### Build REST API
```bash
docker build -f integrations/jira_rest_api/Dockerfile -t jira-rest-api .
```

## Documentation

- **[ARCHITECTURE_MONOREPO.md](./ARCHITECTURE_MONOREPO.md)** - Complete monorepo architecture
- **[integrations/jira_client/README.md](./integrations/jira_client/README.md)** - Jira client docs
- **[integrations/slack_client/README.md](./integrations/slack_client/README.md)** - Slack client docs
- **[integrations/sentry_client/README.md](./integrations/sentry_client/README.md)** - Sentry client docs

## Why This Architecture?

### vs. Dual-Purpose Servers
**Dual-Purpose**: One container serving both MCP and REST
- ❌ Harder to scale independently
- ❌ Mixed concerns (MCP + HTTP in one process)

**Monorepo with Shared Clients**: Separate containers, shared code
- ✅ Scale MCP and REST independently
- ✅ Clear separation of concerns
- ✅ Shared client is a proper Python package
- ✅ Modern Python tooling (uv)

### vs. Code Duplication
**Without Shared Client**: Duplicate API client in each service
- ❌ Violates DRY
- ❌ Bug fixes need to be made twice
- ❌ Inconsistent behavior

**With Shared Client**: ONE implementation, multiple consumers
- ✅ DRY principle
- ✅ Fix bugs once
- ✅ Consistent behavior

## License

MIT
