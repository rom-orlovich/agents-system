# Monorepo Rules

## Enforcement Level
HIGH - Must be followed for all cross-component changes

## Package Dependencies

### Structure
```
integrations/
├── packages/           # Shared client libraries (base layer)
│   ├── jira_client/
│   ├── sentry_client/
│   └── slack_client/
├── api/                # REST API servers (middle layer)
│   ├── jira/
│   ├── sentry/
│   └── slack/
└── mcp-servers/        # MCP protocol servers (top layer)
    ├── jira/
    ├── sentry/
    └── slack/
```

### Dependency Rules
- **Packages** MUST NOT depend on api/ or mcp-servers/
- **API servers** MAY depend on packages/
- **MCP servers** MAY depend on packages/
- **MCP servers** MUST NOT depend on api/
- **NO circular dependencies** between any packages

### Import Rules
```python
integrations/mcp-servers/jira_mcp_server/
  ✅ CAN import from: integrations/packages/jira_client/
  ❌ CANNOT import from: integrations/packages/slack_client/
  ❌ CANNOT import from: integrations/api/jira/

agent-container/
  ✅ CAN import from: integrations/packages/*/
  ❌ CANNOT import from: api-gateway/
  ❌ CANNOT import from: dashboard-api-container/

api-gateway/
  ✅ CAN import from: integrations/packages/*/
  ❌ CANNOT import from: agent-container/
```

## File Organization

### Max Lines Per File
- **Code files:** 300 lines (strict)
- **Test files:** 300 lines (strict)
- **Documentation:** 500 lines (recommended)

### Enforcement
```bash
find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'
```

## Versioning

### Semantic Versioning
All packages use same version: `MAJOR.MINOR.PATCH`

### Version Bumps
- **MAJOR:** Breaking changes
- **MINOR:** New features, backwards compatible
- **PATCH:** Bug fixes

### Single Source of Truth
```toml
# pyproject.toml (root)
[project]
version = "0.1.0"
```

## Testing Strategy

### Unit Tests
Location: `<package>/tests/`
```
integrations/packages/jira_client/tests/test_client.py
agent-container/tests/test_result_poster.py
```

### Integration Tests
Location: `tests/integration/`
```
tests/integration/test_jira_integration.py
tests/integration/test_task_workflow.py
```

### E2E Tests
Location: `tests/e2e/`
```
tests/e2e/test_webhook_flow.py
tests/e2e/test_complete_workflow.py
```

### Coverage Requirements
- **Unit tests:** ≥ 80% per package
- **Integration tests:** Critical paths only
- **E2E tests:** Happy path + error cases

## Documentation

### Required Files
Each package/service must have:
- `README.md`: Overview, setup, usage
- `claude.md`: AI agent context
- `tests/`: Test files

### Claude.md Structure
Maximum 300 lines, following template:
```markdown
# [Component Name]

## Purpose
[What this does]

## Architecture
[How it works]

## Key Files
[Important files]

## Dependencies
[What it depends on]

## Usage
[How to use]

## Development
[How to develop]
```

## Build & Deploy

### Development
```bash
docker-compose up  # All services
docker-compose up api-gateway  # Single service
```

### Testing
```bash
pytest                  # All tests
pytest tests/unit       # Unit tests only
pytest -m integration   # Integration tests only
```

### Linting
```bash
ruff check .
mypy .
```

## Git Workflow

### Branch Strategy
- `main`: Production-ready code
- `feature/*`: New features
- `fix/*`: Bug fixes
- `refactor/*`: Code improvements

### Commit Messages
```
<type>: <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### Pull Requests
- **Required reviews:** 1
- **Required checks:** Tests, linting, type checking
- **Squash merges:** Preferred

## Prohibited Practices

### NO Cross-Service Imports
```python
# ❌ WRONG
from api_gateway.core import TaskLogger  # In agent-container
```

### NO Shared State
- No global variables between services
- No shared database connections
- No shared caches (use Redis)

### NO Tight Coupling
- Services communicate via:
  - MCP protocol
  - REST APIs
  - Message queues (Redis)
- NOT via direct imports

## Change Impact Analysis

### Before Making Changes
1. Identify affected packages
2. Check dependency graph
3. Run tests for affected packages
4. Update documentation

### Cross-Package Changes
1. Make changes in dependency order (bottom-up)
2. Test each package independently
3. Test integration points
4. Update all affected services

## Release Process

### Pre-Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] No breaking changes (or documented)

### Release Steps
1. Update version in pyproject.toml
2. Update CHANGELOG.md
3. Create git tag
4. Build Docker images
5. Deploy to staging
6. Run E2E tests
7. Deploy to production
