# Standalone Components Architecture

## Core Principle

**Each component is completely standalone and independent, communicating only via queue or API.**

## Key Requirements

### 1. No Shared Code Libraries

- ❌ **NO shared Python packages** between components
- ❌ **NO shared code files** or modules
- ✅ **ONLY API contracts** (OpenAPI/Swagger specs, Pydantic models)
- ✅ **ONLY queue message schemas** (JSON)

**Why**: True independence - components can be updated/deployed without affecting others.

### 2. Communication Patterns

**Synchronous Communication** (Request/Response):

- HTTP REST APIs
- Well-defined API contracts (OpenAPI/Swagger)
- Versioned APIs (`/api/v1/...`)

**Asynchronous Communication** (Event-Driven):

- Redis Queue for task processing
- JSON message schemas
- No direct dependencies

**Real-Time Communication** (Optional):

- WebSocket for real-time updates
- Event streaming

### 3. Self-Contained Dependencies

Each component:

- Has its own `requirements.txt`
- Has its own `pyproject.toml`
- Manages its own dependencies
- Can run standalone (with mocked dependencies for testing)

### 4. Independent Databases

**Phase 1: Shared Database** (Initial):

- All components connect to same PostgreSQL
- Simpler migration path
- Shared volume for logs

**Phase 2: Separate Databases** (Production):

- Each component has its own PostgreSQL database
- Complete data isolation
- Independent scaling and backup strategies

---

## Component Communication Matrix

| Component           | Communicates With | Method      | Dependency Type   |
| ------------------- | ----------------- | ----------- | ----------------- |
| **API Gateway**     | GitHub Service    | HTTP API    | None (API only)   |
| **API Gateway**     | Jira Service      | HTTP API    | None (API only)   |
| **API Gateway**     | Slack Service     | HTTP API    | None (API only)   |
| **API Gateway**     | Agent Container   | Redis Queue | None (Queue only) |
| **Agent Container** | GitHub Service    | HTTP API    | None (API only)   |
| **Agent Container** | Jira Service      | HTTP API    | None (API only)   |
| **Agent Container** | Slack Service     | HTTP API    | None (API only)   |
| **Agent Container** | Sentry Service    | HTTP API    | None (API only)   |
| **Dashboard API**   | All Services      | HTTP API    | None (API only)   |
| **Dashboard API**   | Agent Container   | HTTP API    | None (API only)   |

**Key**: All communication is via API or Queue - NO direct code dependencies.

---

## API Contract Definition

### Example: GitHub Service API Contract

```yaml
# api-contracts/github-service/v1/openapi.yaml
openapi: 3.0.0
info:
  title: GitHub Service API
  version: v1
paths:
  /api/v1/github/pr/{owner}/{repo}/{pr_number}/comment:
    post:
      summary: Post comment to GitHub PR
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/PostPRCommentRequest"
      responses:
        "200":
          description: Success
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/PostPRCommentResponse"
components:
  schemas:
    PostPRCommentRequest:
      type: object
      required: [comment]
      properties:
        comment:
          type: string
          minLength: 1
          maxLength: 65536
    PostPRCommentResponse:
      type: object
      required: [success, message]
      properties:
        success:
          type: boolean
        comment_id:
          type: integer
          nullable: true
        message:
          type: string
        error:
          type: string
          nullable: true
```

### Component Implementation

Each component implements the API contract independently:

```python
# github-service/api/models.py
# Component's own implementation of API contract
from pydantic import BaseModel, Field, ConfigDict

class PostPRCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    comment: str = Field(..., min_length=1, max_length=65536)

class PostPRCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    success: bool
    comment_id: int | None
    message: str
    error: str | None

# agent-container/core/api_models/github.py
# Agent Container's own copy of API contract models
from pydantic import BaseModel, Field, ConfigDict

class PostPRCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    comment: str = Field(..., min_length=1, max_length=65536)

class PostPRCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    success: bool
    comment_id: int | None
    message: str
    error: str | None
```

---

## Queue Message Schemas

### Task Queue Message Schema

```python
# api-contracts/queue/task_message.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class TaskQueueMessage(BaseModel):
    model_config = ConfigDict(strict=True)

    task_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    input_message: str = Field(..., min_length=1)
    assigned_agent: str | None = Field(None)
    agent_type: str = Field(...)
    model: str = Field(..., min_length=1)
    priority: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**Each component** implements this schema independently:

```python
# api-gateway/queue/models.py
class TaskQueueMessage(BaseModel):
    ...

# agent-container/queue/models.py
class TaskQueueMessage(BaseModel):
    ...
```

---

## Deployment Independence

### Component Deployment Scenarios

**Scenario 1: Update GitHub Service**

- Deploy new version of GitHub Service
- Other components continue working (they call API)
- No downtime for other components
- Can rollback independently

**Scenario 2: Scale Agent Container**

- Add more Agent Container replicas
- No changes needed to other components
- Load balanced automatically via Redis Queue

**Scenario 3: Update API Gateway**

- Deploy new API Gateway version
- Microservices unaffected (they receive API calls)
- Can use blue-green deployment

**Scenario 4: Database Migration**

- Migrate one component's database
- Other components unaffected
- Can migrate components independently

---

## Testing Standalone Components

### Unit Testing

```python
# github-service/tests/test_github_service.py
# Test component in isolation - mock external dependencies

@pytest.fixture
def mock_external_api():
    """Mock GitHub external API"""
    ...

def test_post_pr_comment_success(mock_external_api):
    """Test GitHub Service in isolation"""
    service = GitHubService(mock_external_api)
    result = await service.post_pr_comment(...)
    assert result.success is True
```

### Integration Testing

```python
# tests/integration/test_api_communication.py
# Test components communicating via API

@pytest.mark.asyncio
async def test_agent_calls_github_service():
    """Test Agent Container calls GitHub Service via API"""
    github_service = start_github_service()
    agent_container = start_agent_container()

    result = await agent_container.post_github_comment(...)
    assert result.success is True

    assert github_service.received_request(...)
```

### Contract Testing

```python
# api-contracts/tests/test_contract_compliance.py
# Test that components implement API contracts correctly

def test_github_service_implements_api_contract():
    """Test GitHub Service implements API contract"""
    ...

def test_agent_container_uses_api_contract():
    """Test Agent Container uses API contract correctly"""
    ...
```

---

## Migration Path to Standalone

### Phase 1: Extract Components (Current)

- Extract components to separate containers
- Share database initially
- Share code via imports (temporary)

### Phase 2: API Contracts (Week 1-2)

- Define API contracts (OpenAPI specs)
- Implement API contracts in each component
- Remove shared code imports

### Phase 3: Independent Dependencies (Week 3-4)

- Each component has own requirements.txt
- No shared Python packages
- Test components independently

### Phase 4: Separate Databases (Week 5-6)

- Migrate to separate databases
- Data synchronization via API if needed
- Complete independence

---

## Benefits of Standalone Architecture

1. **Independent Deployment**: Update one component without affecting others
2. **Independent Scaling**: Scale components based on their own load
3. **Technology Flexibility**: Can use different technologies per component (if needed)
4. **Team Autonomy**: Teams can work independently on different components
5. **Fault Isolation**: Failure in one component doesn't cascade
6. **Testing**: Test components in complete isolation
7. **Maintenance**: Update dependencies per component independently

---

## Anti-Patterns to Avoid

❌ **Shared Code Libraries**:

```python
# ❌ BAD - Shared library
from shared.models import TaskDB
```

✅ **API Contracts**:

```python
# ✅ GOOD - API contract
from api_models.github import PostPRCommentRequest
```

❌ **Direct Database Access**:

```python
# ❌ BAD - Direct database access from another component
from other_component.database import get_task
```

✅ **API Communication**:

```python
# ✅ GOOD - API communication
response = await github_service_client.get_task(task_id)
```

❌ **Tight Coupling**:

```python
# ❌ BAD - Direct import
from agent_container.core import TaskProcessor
```

✅ **Loose Coupling**:

```python
# ✅ GOOD - API communication
response = await agent_service_client.process_task(task_id)
```

---

## Summary

**Standalone Components = True Microservices**

- Each component is independent
- Communication only via API or Queue
- No shared code libraries
- Self-contained dependencies
- Independent deployment and scaling
- Complete fault isolation

This architecture enables:

- ✅ Independent deployment
- ✅ Independent scaling
- ✅ Technology flexibility
- ✅ Team autonomy
- ✅ Fault isolation
- ✅ Easy testing
