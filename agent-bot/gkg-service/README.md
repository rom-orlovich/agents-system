# GKG Service

GitLab Knowledge Graph service for code entity relationship analysis. Provides graph-based queries for understanding code structure, dependencies, and usage patterns.

## Quick Start

```bash
# Run with Docker (recommended)
docker-compose --profile knowledge up gkg-service

# Run locally
cd gkg-service
pip install -r requirements.txt
python main.py
```

## Architecture

The service follows a modular, protocol-based architecture:

```
gkg-service/
├── core/                    # Business logic (framework-agnostic)
│   ├── interfaces.py        # Protocol definitions
│   ├── models.py            # Domain models
│   └── graph_analyzer.py    # Core analysis logic
│
├── adapters/                # External implementations
│   └── gkg_binary_adapter.py  # GKG CLI wrapper
│
├── api/                     # HTTP layer
│   └── routes.py            # FastAPI routes
│
├── tests/                   # Behavior-driven tests
├── docs/                    # Documentation
├── factory.py               # Dependency injection
└── main.py                  # Application entry point
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/analyze/dependencies` | POST | Get file dependencies |
| `/query/usages` | POST | Find symbol usages |
| `/graph/calls` | POST | Get function call graph |
| `/graph/hierarchy` | POST | Get class hierarchy |
| `/graph/related` | POST | Find related entities |
| `/index` | POST | Index a repository |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/data/gkg` | Graph database storage |
| `REPOS_DIR` | `/data/repos` | Repository storage |
| `GKG_BINARY` | `gkg` | Path to GKG binary |
| `HOST` | `0.0.0.0` | Service bind address |
| `PORT` | `8003` | Service port |

## Replacing Components

The GKG binary adapter can be replaced with any implementation of `GraphAnalyzerProtocol`:

```python
# Create custom adapter
class Neo4jAdapter:
    async def query_dependencies(self, ...): ...
    async def find_usages(self, ...): ...
    # ... implement protocol methods

# Use in factory.py
container.set_graph_analyzer(Neo4jAdapter())
```

## Testing

```bash
# Run behavior tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core --cov-report=term-missing
```

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLE_CACHING` | `true` | Cache query results |
| `ENABLE_BATCH` | `true` | Enable batch operations |
