# Indexer Worker Development Guide

## Architecture Overview

This service is a background worker that indexes data from various sources (GitHub, Jira, Confluence) into vector (ChromaDB) and graph (GKG) stores. The architecture is modular and testable.

## Key Principles

1. **Protocol-Based Design** - All external dependencies implement typed protocols
2. **Dependency Injection** - Components wired via `factory.py`
3. **Behavior Tests** - Tests verify business behavior, not API/storage details
4. **Pluggable Sources** - New data sources are easy to add

## Directory Structure

- `core/` - Business logic, no external dependencies
- `adapters/source_adapters/` - Data source implementations (GitHub, Jira, etc.)
- `adapters/storage_adapters/` - Storage backend implementations
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
python worker.py
```

## Adding New Data Source

1. Create protocol method in `core/interfaces.py`:
   ```python
   class SourceIndexerProtocol(Protocol):
       async def fetch_items(self) -> list[SourceItem]: ...
       async def index_items(self, items: list) -> list[Chunk]: ...
   ```

2. Create adapter in `adapters/source_adapters/`:
   ```python
   class SlackIndexer:
       async def fetch_items(self) -> list[dict]:
           # Fetch from Slack API
       async def index_items(self, items) -> list[DocumentChunk]:
           # Chunk messages
   ```

3. Register in `factory.py`:
   ```python
   if source_type == "slack":
       return SlackIndexer(org_id, config)
   ```

4. Add behavior test in `tests/test_orchestrator_behavior.py`

## Testing Strategy

Test behavior, not implementation:
- ✅ "GitHub indexer produces code chunks with correct metadata"
- ✅ "Job completion publishes status event"
- ❌ "ChromaDB upsert called with specific payload"

## File Size Limit

Maximum 300 lines per file. Split large files into:
- `constants.py` - Configuration constants
- `models.py` - Pydantic models
- `chunking.py` - Text chunking logic
- `core.py` - Main orchestration

## Important Notes

- Worker runs indefinitely, polling Redis queue
- Jobs are processed one at a time (no parallel job processing)
- Repos within a job CAN be processed in parallel (configurable)
- Failed items don't fail the entire job - they're counted separately
