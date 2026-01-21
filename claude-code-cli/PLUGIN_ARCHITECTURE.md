# Plugin-Based Architecture - Developer Guide

## Overview

The Claude Code CLI agent system now uses a **plugin-based architecture** that makes it easy to add new webhooks and agents without modifying core code. Everything is **auto-discovered** and **self-documenting** through metadata.

## Key Benefits

✅ **Zero Core Modifications** - Add new webhooks/agents by creating a single file
✅ **Auto-Discovery** - Plugins are automatically found and registered
✅ **Type-Safe** - Pydantic models enforce correct interfaces
✅ **Self-Documenting** - Metadata provides built-in documentation
✅ **Easy Testing** - Each plugin can be tested in isolation
✅ **Consistent Interface** - All plugins follow the same patterns

---

## Webhook Plugins

### Architecture

```
services/webhook-server/
├── core/
│   ├── webhook_base.py          # Base classes
│   ├── webhook_registry.py      # Central registry
│   └── webhook_validator.py     # Signature validation
├── webhooks/
│   ├── __init__.py              # Auto-discovery logic
│   ├── jira_webhook.py          # Jira webhook plugin
│   ├── github_webhook.py        # GitHub webhook plugin
│   ├── sentry_webhook.py        # Sentry webhook plugin
│   ├── slack_webhook.py         # Slack webhook plugin
│   └── [your_webhook.py]        # Add new webhooks here!
└── main.py                       # FastAPI app (no changes needed!)
```

### Adding a New Webhook

**Step 1:** Create a new file in `webhooks/` directory

```python
# webhooks/custom_webhook.py

from core.webhook_base import BaseWebhookHandler, WebhookMetadata, WebhookResponse
from typing import Dict, Any, Optional

class CustomWebhookHandler(BaseWebhookHandler):
    """Handler for Custom service webhooks."""

    @property
    def metadata(self) -> WebhookMetadata:
        """Define webhook metadata."""
        return WebhookMetadata(
            name="custom",                      # Unique name
            endpoint="/webhooks/custom",        # API endpoint
            description="Handle Custom service events",
            secret_env_var="CUSTOM_WEBHOOK_SECRET",
            enabled=True                        # Enable/disable
        )

    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature (HMAC-SHA256, etc.)."""
        from core.webhook_validator import WebhookValidator
        import os

        secret = os.getenv(self.metadata.secret_env_var)
        return WebhookValidator.validate_hmac_sha256(
            payload=payload,
            signature=signature,
            secret=secret
        )

    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse and extract relevant data from webhook payload.

        Returns:
            Dict with extracted data, or None if invalid
        """
        try:
            return {
                "event_type": payload.get("type"),
                "event_id": payload.get("id"),
                "data": payload.get("data", {}),
                # ... extract what you need
            }
        except Exception as e:
            logger.error(f"Failed to parse payload: {e}")
            return None

    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Determine if this webhook event should be processed.

        Returns:
            True if should process, False to ignore
        """
        event_type = parsed_data.get("event_type")
        # Example: only process "error" events
        return event_type == "error"

    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """
        Process the webhook and return response.

        Returns:
            WebhookResponse with status, task_id, message
        """
        # Queue task for processing
        from task_queue import RedisQueue
        from models import TaskSource

        queue = RedisQueue()
        task_data = {
            "source": TaskSource.CUSTOM.value,  # Add to TaskSource enum
            "description": parsed_data.get("data", {}).get("message"),
            "event_id": parsed_data.get("event_id"),
        }

        task_id = await queue.push(settings.PLANNING_QUEUE, task_data)

        return WebhookResponse(
            status="queued",
            task_id=task_id,
            message=f"Custom event {parsed_data['event_id']} queued for processing"
        )
```

**Step 2:** Update main.py to add the endpoint

```python
# In main.py, add webhook endpoint:

@app.post("/webhooks/custom", tags=["Webhooks"])
async def custom_webhook(request: Request):
    """Custom webhook endpoint."""
    return await generic_webhook_handler("custom", request)
```

**Step 3:** That's it! The webhook is auto-discovered and registered.

### Webhook Interface

All webhook handlers must implement:

| Method | Purpose | Returns |
|--------|---------|---------|
| `metadata` | Define webhook name, endpoint, description | `WebhookMetadata` |
| `validate_signature()` | Verify webhook authenticity (HMAC, etc.) | `bool` |
| `parse_payload()` | Extract relevant data from webhook | `Dict` or `None` |
| `should_process()` | Determine if event should be processed | `bool` |
| `handle()` | Process the webhook (queue tasks, etc.) | `WebhookResponse` |

Optional override:
- `on_error()` - Custom error handling

---

## Agent Plugins

### Architecture

```
agents/
├── core/
│   ├── agent_base.py            # Base classes
│   ├── agent_registry.py        # Central registry
│   └── agent_metrics.py         # Metrics tracking
├── sub_agents/
│   ├── __init__.py              # Auto-discovery logic
│   ├── planning_agent.py        # Planning agent plugin
│   ├── executor_agent.py        # Execution agent plugin
│   └── [your_agent.py]          # Add new agents here!
└── planning-agent/              # Existing worker (will migrate)
    └── worker.py
```

### Adding a New Agent

**Step 1:** Create a new file in `sub_agents/` directory

```python
# sub_agents/custom_agent.py

from core.agent_base import (
    BaseAgent,
    AgentMetadata,
    AgentCapability,
    AgentContext,
    AgentResult,
    AgentUsageMetrics,
)

class CustomAgent(BaseAgent):
    """Custom agent that does something specific."""

    @property
    def metadata(self) -> AgentMetadata:
        """Define agent metadata."""
        return AgentMetadata(
            name="custom-agent",
            display_name="Custom Agent",
            description="Performs custom analysis and operations",
            capabilities=[
                AgentCapability.ANALYSIS,
                AgentCapability.ENRICHMENT
            ],
            version="1.0.0",
            enabled=True,
            max_retries=3,
            timeout_seconds=1800
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's main logic.

        Args:
            context: AgentContext with task data, session_id, config

        Returns:
            AgentResult with output, metrics, next_agent
        """
        task = context.task
        task_id = context.task_id
        session_id = context.session_id

        logger.info(f"Custom Agent executing for task {task_id}")

        # Do your agent logic here
        # Example: call external API, run analysis, etc.
        result_data = await self._do_custom_work(task)

        # Return result
        return AgentResult(
            success=True,
            agent_name=self.metadata.name,
            session_id=session_id,
            output={
                "result": result_data,
                "task_id": task_id,
            },
            usage=AgentUsageMetrics(
                input_tokens=1000,
                output_tokens=500,
                total_tokens=1500,
                total_cost_usd=0.05,
                model_used="claude-sonnet-4.5"
            ),
            next_agent="executor-agent"  # Optional: chain to next agent
        )

    async def _do_custom_work(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Your custom logic here."""
        return {"status": "completed"}
```

**Step 2:** That's it! The agent is auto-discovered and registered.

### Agent Interface

All agents must implement:

| Method | Purpose | Returns |
|--------|---------|---------|
| `metadata` | Define agent name, capabilities, etc. | `AgentMetadata` |
| `execute()` | Main agent logic | `AgentResult` |

Optional overrides:
- `pre_execute()` - Pre-execution validation (return `False` to skip)
- `post_execute()` - Post-execution processing
- `on_error()` - Custom error handling
- `should_retry()` - Custom retry logic

### Agent Capabilities

Available capabilities (can have multiple):

```python
class AgentCapability(str, Enum):
    PLANNING = "planning"
    EXECUTION = "execution"
    DISCOVERY = "discovery"
    REVIEW = "review"
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    ENRICHMENT = "enrichment"
```

### Using the Agent Registry

```python
from agents.core.agent_registry import agent_registry

# Initialize (auto-discovers agents)
agent_registry.auto_discover()

# Execute an agent
context = AgentContext(
    task_id="task-123",
    session_id="session-456",
    task={"description": "Fix bug"},
    config={}
)

result = await agent_registry.execute_agent("planning-agent", context)
```

---

## Metrics Tracking

All agent executions are automatically tracked:

### Prometheus Metrics

```python
# Execution count by agent and status
ai_agent_execution_total{agent="planning-agent", status="success", task_type="jira_enrich"}

# Execution duration
ai_agent_execution_duration_seconds{agent="planning-agent", task_type="jira_enrich"}

# Cost tracking
ai_agent_cost_total_usd{agent="planning-agent", model="claude-sonnet-4.5"}

# Token usage
ai_agent_tokens_total{agent="planning-agent", token_type="input"}

# Active sessions
ai_agent_sessions_active{agent="planning-agent"}
```

### Accessing Metrics

**Dashboard API:**
```bash
GET /api/dashboard/agent-stats?agent=planning-agent
GET /api/dashboard/cost-breakdown?group_by=agent
GET /api/dashboard/agent-chain-analytics
```

**Prometheus Endpoint:**
```bash
GET /metrics
```

---

## Dashboard API

### Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/dashboard/agents` | List all registered agents |
| `GET /api/dashboard/tasks` | Get tasks with filtering |
| `GET /api/dashboard/tasks/{task_id}` | Get task details with agent executions |
| `GET /api/dashboard/agent-stats` | Get agent statistics |
| `GET /api/dashboard/cost-breakdown` | Get cost breakdown by agent/day/task_type |
| `GET /api/dashboard/agent-chain-analytics` | Get agent chain patterns |
| `GET /api/dashboard/metrics-summary` | Get dashboard overview metrics |

### Example Queries

**Get all agents:**
```bash
curl http://localhost:8000/api/dashboard/agents
```

**Get tasks filtered by agent:**
```bash
curl "http://localhost:8000/api/dashboard/tasks?agent=planning-agent&status=completed&limit=10"
```

**Get cost breakdown by day:**
```bash
curl "http://localhost:8000/api/dashboard/cost-breakdown?group_by=day&start_date=2024-01-01"
```

---

## Testing

### Testing Webhook Plugins

```python
# tests/webhooks/test_custom_webhook.py
import pytest
from webhooks.custom_webhook import CustomWebhookHandler

@pytest.mark.asyncio
async def test_should_process_error_events():
    handler = CustomWebhookHandler()

    parsed_data = {
        "event_type": "error",
        "event_id": "123"
    }

    assert await handler.should_process(parsed_data) is True

@pytest.mark.asyncio
async def test_should_not_process_info_events():
    handler = CustomWebhookHandler()

    parsed_data = {
        "event_type": "info",
        "event_id": "456"
    }

    assert await handler.should_process(parsed_data) is False
```

### Testing Agent Plugins

```python
# tests/sub_agents/test_custom_agent.py
import pytest
from sub_agents.custom_agent import CustomAgent
from core.agent_base import AgentContext

@pytest.mark.asyncio
async def test_custom_agent_execution():
    agent = CustomAgent()

    context = AgentContext(
        task_id="task-123",
        session_id="session-456",
        task={"description": "Test task"},
        config={}
    )

    result = await agent.execute(context)

    assert result.success is True
    assert result.agent_name == "custom-agent"
    assert "result" in result.output
```

---

## Best Practices

### Webhook Plugins

1. **Always validate signatures** - Prevent unauthorized access
2. **Parse payloads safely** - Return `None` on parse errors
3. **Use specific event filters** - Only process relevant events in `should_process()`
4. **Queue tasks appropriately** - Planning vs. execution queue
5. **Log extensively** - Makes debugging easier

### Agent Plugins

1. **Keep execute() focused** - One clear responsibility
2. **Track usage metrics** - Token counts and costs
3. **Handle errors gracefully** - Implement `on_error()` if needed
4. **Set appropriate timeouts** - Prevent hanging operations
5. **Test in isolation** - Unit test each agent separately

### General

1. **Follow naming conventions** - `*_webhook.py` and `*_agent.py`
2. **Document your plugins** - Clear docstrings and type hints
3. **Update metadata versions** - When making breaking changes
4. **Test before deploying** - Webhook signatures, agent logic
5. **Monitor metrics** - Watch costs and performance

---

## Migration Guide

### Migrating Existing Webhooks

**Before (Old Route System):**
```python
# routes/custom.py
@router.post("/")
async def custom_webhook(request: Request):
    payload = await request.json()
    # ... lots of inline logic ...
```

**After (Plugin System):**
```python
# webhooks/custom_webhook.py
class CustomWebhookHandler(BaseWebhookHandler):
    # ... clean, testable, reusable ...
```

### Migrating Existing Agents

**Before (Worker Loop):**
```python
# agents/custom-agent/worker.py
async def process_task(task_data):
    # ... inline logic ...
```

**After (Plugin System):**
```python
# agents/sub_agents/custom_agent.py
class CustomAgent(BaseAgent):
    async def execute(self, context):
        # ... clean, testable, reusable ...
```

---

## Troubleshooting

### Webhook Not Discovered

Check:
1. File naming: Must end with `_webhook.py`
2. Class naming: Must inherit from `BaseWebhookHandler`
3. Instantiation: Must be instantiable without arguments
4. Imports: Check for import errors in logs

### Agent Not Registered

Check:
1. File naming: Must end with `_agent.py`
2. Class naming: Must inherit from `BaseAgent`
3. Instantiation: Must be instantiable without arguments
4. Directory: Must be in `sub_agents/` directory

### Signature Validation Failing

Check:
1. Environment variable is set correctly
2. Signature header name matches (X-Hub-Signature-256, etc.)
3. Payload is raw bytes, not parsed JSON
4. Secret matches webhook configuration

---

## Summary

The plugin-based architecture makes it **trivially easy** to extend the system:

1. **Add Webhook**: Create `webhooks/my_webhook.py` → Done!
2. **Add Agent**: Create `sub_agents/my_agent.py` → Done!
3. **Test**: Write unit tests for your plugin
4. **Deploy**: Auto-discovered and registered on startup

No core code changes. No complex configuration. Just clean, modular plugins that are easy to understand, test, and maintain.
