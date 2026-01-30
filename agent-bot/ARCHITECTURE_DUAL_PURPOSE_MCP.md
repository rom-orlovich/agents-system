# Dual-Purpose MCP Architecture - DRY Principle

## The Problem You Identified

**Question**: "The API of Sentry, Jira, and Slack use the same functions as the MCP. Can the MCP also serve the REST API itself for DRY?"

**Answer**: **YES! Absolutely!** This is a much better architecture.

---

## Current Architecture (Has Duplication)

```
┌─────────────────────┐
│  Jira REST Service  │  ← Has Jira API client
│  - API endpoints    │
│  - Jira client code │
└─────────────────────┘

┌─────────────────────┐
│  Jira MCP Server    │  ← ALSO has Jira API client (DUPLICATE!)
│  - MCP tools        │
│  - Jira client code │  ← Same code repeated!
└─────────────────────┘

❌ PROBLEM: Jira API client logic duplicated!
❌ PROBLEM: Need to maintain two codebases
❌ PROBLEM: Violates DRY principle
```

---

## New Architecture (DRY - Don't Repeat Yourself)

```
┌───────────────────────────────────────┐
│  Jira MCP Server (DUAL-PURPOSE)       │
│                                       │
│  ┌─────────────────────────────────┐ │
│  │  Shared Implementation          │ │
│  │  - jira_add_comment_impl()      │ │
│  │  - jira_get_issue_impl()        │ │
│  │  - jira_create_issue_impl()     │ │
│  │  (ONE place for API client!)    │ │
│  └─────────────────────────────────┘ │
│           ↗                    ↖      │
│          /                      \     │
│  ┌──────────┐            ┌──────────┐│
│  │MCP Tools │            │REST API  ││
│  │(stdio)   │            │(HTTP)    ││
│  └──────────┘            └──────────┘│
└───────────────────────────────────────┘

✅ SOLUTION: ONE implementation, TWO interfaces!
✅ BENEFIT: Maintain once, use twice
✅ BENEFIT: DRY principle respected
```

---

## How It Works

### Shared Implementation Layer

```python
# Core business logic - SINGLE implementation
async def jira_add_comment_impl(issue_key: str, comment: str) -> AddCommentResponse:
    """
    This function is called by BOTH:
    - MCP tools (from agents)
    - REST API endpoints (from other services)
    """
    auth_header = get_auth_header()
    base_url = get_base_url()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/issue/{issue_key}/comment",
            headers={"Authorization": auth_header},
            json={"body": comment}
        )

        return AddCommentResponse(
            success=True,
            comment_id=result.get("id"),
            message=f"Successfully added comment"
        )
```

### MCP Interface (for Agents)

```python
@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "jira_add_comment":
        validated_input = AddCommentInput.model_validate(arguments)

        # Calls shared implementation!
        result = await jira_add_comment_impl(
            validated_input.issue_key,
            validated_input.comment
        )

        return [TextContent(type="text", text=result.message)]
```

### REST Interface (for Direct HTTP Calls)

```python
@rest_api.post("/api/v1/jira/issue/{issue_key}/comment")
async def add_comment_rest(issue_key: str, request: AddCommentInput):
    # Calls SAME shared implementation!
    return await jira_add_comment_impl(issue_key, request.comment)
```

---

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────┐
│  External Services (GitHub, Jira, Slack, Sentry)         │
└────────────────────▲──────────────────────────────────────┘
                     │
                     │ HTTPS API Calls
                     │
┌────────────────────┴──────────────────────────────────────┐
│  DUAL-PURPOSE MCP SERVERS                                 │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐            │
│  │   Jira      │  │  Slack   │  │  Sentry  │            │
│  │             │  │          │  │          │            │
│  │ ┌─────────┐ │  │┌────────┐│  │┌────────┐│            │
│  │ │Shared   │ │  ││Shared  ││  ││Shared  ││            │
│  │ │Impl     │ │  ││Impl    ││  ││Impl    ││            │
│  │ └─────────┘ │  │└────────┘│  │└────────┘│            │
│  │   ↗    ↖    │  │  ↗   ↖   │  │  ↗   ↖   │            │
│  │  /      \   │  │ /     \  │  │ /     \  │            │
│  │ MCP    REST │  │MCP   REST│  │MCP   REST│            │
│  │(stdio) (HTTP)│  │      │  │  │      │  │            │
│  └─────────────┘  │└──────────┘│└──────────┘            │
└───────────────────────────────────────────────────────────┘
         ↑               ↑            ↑
         │               │            │
         │ stdio         │ HTTP       │ HTTP
         │               │            │
    ┌────┴────┐    ┌─────┴────┐  ┌───┴──────┐
    │ Agent   │    │API       │  │Dashboard │
    │Container│    │Gateway   │  │API       │
    └─────────┘    └──────────┘  └──────────┘

    Uses MCP      Can use REST   Can use REST
    (stdio)       (HTTP)         (HTTP)
```

---

## Usage Examples

### From Agent (via MCP)

```python
# Agent container uses MCP client
from mcp import Client

async with Client(host="jira-mcp-server") as client:
    # Call MCP tool
    result = await client.call_tool(
        "jira_add_comment",
        {
            "issue_key": "PROJ-123",
            "comment": "Agent analyzed this issue"
        }
    )
```

**Flow**:
1. Agent → MCP Client
2. MCP Client → Jira MCP Server (stdio)
3. MCP Server → `call_tool()` → `jira_add_comment_impl()`
4. Implementation → Jira API
5. Response back through chain

---

### From API Gateway or Dashboard (via REST)

```python
# API Gateway or Dashboard uses HTTP
import httpx

async with httpx.AsyncClient() as client:
    # Call REST endpoint
    response = await client.post(
        "http://jira-mcp-server:8082/api/v1/jira/issue/PROJ-123/comment",
        json={
            "issue_key": "PROJ-123",
            "comment": "Manual comment via REST"
        }
    )
```

**Flow**:
1. Service → HTTP Request
2. Jira MCP Server FastAPI → `add_comment_rest()`
3. REST endpoint → `jira_add_comment_impl()`
4. Implementation → Jira API
5. Response back through chain

---

## Benefits of Dual-Purpose Architecture

### 1. DRY Principle ✅

**Before**:
```
jira-rest-service/client.py     ← 500 lines
jira-mcp-server/server.py       ← 500 lines (duplicate!)
Total: 1000 lines to maintain
```

**After**:
```
jira-mcp-server/server_dual.py  ← 600 lines (includes both!)
Total: 600 lines to maintain
```

### 2. Single Source of Truth ✅

```python
# Fix bug once, both interfaces benefit!
async def jira_add_comment_impl(issue_key: str, comment: str):
    # Bug fix here applies to:
    # - MCP tool calls (from agents)
    # - REST API calls (from services)
```

### 3. Consistent Behavior ✅

Both interfaces use same:
- Authentication logic
- Error handling
- Retry logic
- Logging
- Validation

### 4. Easier Testing ✅

```python
# Test implementation once
async def test_jira_add_comment_impl():
    result = await jira_add_comment_impl("PROJ-123", "test")
    assert result.success is True

# Both interfaces tested through this!
```

### 5. Flexibility ✅

Use the right interface for the job:
- **Agents**: Use MCP (stdio) - designed for tool calling
- **Services**: Use REST (HTTP) - standard web services
- **Both work!** Same implementation underneath

---

## Docker Compose Configuration

```yaml
# Jira MCP Server (Dual-Purpose)
jira-mcp-server:
  build: ./jira-mcp-server
  ports:
    - "8082:8082"  # REST API port
  environment:
    - JIRA_EMAIL=${JIRA_EMAIL}
    - JIRA_API_TOKEN=${JIRA_API_TOKEN}
    - JIRA_DOMAIN=${JIRA_DOMAIN}
    - SERVER_MODE=both  # Run both MCP and REST
  stdin_open: true
  tty: true

# Agent uses MCP (stdio)
agent-container:
  environment:
    - MCP_JIRA_HOST=jira-mcp-server
  depends_on:
    - jira-mcp-server

# Dashboard can use REST (HTTP)
dashboard-api:
  environment:
    - JIRA_API_URL=http://jira-mcp-server:8082
  depends_on:
    - jira-mcp-server
```

---

## Server Modes

The dual-purpose server supports three modes:

### Mode 1: Both (Default)

```bash
SERVER_MODE=both  # Runs MCP (stdio) + REST (HTTP) simultaneously
```

Use when:
- Agents need MCP tools
- Other services need REST API
- Production deployment

### Mode 2: MCP Only

```bash
SERVER_MODE=mcp  # Runs only MCP server (stdio)
```

Use when:
- Only agents need access
- Reduce resource usage
- Testing MCP tools

### Mode 3: REST Only

```bash
SERVER_MODE=rest  # Runs only REST API (HTTP)
```

Use when:
- Only HTTP services need access
- Testing REST endpoints
- Legacy system integration

---

## Implementation Pattern for All Services

Apply this pattern to:
- ✅ Jira (already implemented)
- ✅ Slack (apply same pattern)
- ✅ Sentry (apply same pattern)
- ⚠️ GitHub (use official MCP, optionally add REST wrapper)

### Template Structure

```python
# 1. Shared implementation (business logic)
async def service_action_impl(params) -> Response:
    # Core logic here
    # Calls external API
    return Response(...)

# 2. MCP interface
@mcp_server.call_tool()
async def call_tool(name, arguments):
    validated = Model.model_validate(arguments)
    result = await service_action_impl(validated.params)
    return [TextContent(text=result.message)]

# 3. REST interface
@rest_api.post("/api/v1/service/action")
async def action_rest(request: Model):
    return await service_action_impl(request.params)

# 4. Run both
async def main():
    await asyncio.gather(
        run_mcp_server(),  # stdio
        run_rest_server()  # HTTP
    )
```

---

## Testing Dual-Purpose Servers

### Test Shared Implementation

```python
@pytest.mark.asyncio
async def test_jira_add_comment_impl():
    # Test core business logic
    result = await jira_add_comment_impl("PROJ-123", "test comment")

    assert result.success is True
    assert result.comment_id is not None
    # Both MCP and REST use this!
```

### Test MCP Interface

```python
@pytest.mark.asyncio
async def test_mcp_jira_add_comment():
    # Test MCP tool
    async with MCPClient(host="jira-mcp-server") as client:
        result = await client.call_tool(
            "jira_add_comment",
            {"issue_key": "PROJ-123", "comment": "test"}
        )
        assert "Successfully added" in result[0].text
```

### Test REST Interface

```python
@pytest.mark.asyncio
async def test_rest_jira_add_comment():
    # Test REST endpoint
    async with AsyncClient(app=rest_api) as client:
        response = await client.post(
            "/api/v1/jira/issue/PROJ-123/comment",
            json={"issue_key": "PROJ-123", "comment": "test"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
```

---

## Migration Strategy

### Phase 1: Add REST to MCP Servers ✅
- Implement `server_dual.py` for each service
- Keep both MCP and REST
- Test both interfaces

### Phase 2: Update Consumers
- Services that need REST can now use it
- Agents continue using MCP
- Both work simultaneously

### Phase 3: Remove Old Services (Optional)
- If you had separate REST services, remove them
- Everything now uses dual-purpose MCP servers
- Single codebase to maintain

---

## Summary

### Question: Can MCP servers also serve REST APIs for DRY?

**Answer: YES!** ✅

**Benefits**:
1. ✅ **DRY**: One implementation, two interfaces
2. ✅ **Maintainability**: Fix bugs once
3. ✅ **Consistency**: Same behavior everywhere
4. ✅ **Flexibility**: Use MCP or REST as needed
5. ✅ **Testing**: Test once, both work

**Architecture**:
```
Shared Implementation (jira_add_comment_impl)
        ↗                    ↖
   MCP Tools              REST API
   (for agents)      (for HTTP services)
```

**Result**: Much better than duplicating code! 🎉

---

## Next Steps

1. ✅ Jira dual-purpose server implemented
2. → Apply same pattern to Slack
3. → Apply same pattern to Sentry
4. → Update docker-compose.yml
5. → Test both MCP and REST interfaces
6. → Update documentation
