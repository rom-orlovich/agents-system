# GKG Service Development Guide

## Architecture Overview

This service wraps the GitLab Knowledge Graph (GKG) binary to provide HTTP API access to code relationship queries. The architecture is modular and testable.

## Key Principles

1. **Protocol-Based Design** - All external dependencies implement typed protocols
2. **Dependency Injection** - Components wired via `factory.py`
3. **Behavior Tests** - Tests verify business behavior, not GKG binary details
4. **Feature Flags** - Capabilities toggleable via environment variables

## Directory Structure

- `core/` - Business logic, no external dependencies
- `adapters/` - External service wrappers (GKG binary, Neo4j, etc.)
- `api/` - HTTP route handlers
- `tests/` - Behavior-driven tests with mocks
- `docs/` - Architecture and API documentation

## Key Commands

```bash
# Run tests
pytest tests/ -v

# Format code
ruff format .

# Lint
ruff check .

# Run locally
python main.py
```

## Adding New Query Types

1. Add method to `GraphAnalyzerProtocol` in `core/interfaces.py`
2. Implement in `core/graph_analyzer.py` with business logic
3. Add adapter implementation in `adapters/gkg_binary_adapter.py`
4. Add route in `api/routes.py`
5. Add behavior test in `tests/test_graph_analyzer_behavior.py`

## Replacing GKG Binary

To switch to a different graph store (e.g., Neo4j):

1. Create `adapters/neo4j_adapter.py` implementing `GraphAnalyzerProtocol`
2. Update `factory.py` to use new adapter based on config
3. Existing tests should pass without modification

## Testing Strategy

Test behavior, not implementation:
- ✅ "Dependencies query returns file relationships"
- ✅ "Call graph includes both callers and callees"
- ❌ "GKG binary called with correct Cypher query"

## File Size Limit

Maximum 300 lines per file. Split large files into:
- `constants.py` - Configuration constants
- `models.py` - Pydantic models
- `exceptions.py` - Custom exceptions
- `core.py` - Main logic
