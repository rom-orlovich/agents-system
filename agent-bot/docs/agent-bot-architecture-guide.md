# Agent Bot - Comprehensive Architecture Guide

## Executive Summary

This document addresses critical architectural decisions for making your agent-bot system production-ready, modular, and extensible. It covers integration changes, modularity patterns, knowledge graph implementation, and repository cloning strategies.

---

## Part 1: Critical Integration Changes Analysis

### Current Architecture Assessment

Based on your documentation, your architecture has solid foundations but needs specific changes for multi-organization support.

### Required Changes

#### 1.1 Token Management Service (NEW COMPONENT)

Your current architecture assumes static tokens. For multi-org support, you need dynamic token management:

```
integrations/
├── token_service/           # NEW - Central token management
│   ├── token_service/
│   │   ├── __init__.py
│   │   ├── service.py       # TokenService class
│   │   ├── models.py        # Installation, Token models
│   │   ├── repository.py    # DB operations
│   │   ├── refresh.py       # Token refresh logic
│   │   └── exceptions.py
│   └── tests/
```

**Core Model:**

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Literal

class Installation(BaseModel):
    model_config = ConfigDict(strict=True)
    
    id: str
    platform: Literal["github", "slack", "jira", "sentry"]
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None
    token_expires_at: datetime | None
    scopes: list[str]
    webhook_secret: str
    installed_at: datetime
    installed_by: str
    metadata: dict[str, str]
```

#### 1.2 Webhook Handler Changes

Your `api-gateway/webhooks/` handlers need to identify the organization:

```python
# api-gateway/webhooks/github_handler.py - CHANGES NEEDED

async def handle(payload: dict, headers: dict) -> WebhookResponse:
    # CURRENT: Static token from env
    # NEEDED: Dynamic token lookup
    
    installation_id = payload.get("installation", {}).get("id")
    
    # NEW: Fetch org-specific credentials
    installation = await token_service.get_installation(
        platform="github",
        installation_id=str(installation_id)
    )
    
    # Validate signature with org-specific secret
    validate_signature(
        payload, 
        headers, 
        secret=installation.webhook_secret  # Per-org secret
    )
    
    task = TaskQueueMessage(
        task_id=generate_task_id(),
        installation_id=installation.id,  # NEW: Track which org
        access_token=installation.access_token,  # Org-specific token
        ...
    )
```

#### 1.3 OAuth Callback Endpoint (NEW)

Add OAuth flow handling:

```
api-gateway/
├── webhooks/
│   └── ...
├── oauth/                    # NEW
│   ├── __init__.py
│   ├── github_oauth.py       # GitHub OAuth callback
│   ├── slack_oauth.py        # Slack OAuth callback
│   ├── jira_oauth.py         # Jira OAuth callback
│   └── models.py             # OAuth state, tokens
```

#### 1.4 Database Schema Addition

```sql
-- migrations/versions/001_add_installations.py

CREATE TABLE installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(20) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    scopes TEXT[],
    webhook_secret VARCHAR(255) NOT NULL,
    installed_at TIMESTAMP DEFAULT NOW(),
    installed_by VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(platform, organization_id)
);

CREATE INDEX idx_installations_platform_org 
ON installations(platform, organization_id);
```

---

## Part 2: Modularity - Ports & Adapters Pattern

### Architecture Overview

Implement hexagonal architecture (ports & adapters) for maximum flexibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAIN CORE                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Business Logic (Pure Python, No External Dependencies)  │   │
│  │  - Task Processing Logic                                 │   │
│  │  - Workflow Orchestration                                │   │
│  │  - Agent Decision Making                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│         INPUT PORTS     STORAGE PORTS    OUTPUT PORTS          │
│         (Interfaces)    (Interfaces)     (Interfaces)          │
└─────────────────────────────────────────────────────────────────┘
              │               │               │
              ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ADAPTERS                                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ GitHub  │  │  Redis  │  │ Postgres│  │ Claude  │            │
│  │ Webhook │  │  Queue  │  │   DB    │  │   CLI   │            │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │  Jira   │  │  SQS    │  │ MongoDB │  │ Cursor  │            │
│  │ Webhook │  │  Queue  │  │   DB    │  │   CLI   │            │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Port Definitions (Interfaces)

Create a `ports/` directory in each component:

```
agent-container/
├── ports/                    # Abstract interfaces
│   ├── __init__.py
│   ├── queue.py              # QueuePort protocol
│   ├── database.py           # DatabasePort protocol
│   ├── cli_runner.py         # CLIRunnerPort protocol
│   ├── external_service.py   # ExternalServicePort protocol
│   └── logger.py             # LoggerPort protocol
├── adapters/                 # Concrete implementations
│   ├── __init__.py
│   ├── queue/
│   │   ├── redis_adapter.py
│   │   ├── sqs_adapter.py
│   │   └── memory_adapter.py  # For testing
│   ├── database/
│   │   ├── postgres_adapter.py
│   │   ├── mongodb_adapter.py
│   │   └── memory_adapter.py  # For testing
│   ├── cli/
│   │   ├── claude_adapter.py
│   │   ├── cursor_adapter.py
│   │   └── mock_adapter.py    # For testing
│   └── external/
│       ├── github_adapter.py
│       ├── jira_adapter.py
│       └── slack_adapter.py
└── core/                     # Domain logic (uses ports only)
    ├── task_processor.py
    └── workflow_engine.py
```

### 2.2 Port Protocol Definitions

```python
# ports/queue.py
from typing import Protocol
from abc import abstractmethod

class QueuePort(Protocol):
    @abstractmethod
    async def enqueue(self, message: TaskQueueMessage) -> None: ...
    
    @abstractmethod
    async def dequeue(self, timeout: float) -> TaskQueueMessage | None: ...
    
    @abstractmethod
    async def acknowledge(self, message_id: str) -> None: ...
    
    @abstractmethod
    async def get_queue_length(self) -> int: ...
```

```python
# ports/cli_runner.py
from typing import Protocol, AsyncIterator

class CLIRunnerPort(Protocol):
    @abstractmethod
    async def execute(
        self,
        prompt: str,
        model: str,
        working_dir: str
    ) -> AsyncIterator[CLIOutput]: ...
    
    @abstractmethod
    async def cancel(self, execution_id: str) -> None: ...
```

```python
# ports/database.py
from typing import Protocol, TypeVar, Generic

T = TypeVar("T")

class RepositoryPort(Protocol, Generic[T]):
    @abstractmethod
    async def get(self, id: str) -> T | None: ...
    
    @abstractmethod
    async def save(self, entity: T) -> T: ...
    
    @abstractmethod
    async def delete(self, id: str) -> bool: ...
    
    @abstractmethod
    async def find_by(self, **criteria) -> list[T]: ...
```

### 2.3 Adapter Implementations

```python
# adapters/queue/redis_adapter.py
import redis.asyncio as redis
from ports.queue import QueuePort

class RedisQueueAdapter(QueuePort):
    def __init__(self, redis_url: str, queue_name: str):
        self.redis = redis.from_url(redis_url)
        self.queue_name = queue_name
    
    async def enqueue(self, message: TaskQueueMessage) -> None:
        await self.redis.zadd(
            self.queue_name,
            {message.model_dump_json(): message.priority}
        )
    
    async def dequeue(self, timeout: float) -> TaskQueueMessage | None:
        result = await self.redis.bzpopmin(self.queue_name, timeout)
        if result:
            return TaskQueueMessage.model_validate_json(result[1])
        return None
```

```python
# adapters/queue/sqs_adapter.py
import aioboto3
from ports.queue import QueuePort

class SQSQueueAdapter(QueuePort):
    def __init__(self, queue_url: str, region: str):
        self.queue_url = queue_url
        self.session = aioboto3.Session()
        self.region = region
    
    async def enqueue(self, message: TaskQueueMessage) -> None:
        async with self.session.client("sqs", region_name=self.region) as sqs:
            await sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message.model_dump_json(),
                MessageAttributes={
                    "Priority": {"DataType": "Number", "StringValue": str(message.priority)}
                }
            )
```

### 2.4 Dependency Injection Container

```python
# container.py
from dataclasses import dataclass
from ports.queue import QueuePort
from ports.database import RepositoryPort
from ports.cli_runner import CLIRunnerPort

@dataclass
class Container:
    queue: QueuePort
    task_repository: RepositoryPort[Task]
    installation_repository: RepositoryPort[Installation]
    cli_runner: CLIRunnerPort

def create_container(config: Config) -> Container:
    match config.queue_type:
        case "redis":
            queue = RedisQueueAdapter(config.redis_url, config.queue_name)
        case "sqs":
            queue = SQSQueueAdapter(config.sqs_url, config.aws_region)
        case "memory":
            queue = MemoryQueueAdapter()
    
    match config.database_type:
        case "postgres":
            task_repo = PostgresTaskRepository(config.database_url)
            install_repo = PostgresInstallationRepository(config.database_url)
        case "mongodb":
            task_repo = MongoTaskRepository(config.mongo_url)
            install_repo = MongoInstallationRepository(config.mongo_url)
    
    match config.cli_type:
        case "claude":
            cli = ClaudeCliAdapter(config.claude_config)
        case "cursor":
            cli = CursorCliAdapter(config.cursor_config)
    
    return Container(
        queue=queue,
        task_repository=task_repo,
        installation_repository=install_repo,
        cli_runner=cli
    )
```

### 2.5 Webhook Extension Pattern

```python
# api-gateway/webhooks/registry.py
from typing import Protocol, Callable

class WebhookHandlerProtocol(Protocol):
    async def validate(self, payload: bytes, headers: dict) -> bool: ...
    async def parse(self, payload: bytes) -> WebhookPayload: ...
    async def handle(self, payload: WebhookPayload) -> WebhookResponse: ...

class WebhookRegistry:
    def __init__(self):
        self._handlers: dict[str, WebhookHandlerProtocol] = {}
    
    def register(self, provider: str, handler: WebhookHandlerProtocol) -> None:
        self._handlers[provider] = handler
    
    def get_handler(self, provider: str) -> WebhookHandlerProtocol | None:
        return self._handlers.get(provider)
    
    def list_providers(self) -> list[str]:
        return list(self._handlers.keys())

# Usage - easy to add new webhooks
registry = WebhookRegistry()
registry.register("github", GitHubWebhookHandler())
registry.register("jira", JiraWebhookHandler())
registry.register("slack", SlackWebhookHandler())
registry.register("linear", LinearWebhookHandler())  # NEW!
registry.register("notion", NotionWebhookHandler())  # NEW!
```

---

## Part 3: Agent Container Organization

### 3.1 Complete .claude Structure

```
agent-container/
├── .claude/
│   ├── claude.md                    # Main config (EXISTS)
│   │
│   ├── agents/                      # Sub-agents
│   │   ├── planning-agent.md        # Task decomposition
│   │   ├── code-review-agent.md     # PR review specialist
│   │   ├── bug-fix-agent.md         # Bug investigation & fix
│   │   ├── security-scan-agent.md   # Security analysis
│   │   └── test-writer-agent.md     # Test generation
│   │
│   ├── skills/                      # Reusable capabilities
│   │   ├── mcp-integration.md       # (EXISTS)
│   │   ├── skill-creator.md         # (EXISTS)
│   │   ├── agent-creator.md         # (EXISTS)
│   │   ├── code-analysis.md         # AST parsing, patterns
│   │   ├── git-operations.md        # Clone, branch, commit
│   │   ├── test-execution.md        # Run tests, coverage
│   │   ├── dependency-analysis.md   # Package deps, vulns
│   │   ├── knowledge-graph.md       # Graph queries (NEW)
│   │   └── repo-context.md          # Load repo context (NEW)
│   │
│   ├── rules/                       # Constraints
│   │   ├── project-best-practices.md  # (EXISTS)
│   │   ├── security-rules.md        # No secrets, safe ops
│   │   ├── output-format-rules.md   # Response formatting
│   │   ├── escalation-rules.md      # When to ask human
│   │   └── resource-limits.md       # Time, token limits
│   │
│   ├── commands/                    # Trigger patterns
│   │   ├── analyze.md               # @agent analyze
│   │   ├── review.md                # @agent review
│   │   ├── fix.md                   # @agent fix
│   │   ├── test.md                  # @agent test
│   │   ├── explain.md               # @agent explain
│   │   └── refactor.md              # @agent refactor
│   │
│   └── hooks/                       # Lifecycle hooks
│       ├── pre-execution.md         # Before task starts
│       ├── post-execution.md        # After task completes
│       ├── on-error.md              # Error handling
│       └── on-timeout.md            # Timeout handling
```

### 3.2 Agent Definitions

**planning-agent.md:**

```markdown
# Planning Agent

## Role
Decompose complex tasks into actionable steps and coordinate sub-agents.

## Capabilities
- Break down user requests into discrete tasks
- Identify required skills and agents for each task
- Create execution plan with dependencies
- Monitor progress and adjust plan

## When to Activate
- Multi-step tasks requiring coordination
- Tasks involving multiple files or components
- Requests that need analysis before action

## Required Skills
- code-analysis: Understand codebase structure
- repo-context: Load relevant context
- knowledge-graph: Query code relationships

## Decision Making
1. Analyze user request for intent and scope
2. Query knowledge graph for affected components
3. Break into tasks with clear inputs/outputs
4. Assign tasks to appropriate sub-agents
5. Aggregate results and verify completeness

## Output Format
```json
{
  "plan_id": "plan-123",
  "tasks": [
    {
      "id": "task-1",
      "type": "code_review",
      "agent": "code-review-agent",
      "inputs": {"files": ["src/api.py"]},
      "depends_on": []
    }
  ],
  "estimated_duration_minutes": 5
}
```

## Escalation Rules
- More than 10 tasks needed → Ask user to narrow scope
- Circular dependencies detected → Report and halt
- Unknown file types → Ask for clarification
```

**bug-fix-agent.md:**

```markdown
# Bug Fix Agent

## Role
Investigate, diagnose, and fix bugs with minimal code changes.

## Capabilities
- Analyze error messages and stack traces
- Identify root cause through code analysis
- Generate minimal, targeted fixes
- Write regression tests for fixes

## When to Activate
- Sentry error events
- Bug reports from Jira
- @agent fix commands

## Required Skills
- code-analysis: Trace code paths
- test-execution: Run and verify tests
- git-operations: Create fix branches
- knowledge-graph: Find related code

## Process
1. Parse error context (stack trace, logs, reproduction steps)
2. Query knowledge graph for affected functions
3. Identify root cause through static analysis
4. Generate fix with explanation
5. Write regression test
6. Run existing tests to verify no regressions

## Success Criteria
- Root cause identified and documented
- Fix is minimal (< 50 lines changed)
- Regression test added
- All existing tests pass

## Escalation Rules
- Cannot reproduce error → Request more context
- Fix requires > 100 lines → Suggest refactor first
- Security-related bug → Flag for human review
```

### 3.3 Command Definitions

**commands/review.md:**

```markdown
# Review Command

## Trigger Patterns
- `@agent review`
- `@agent review this PR`
- `@agent please review`
- GitHub PR opened with `agent-review` label

## Behavior
Perform comprehensive code review focusing on:
1. Code quality and best practices
2. Potential bugs and edge cases
3. Security vulnerabilities
4. Test coverage gaps
5. Performance concerns

## Parameters
- `--focus security` - Security-focused review
- `--focus performance` - Performance-focused review
- `--strict` - Apply stricter standards

## Output
Post review comment to PR with:
- Summary (✅/⚠️/❌)
- Specific issues with line references
- Suggestions for improvement
- Reaction emoji based on quality

## Example
User: `@agent review --focus security`
Agent: Fetches PR diff, runs security-scan-agent, posts detailed review
```

### 3.4 Hook Definitions

**hooks/pre-execution.md:**

```markdown
# Pre-Execution Hook

## Purpose
Prepare environment and validate preconditions before task execution.

## Actions
1. Validate task has required inputs
2. Check resource availability (disk space, memory)
3. Load organization context (token, settings)
4. Clone/update repository if needed
5. Index codebase for knowledge graph
6. Log task start to streaming logger

## Validation Checks
- [ ] Task ID is valid format
- [ ] Organization installation is active
- [ ] Required skills are available
- [ ] Repository is accessible
- [ ] Sufficient resources available

## Failure Handling
- Missing inputs → Return error with specific field
- Inactive installation → Log and skip task
- Resource shortage → Queue for later retry
- Repository inaccessible → Retry with backoff

## Output
```json
{
  "hook": "pre-execution",
  "task_id": "task-123",
  "status": "ready",
  "context": {
    "repo_path": "/data/repos/org/repo",
    "graph_indexed": true,
    "files_count": 1234
  }
}
```
```

---

## Part 4: Root Project Organization

### 4.1 Root .claude Structure

```
agent-bot/
├── .claude/
│   ├── claude.md                    # (EXISTS) - Project overview
│   │
│   ├── rules/
│   │   ├── project-best-practices.md  # (EXISTS)
│   │   ├── monorepo-rules.md        # Cross-package rules
│   │   ├── dependency-rules.md      # Package dependencies
│   │   └── release-rules.md         # Version, changelog
│   │
│   ├── skills/
│   │   ├── mcp-integration.md       # (EXISTS)
│   │   ├── skill-creator.md         # (EXISTS)
│   │   ├── agent-creator.md         # (EXISTS)
│   │   ├── docker-compose.md        # Service orchestration
│   │   ├── testing-strategy.md      # Test organization
│   │   └── deployment.md            # Deploy procedures
│   │
│   ├── agents/
│   │   ├── devops-agent.md          # Infrastructure tasks
│   │   ├── documentation-agent.md   # Doc generation
│   │   └── migration-agent.md       # DB migrations
│   │
│   ├── commands/
│   │   ├── setup.md                 # Project setup
│   │   ├── test.md                  # Run tests
│   │   ├── deploy.md                # Deploy services
│   │   └── migrate.md               # Run migrations
│   │
│   └── hooks/
│       ├── pre-commit.md            # Validation before commit
│       └── pre-push.md              # Validation before push
```

### 4.2 Monorepo Rules

**rules/monorepo-rules.md:**

```markdown
# Monorepo Rules

## Package Dependencies
- Shared clients MUST be in `integrations/packages/`
- MCP servers MUST depend on shared clients
- REST APIs MUST depend on shared clients
- NO circular dependencies between packages

## Import Rules
```
integrations/jira_mcp_server/ 
  → CAN import from: integrations/jira_client/
  → CANNOT import from: integrations/slack_client/
  
agent-container/
  → CAN import from: integrations/*_client/
  → CANNOT import from: api-gateway/
```

## Versioning
- All packages use same version number
- Bump version in root pyproject.toml
- Generate changelog from git commits

## Testing
- Unit tests in each package: `package/tests/`
- Integration tests in root: `tests/integration/`
- E2E tests in root: `tests/e2e/`
```

---

## Part 5: Knowledge Graph Integration

### 5.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Knowledge Graph System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Parser    │───▶│   Graph     │◀───│    MCP      │         │
│  │  (gkg/AST)  │    │   (Kuzu)    │    │   Server    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                  │
│         ▼                  ▼                  ▼                  │
│  ┌─────────────────────────────────────────────────┐            │
│  │              Entities & Relations                │            │
│  │  • Files, Directories, Modules                  │            │
│  │  • Classes, Functions, Methods                  │            │
│  │  • Imports, Calls, Inheritance                  │            │
│  │  • Dependencies, Tests                          │            │
│  └─────────────────────────────────────────────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Implementation Options

**Option A: Use GitLab Knowledge Graph (Recommended for Start)**

```yaml
# docker-compose.yml
services:
  knowledge-graph:
    image: registry.gitlab.com/gitlab-org/rust/knowledge-graph:latest
    volumes:
      - ./repos:/data/repos:ro
      - ./graph-data:/data/graph
    environment:
      - GKG_DATA_DIR=/data/graph
    ports:
      - "3030:3030"
```

**Option B: Build Custom with Kuzu (More Control)**

```python
# integrations/knowledge_graph/
├── knowledge_graph/
│   ├── __init__.py
│   ├── indexer.py           # Parse code, build graph
│   ├── query.py             # Cypher queries
│   ├── models.py            # Entity models
│   └── mcp_server.py        # MCP interface
```

### 5.3 MCP Server for Knowledge Graph

```python
# integrations/knowledge_graph_mcp_server/server.py
from mcp import FastMCP
import kuzu

mcp = FastMCP("Knowledge Graph")

@mcp.tool
async def get_function_callers(
    function_name: str,
    file_path: str | None = None
) -> list[dict]:
    """Find all functions that call the specified function."""
    query = """
    MATCH (caller:Function)-[:CALLS]->(callee:Function {name: $name})
    RETURN caller.name, caller.file_path, caller.line_number
    """
    return await db.execute(query, {"name": function_name})

@mcp.tool
async def get_class_hierarchy(class_name: str) -> dict:
    """Get inheritance hierarchy for a class."""
    query = """
    MATCH path = (c:Class {name: $name})-[:EXTENDS*]->(parent:Class)
    RETURN path
    """
    return await db.execute(query, {"name": class_name})

@mcp.tool
async def get_file_dependencies(file_path: str) -> dict:
    """Get all files that this file depends on."""
    query = """
    MATCH (f:File {path: $path})-[:IMPORTS]->(dep:File)
    RETURN dep.path, dep.module_name
    """
    return await db.execute(query, {"path": file_path})

@mcp.tool
async def find_affected_by_change(file_path: str) -> list[str]:
    """Find all files that would be affected by changes to this file."""
    query = """
    MATCH (f:File {path: $path})<-[:IMPORTS*1..5]-(affected:File)
    RETURN DISTINCT affected.path
    """
    return await db.execute(query, {"path": file_path})

@mcp.tool
async def get_test_coverage(function_name: str) -> dict:
    """Find tests that cover a specific function."""
    query = """
    MATCH (t:Test)-[:TESTS]->(f:Function {name: $name})
    RETURN t.name, t.file_path
    """
    return await db.execute(query, {"name": function_name})
```

### 5.4 Knowledge Graph Skill

**.claude/skills/knowledge-graph.md:**

```markdown
# Knowledge Graph Skill

## Purpose
Query code relationships to understand impact, find dependencies, and navigate codebases.

## Available Queries

### Find Function Callers
```
get_function_callers(function_name="process_task")
→ Returns all locations where process_task is called
```

### Get Class Hierarchy
```
get_class_hierarchy(class_name="TaskWorker")
→ Returns inheritance tree: TaskWorker → BaseWorker → ABC
```

### Impact Analysis
```
find_affected_by_change(file_path="src/models/task.py")
→ Returns all files that import/depend on task.py
```

### Test Coverage
```
get_test_coverage(function_name="validate_webhook")
→ Returns tests that exercise this function
```

## When to Use
- Before making changes: Check what will be affected
- During code review: Understand the scope of changes
- Bug investigation: Trace call paths
- Refactoring: Find all usages of a function/class

## Best Practices
- Query graph before reading large files
- Use impact analysis for change risk assessment
- Combine with AST analysis for detailed understanding
```

### 5.5 Indexing Workflow

```python
# agent-container/core/graph_indexer.py
from knowledge_graph import KnowledgeGraphClient

class RepoIndexer:
    def __init__(self, graph_client: KnowledgeGraphClient):
        self.graph = graph_client
    
    async def index_repository(self, repo_path: str) -> IndexResult:
        """Index a repository into the knowledge graph."""
        
        # Check if already indexed
        last_indexed = await self.graph.get_last_indexed(repo_path)
        last_commit = await git.get_head_commit(repo_path)
        
        if last_indexed and last_indexed.commit == last_commit:
            return IndexResult(status="cached", entities=0)
        
        # Parse and index
        entities = []
        for file_path in await self._get_source_files(repo_path):
            parsed = await self._parse_file(file_path)
            entities.extend(parsed.entities)
            entities.extend(parsed.relations)
        
        await self.graph.bulk_insert(entities)
        await self.graph.set_last_indexed(repo_path, last_commit)
        
        return IndexResult(status="indexed", entities=len(entities))
    
    async def _parse_file(self, file_path: str) -> ParseResult:
        """Parse a file and extract entities and relations."""
        ext = file_path.suffix
        
        match ext:
            case ".py":
                return await self._parse_python(file_path)
            case ".ts" | ".tsx" | ".js" | ".jsx":
                return await self._parse_typescript(file_path)
            case ".rs":
                return await self._parse_rust(file_path)
            case _:
                return ParseResult(entities=[], relations=[])
```

---

## Part 6: Repository Cloning Strategy

### 6.1 Recommendation: YES, Clone Repos

**Benefits:**
- Full file access for deep analysis
- Run tests and linters locally
- Knowledge graph indexing
- Git operations (branch, commit)
- Offline capability

### 6.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Repository Manager                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Clone     │───▶│   Cache     │───▶│   Cleanup   │         │
│  │   Service   │    │   Manager   │    │   Service   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────┐            │
│  │            Persistent Volume                     │            │
│  │  /data/repos/{org}/{repo}/.git                  │            │
│  │  /data/repos/{org}/{repo}/src/                  │            │
│  └─────────────────────────────────────────────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Implementation

```python
# agent-container/core/repo_manager.py
import subprocess
from pathlib import Path
from dataclasses import dataclass

@dataclass
class RepoConfig:
    base_path: Path = Path("/data/repos")
    max_repo_size_mb: int = 500
    max_repos_per_org: int = 10
    shallow_clone_depth: int = 1
    cache_ttl_hours: int = 24

class RepoManager:
    def __init__(
        self, 
        config: RepoConfig,
        token_service: TokenService
    ):
        self.config = config
        self.token_service = token_service
    
    async def ensure_repo(
        self,
        organization_id: str,
        repo_full_name: str,
        ref: str = "main"
    ) -> Path:
        """Ensure repo is cloned and up-to-date, return path."""
        
        repo_path = self._get_repo_path(organization_id, repo_full_name)
        
        if repo_path.exists():
            await self._update_repo(repo_path, ref)
        else:
            await self._clone_repo(organization_id, repo_full_name, ref)
        
        return repo_path
    
    async def _clone_repo(
        self,
        organization_id: str,
        repo_full_name: str,
        ref: str
    ) -> Path:
        """Clone repository with org-specific credentials."""
        
        installation = await self.token_service.get_installation(
            platform="github",
            organization_id=organization_id
        )
        
        repo_path = self._get_repo_path(organization_id, repo_full_name)
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clone with token in URL (secure - stored in memory only)
        clone_url = f"https://x-access-token:{installation.access_token}@github.com/{repo_full_name}.git"
        
        cmd = [
            "git", "clone",
            "--depth", str(self.config.shallow_clone_depth),
            "--branch", ref,
            "--single-branch",
            clone_url,
            str(repo_path)
        ]
        
        await self._run_git(cmd)
        
        # Remove token from remote URL after clone
        await self._sanitize_remote(repo_path, repo_full_name)
        
        return repo_path
    
    async def _update_repo(self, repo_path: Path, ref: str) -> None:
        """Fetch latest changes for a ref."""
        
        installation = await self._get_installation_for_repo(repo_path)
        
        # Temporarily set credentials
        await self._set_credentials(repo_path, installation.access_token)
        
        try:
            await self._run_git(["git", "-C", str(repo_path), "fetch", "origin", ref])
            await self._run_git(["git", "-C", str(repo_path), "checkout", f"origin/{ref}"])
        finally:
            await self._clear_credentials(repo_path)
    
    async def checkout_pr(
        self,
        repo_path: Path,
        pr_number: int
    ) -> None:
        """Checkout a PR's head commit."""
        
        installation = await self._get_installation_for_repo(repo_path)
        await self._set_credentials(repo_path, installation.access_token)
        
        try:
            await self._run_git([
                "git", "-C", str(repo_path),
                "fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"
            ])
            await self._run_git([
                "git", "-C", str(repo_path),
                "checkout", f"pr-{pr_number}"
            ])
        finally:
            await self._clear_credentials(repo_path)
    
    async def cleanup_old_repos(self) -> int:
        """Remove repos not accessed within TTL."""
        
        removed = 0
        cutoff = datetime.now() - timedelta(hours=self.config.cache_ttl_hours)
        
        for org_path in self.config.base_path.iterdir():
            for repo_path in org_path.iterdir():
                if repo_path.stat().st_atime < cutoff.timestamp():
                    shutil.rmtree(repo_path)
                    removed += 1
        
        return removed
    
    def _get_repo_path(self, org_id: str, repo_full_name: str) -> Path:
        """Get filesystem path for a repo."""
        # org_id/owner/repo
        return self.config.base_path / org_id / repo_full_name.replace("/", "_")
    
    async def _sanitize_remote(self, repo_path: Path, repo_full_name: str) -> None:
        """Remove credentials from remote URL."""
        safe_url = f"https://github.com/{repo_full_name}.git"
        await self._run_git([
            "git", "-C", str(repo_path),
            "remote", "set-url", "origin", safe_url
        ])
```

### 6.4 Security Considerations

```python
# Security rules for repo cloning

class RepoSecurityPolicy:
    """Security constraints for repository operations."""
    
    # Paths that are NEVER allowed
    BLOCKED_PATHS = [
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "**/secrets/**",
        "**/.credentials/**"
    ]
    
    # File extensions that can be analyzed
    ALLOWED_EXTENSIONS = [
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".go", ".rs", ".java", ".rb", ".php",
        ".md", ".txt", ".json", ".yaml", ".yml",
        ".toml", ".cfg", ".ini"
    ]
    
    # Max file size to read (prevent memory issues)
    MAX_FILE_SIZE_MB = 10
    
    async def can_access_file(self, file_path: Path) -> bool:
        """Check if agent can access this file."""
        
        # Check blocked paths
        for pattern in self.BLOCKED_PATHS:
            if file_path.match(pattern):
                return False
        
        # Check extension
        if file_path.suffix not in self.ALLOWED_EXTENSIONS:
            return False
        
        # Check size
        if file_path.stat().st_size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            return False
        
        return True
```

### 6.5 Docker Configuration

```yaml
# docker-compose.yml
services:
  agent-container:
    build: ./agent-container
    volumes:
      # Persistent repo storage
      - repo-data:/data/repos
      # Knowledge graph data
      - graph-data:/data/graph
      # Task logs
      - log-data:/data/logs
    environment:
      - REPO_BASE_PATH=/data/repos
      - REPO_MAX_SIZE_MB=500
      - REPO_CACHE_TTL_HOURS=24
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

volumes:
  repo-data:
    driver: local
  graph-data:
    driver: local
  log-data:
    driver: local
```

### 6.6 Workflow Integration

```python
# agent-container/workers/task_worker.py

async def process_task(task: Task, container: Container) -> TaskResult:
    """Process a task with full repo context."""
    
    # 1. Pre-execution: Ensure repo is available
    repo_path = await container.repo_manager.ensure_repo(
        organization_id=task.installation_id,
        repo_full_name=task.metadata["repository"],
        ref=task.metadata.get("ref", "main")
    )
    
    # 2. If PR task, checkout PR
    if task.metadata.get("pr_number"):
        await container.repo_manager.checkout_pr(
            repo_path,
            task.metadata["pr_number"]
        )
    
    # 3. Index for knowledge graph
    await container.graph_indexer.index_repository(repo_path)
    
    # 4. Execute CLI with repo context
    result = await container.cli_runner.execute(
        prompt=task.input_message,
        model=task.model,
        working_dir=str(repo_path)  # CLI runs in repo directory
    )
    
    return result
```

---

## Part 7: Complete Integration Flow

### End-to-End Task Processing

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. GitHub PR Comment: "@agent analyze src/api.py"               │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. API Gateway                                                   │
│    • Extract installation_id from webhook                        │
│    • Lookup org credentials from token_service                   │
│    • Validate signature with org-specific secret                 │
│    • Create task with installation context                       │
│    • Return 200 OK immediately                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Agent Container (Pre-Execution Hook)                          │
│    • Clone/update repository                                     │
│    • Checkout PR branch                                          │
│    • Index into knowledge graph                                  │
│    • Load repo context                                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Planning Agent                                                │
│    • Query knowledge graph for src/api.py context               │
│    • Find: imports, callers, tests                               │
│    • Create analysis plan                                        │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Code Review Agent                                             │
│    • Read file content from cloned repo                          │
│    • Analyze code quality, security, performance                 │
│    • Check test coverage via knowledge graph                     │
│    • Generate review comments                                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Result Poster                                                 │
│    • Post review to GitHub PR via MCP                            │
│    • Add reaction emoji                                          │
│    • Log completion                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary: Implementation Priority

### Phase 1 (Week 1-2): Core Integration
1. [ ] Add `token_service` for multi-org credentials
2. [ ] Add OAuth callback endpoints
3. [ ] Update webhook handlers for dynamic tokens
4. [ ] Add `installations` table to database

### Phase 2 (Week 3-4): Modularity
1. [ ] Define port interfaces in `ports/`
2. [ ] Create adapters for existing implementations
3. [ ] Implement dependency injection container
4. [ ] Add webhook registry for extensibility

### Phase 3 (Week 5-6): Repository Management
1. [ ] Implement `RepoManager` with clone/update
2. [ ] Add security policies for file access
3. [ ] Configure persistent volumes in Docker
4. [ ] Integrate with task worker

### Phase 4 (Week 7-8): Knowledge Graph
1. [ ] Deploy GitLab Knowledge Graph or Kuzu
2. [ ] Create MCP server for graph queries
3. [ ] Add `knowledge-graph.md` skill
4. [ ] Integrate indexing into pre-execution hook

### Phase 5 (Week 9-10): Agent Organization
1. [ ] Create all sub-agent definitions
2. [ ] Define commands and triggers
3. [ ] Implement lifecycle hooks
4. [ ] Add rules for each agent type

---

## Files to Create/Modify

### New Files
```
integrations/token_service/
api-gateway/oauth/
agent-container/ports/
agent-container/adapters/
agent-container/core/repo_manager.py
agent-container/core/graph_indexer.py
integrations/knowledge_graph_mcp_server/
.claude/agents/*.md (5 agents)
.claude/skills/knowledge-graph.md
.claude/skills/repo-context.md
.claude/skills/git-operations.md
.claude/commands/*.md (6 commands)
.claude/hooks/*.md (4 hooks)
.claude/rules/monorepo-rules.md
```

### Modified Files
```
api-gateway/webhooks/*.py (add dynamic token lookup)
agent-container/workers/task_worker.py (add repo/graph integration)
docker-compose.yml (add volumes, knowledge-graph service)
migrations/ (add installations table)
```
