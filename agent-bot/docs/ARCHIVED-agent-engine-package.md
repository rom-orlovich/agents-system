# ARCHIVED: Agent Engine Package

**Status**: ARCHIVED (2026-01-31)
**Reason**: Consolidated into agent-engine container

## Overview

The `agent-engine-package/` was a Python package that provided the core agent engine functionality. It has been consolidated directly into the `agent-engine/` container to simplify the architecture.

## What Was Included

### Core Components

```
agent-engine-package/
├── pyproject.toml                      # Python package configuration
├── agent_engine/
│   ├── core/                          # CLI providers, worker, queue
│   │   ├── cli/
│   │   │   ├── base.py                # CLIProvider protocol
│   │   │   ├── executor.py            # Provider factory
│   │   │   └── providers/
│   │   │       ├── claude/            # Claude Code CLI provider
│   │   │       │   ├── __init__.py
│   │   │       │   ├── config.py
│   │   │       │   ├── runner.py
│   │   │       │   └── parser.py
│   │   │       └── cursor/            # Cursor CLI provider
│   │   │           ├── __init__.py
│   │   │           ├── config.py
│   │   │           └── runner.py
│   │   ├── worker.py                  # Task worker
│   │   ├── queue_manager.py           # Redis queue manager
│   │   └── config.py                  # Settings
│   ├── models/                        # SQLAlchemy models
│   │   ├── task.py
│   │   └── execution_log.py
│   └── utils/                         # Utilities
│       └── logging.py
└── tests/
    ├── unit/
    │   └── test_cursor_provider.py
    └── integration/
```

### Key Features

1. **Multi-CLI Provider Support**
   - Claude Code CLI provider
   - Cursor CLI provider
   - Protocol-based interface for adding new providers

2. **Task Processing**
   - Redis-based queue manager
   - Async task worker
   - Real-time output streaming via asyncio.Queue

3. **Configuration**
   - Environment-based settings
   - Per-provider configuration
   - Timeout and model controls

## Migration Notes

All functionality from this package has been moved to:
- **Location**: `agent-engine/` container
- **Installation**: Now handled via Dockerfile directly
- **Configuration**: Same environment variables, now in `agent-engine/.env`

## Code References

If you need to reference the original implementation:
- CLI Providers: See `agent-engine/src/cli/providers/`
- Task Worker: See `agent-engine/src/core/worker.py`
- Queue Manager: See `agent-engine/src/core/queue_manager.py`

## Testing

Original tests have been moved to:
- Unit tests: `agent-engine/tests/unit/`
- Integration tests: `agent-engine/tests/integration/`

To run tests:
```bash
cd agent-engine
pytest tests/
```

## Why This Was Archived

**Before (Complex)**:
```
1. Separate Python package (agent-engine-package/)
2. Installed into container via pip install -e
3. Dual maintenance of package + container
4. Version management complexity
```

**After (Simplified)**:
```
1. Code directly in agent-engine/ container
2. Single source of truth
3. Easier development and debugging
4. Reduced build complexity
```

## Historical Context

This package was originally created to:
- Provide reusable CLI provider abstractions
- Enable testing outside of containers
- Support multiple deployment models

The consolidation into a single container improves:
- Development velocity (no package versioning)
- Debugging experience (single codebase)
- Build times (no separate package install)
- Maintenance burden (one less component)
