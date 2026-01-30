# Agent Bot - TDD Implementation Guide

## Part 5: Agent Organization & Webhooks Extension

---

## Strict Project Rules Reminder

| Rule | Enforcement |
|------|-------------|
| **Max 300 lines per file** | Split into modules |
| **NO `any` types** | `ConfigDict(strict=True)` everywhere |
| **NO comments in code** | Self-explanatory naming only |
| **Tests < 5 seconds** | Mock all external calls |
| **Structured logging** | `logger.info("event", key=value)` |
| **Async for I/O** | `httpx.AsyncClient`, not `requests` |
| **TDD workflow** | RED → GREEN → REFACTOR |

---

## Phase 9: Webhook Extension System

### Step 9.1: Create Directory Structure

```bash
mkdir -p api-gateway/webhooks/registry
mkdir -p api-gateway/webhooks/handlers
mkdir -p api-gateway/tests/webhooks

touch api-gateway/webhooks/registry/__init__.py
touch api-gateway/webhooks/registry/protocol.py
touch api-gateway/webhooks/registry/registry.py
touch api-gateway/webhooks/handlers/__init__.py
touch api-gateway/webhooks/handlers/github.py
touch api-gateway/webhooks/handlers/jira.py
touch api-gateway/webhooks/handlers/slack.py
touch api-gateway/tests/webhooks/__init__.py
touch api-gateway/tests/webhooks/test_registry.py
touch api-gateway/tests/webhooks/test_github_handler.py
```

### Step 9.2: Write Tests FIRST - Webhook Protocol

**File: `api-gateway/tests/webhooks/test_registry.py`** (< 150 lines)

```python
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from webhooks.registry.protocol import (
    WebhookPayload,
    WebhookResponse,
    WebhookHandlerProtocol,
)
from webhooks.registry.registry import WebhookRegistry


class MockWebhookHandler:
    def __init__(self, provider: str):
        self._provider = provider

    async def validate(self, payload: bytes, headers: dict) -> bool:
        return True

    async def parse(self, payload: bytes, headers: dict) -> WebhookPayload:
        return WebhookPayload(
            provider=self._provider,
            event_type="test_event",
            installation_id="inst-123",
            organization_id="org-456",
            raw_payload={"test": "data"},
            timestamp=datetime.now(timezone.utc),
        )

    async def handle(
        self, payload: WebhookPayload, access_token: str
    ) -> WebhookResponse:
        return WebhookResponse(
            success=True,
            task_id="task-789",
        )


class TestWebhookRegistry:
    @pytest.fixture
    def registry(self) -> WebhookRegistry:
        return WebhookRegistry()

    def test_register_handler(self, registry: WebhookRegistry):
        handler = MockWebhookHandler("github")
        registry.register("github", handler)

        assert "github" in registry.list_providers()

    def test_get_registered_handler(self, registry: WebhookRegistry):
        handler = MockWebhookHandler("github")
        registry.register("github", handler)

        retrieved = registry.get_handler("github")

        assert retrieved is handler

    def test_get_unregistered_handler_returns_none(
        self, registry: WebhookRegistry
    ):
        result = registry.get_handler("unknown")

        assert result is None

    def test_list_providers(self, registry: WebhookRegistry):
        registry.register("github", MockWebhookHandler("github"))
        registry.register("jira", MockWebhookHandler("jira"))
        registry.register("slack", MockWebhookHandler("slack"))

        providers = registry.list_providers()

        assert set(providers) == {"github", "jira", "slack"}

    def test_unregister_handler(self, registry: WebhookRegistry):
        handler = MockWebhookHandler("github")
        registry.register("github", handler)
        registry.unregister("github")

        assert registry.get_handler("github") is None

    def test_register_replaces_existing(self, registry: WebhookRegistry):
        handler1 = MockWebhookHandler("github")
        handler2 = MockWebhookHandler("github")

        registry.register("github", handler1)
        registry.register("github", handler2)

        assert registry.get_handler("github") is handler2


class TestWebhookPayload:
    def test_create_valid_payload(self):
        payload = WebhookPayload(
            provider="github",
            event_type="pull_request.opened",
            installation_id="inst-123",
            organization_id="org-456",
            raw_payload={"action": "opened"},
            timestamp=datetime.now(timezone.utc),
        )

        assert payload.provider == "github"
        assert payload.event_type == "pull_request.opened"

    def test_payload_with_metadata(self):
        payload = WebhookPayload(
            provider="github",
            event_type="pull_request.opened",
            installation_id="inst-123",
            organization_id="org-456",
            raw_payload={},
            timestamp=datetime.now(timezone.utc),
            metadata={"pr_number": "42", "repo": "owner/repo"},
        )

        assert payload.metadata["pr_number"] == "42"


class TestWebhookResponse:
    def test_success_response(self):
        response = WebhookResponse(
            success=True,
            task_id="task-123",
        )

        assert response.success is True
        assert response.task_id == "task-123"

    def test_failure_response(self):
        response = WebhookResponse(
            success=False,
            error="Invalid signature",
        )

        assert response.success is False
        assert response.error == "Invalid signature"
```

### Step 9.3: Implement Webhook Protocol

**File: `api-gateway/webhooks/registry/protocol.py`** (< 80 lines)

```python
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class WebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    provider: str
    event_type: str
    installation_id: str
    organization_id: str
    raw_payload: dict
    timestamp: datetime
    metadata: dict[str, str] = {}


class WebhookResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    task_id: str | None = None
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


class TaskCreationRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    provider: str
    event_type: str
    installation_id: str
    organization_id: str
    input_message: str
    source_metadata: dict[str, str]
    priority: int = 2


@runtime_checkable
class WebhookHandlerProtocol(Protocol):
    async def validate(
        self, payload: bytes, headers: dict, secret: str
    ) -> bool:
        ...

    async def parse(
        self, payload: bytes, headers: dict
    ) -> WebhookPayload:
        ...

    async def should_process(self, payload: WebhookPayload) -> bool:
        ...

    async def create_task_request(
        self, payload: WebhookPayload
    ) -> TaskCreationRequest:
        ...


class SignatureValidationError(Exception):
    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f"Signature validation failed for {provider}: {reason}")


class PayloadParseError(Exception):
    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f"Payload parsing failed for {provider}: {reason}")
```

### Step 9.4: Implement Webhook Registry

**File: `api-gateway/webhooks/registry/registry.py`** (< 80 lines)

```python
import structlog

from .protocol import WebhookHandlerProtocol

logger = structlog.get_logger()


class WebhookRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, WebhookHandlerProtocol] = {}

    def register(
        self, provider: str, handler: WebhookHandlerProtocol
    ) -> None:
        logger.info("registering_webhook_handler", provider=provider)
        self._handlers[provider] = handler

    def unregister(self, provider: str) -> None:
        if provider in self._handlers:
            logger.info("unregistering_webhook_handler", provider=provider)
            del self._handlers[provider]

    def get_handler(self, provider: str) -> WebhookHandlerProtocol | None:
        return self._handlers.get(provider)

    def list_providers(self) -> list[str]:
        return list(self._handlers.keys())

    def has_handler(self, provider: str) -> bool:
        return provider in self._handlers


def create_default_registry() -> WebhookRegistry:
    from webhooks.handlers.github import GitHubWebhookHandler
    from webhooks.handlers.jira import JiraWebhookHandler
    from webhooks.handlers.slack import SlackWebhookHandler

    registry = WebhookRegistry()
    registry.register("github", GitHubWebhookHandler())
    registry.register("jira", JiraWebhookHandler())
    registry.register("slack", SlackWebhookHandler())

    return registry
```

### Step 9.5: Write Tests FIRST - GitHub Webhook Handler

**File: `api-gateway/tests/webhooks/test_github_handler.py`** (< 200 lines)

```python
import pytest
import hmac
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from webhooks.handlers.github import GitHubWebhookHandler
from webhooks.registry.protocol import (
    WebhookPayload,
    SignatureValidationError,
)


@pytest.fixture
def handler() -> GitHubWebhookHandler:
    return GitHubWebhookHandler()


@pytest.fixture
def sample_pr_payload() -> dict:
    return {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "Fix bug in auth",
            "body": "@agent review this PR",
            "head": {"ref": "feature-branch", "sha": "abc123"},
            "base": {"ref": "main"},
            "user": {"login": "developer"},
        },
        "repository": {
            "full_name": "owner/repo",
            "default_branch": "main",
        },
        "installation": {"id": 12345},
        "sender": {"login": "developer"},
    }


@pytest.fixture
def sample_comment_payload() -> dict:
    return {
        "action": "created",
        "comment": {
            "body": "@agent analyze src/main.py",
            "user": {"login": "developer"},
        },
        "issue": {
            "number": 42,
            "pull_request": {"url": "https://api.github.com/..."},
        },
        "repository": {"full_name": "owner/repo"},
        "installation": {"id": 12345},
        "sender": {"login": "developer"},
    }


class TestGitHubWebhookHandlerValidate:
    @pytest.mark.asyncio
    async def test_valid_signature(
        self, handler: GitHubWebhookHandler, sample_pr_payload: dict
    ):
        secret = "test_secret"
        payload_bytes = json.dumps(sample_pr_payload).encode()
        signature = "sha256=" + hmac.new(
            secret.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()

        headers = {"x-hub-signature-256": signature}

        result = await handler.validate(payload_bytes, headers, secret)

        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_signature(
        self, handler: GitHubWebhookHandler, sample_pr_payload: dict
    ):
        payload_bytes = json.dumps(sample_pr_payload).encode()
        headers = {"x-hub-signature-256": "sha256=invalid"}

        result = await handler.validate(payload_bytes, headers, "secret")

        assert result is False

    @pytest.mark.asyncio
    async def test_missing_signature_header(
        self, handler: GitHubWebhookHandler, sample_pr_payload: dict
    ):
        payload_bytes = json.dumps(sample_pr_payload).encode()
        headers = {}

        result = await handler.validate(payload_bytes, headers, "secret")

        assert result is False


class TestGitHubWebhookHandlerParse:
    @pytest.mark.asyncio
    async def test_parse_pr_opened(
        self, handler: GitHubWebhookHandler, sample_pr_payload: dict
    ):
        payload_bytes = json.dumps(sample_pr_payload).encode()
        headers = {"x-github-event": "pull_request"}

        result = await handler.parse(payload_bytes, headers)

        assert result.provider == "github"
        assert result.event_type == "pull_request.opened"
        assert result.installation_id == "12345"
        assert result.metadata["pr_number"] == "42"
        assert result.metadata["repo"] == "owner/repo"

    @pytest.mark.asyncio
    async def test_parse_issue_comment(
        self, handler: GitHubWebhookHandler, sample_comment_payload: dict
    ):
        payload_bytes = json.dumps(sample_comment_payload).encode()
        headers = {"x-github-event": "issue_comment"}

        result = await handler.parse(payload_bytes, headers)

        assert result.event_type == "issue_comment.created"
        assert "@agent" in result.metadata.get("comment_body", "")


class TestGitHubWebhookHandlerShouldProcess:
    @pytest.mark.asyncio
    async def test_should_process_pr_with_agent_mention(
        self, handler: GitHubWebhookHandler
    ):
        payload = WebhookPayload(
            provider="github",
            event_type="issue_comment.created",
            installation_id="12345",
            organization_id="owner",
            raw_payload={},
            timestamp=datetime.now(timezone.utc),
            metadata={"comment_body": "@agent review this"},
        )

        result = await handler.should_process(payload)

        assert result is True

    @pytest.mark.asyncio
    async def test_should_not_process_without_mention(
        self, handler: GitHubWebhookHandler
    ):
        payload = WebhookPayload(
            provider="github",
            event_type="issue_comment.created",
            installation_id="12345",
            organization_id="owner",
            raw_payload={},
            timestamp=datetime.now(timezone.utc),
            metadata={"comment_body": "Just a regular comment"},
        )

        result = await handler.should_process(payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_should_process_pr_with_label(
        self, handler: GitHubWebhookHandler
    ):
        payload = WebhookPayload(
            provider="github",
            event_type="pull_request.labeled",
            installation_id="12345",
            organization_id="owner",
            raw_payload={},
            timestamp=datetime.now(timezone.utc),
            metadata={"labels": "agent-review,bug"},
        )

        result = await handler.should_process(payload)

        assert result is True


class TestGitHubWebhookHandlerCreateTask:
    @pytest.mark.asyncio
    async def test_create_task_from_comment(
        self, handler: GitHubWebhookHandler
    ):
        payload = WebhookPayload(
            provider="github",
            event_type="issue_comment.created",
            installation_id="12345",
            organization_id="owner",
            raw_payload={},
            timestamp=datetime.now(timezone.utc),
            metadata={
                "comment_body": "@agent analyze src/main.py",
                "pr_number": "42",
                "repo": "owner/repo",
            },
        )

        task = await handler.create_task_request(payload)

        assert "analyze src/main.py" in task.input_message
        assert task.source_metadata["pr_number"] == "42"
```

### Step 9.6: Implement GitHub Webhook Handler

**File: `api-gateway/webhooks/handlers/github.py`** (< 200 lines)

```python
import hmac
import hashlib
import json
import re
from datetime import datetime, timezone

import structlog

from ..registry.protocol import (
    WebhookPayload,
    TaskCreationRequest,
    PayloadParseError,
)

logger = structlog.get_logger()

AGENT_MENTION_PATTERN = re.compile(r"@agent\s+(.+?)(?:\n|$)", re.IGNORECASE)
AGENT_LABELS = {"agent-review", "agent-fix", "agent-analyze"}


class GitHubWebhookHandler:
    async def validate(
        self, payload: bytes, headers: dict, secret: str
    ) -> bool:
        signature = headers.get("x-hub-signature-256", "")
        if not signature:
            logger.warning("github_webhook_missing_signature")
            return False

        expected = "sha256=" + hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def parse(
        self, payload: bytes, headers: dict
    ) -> WebhookPayload:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise PayloadParseError("github", f"Invalid JSON: {e}")

        event_type = headers.get("x-github-event", "unknown")
        action = data.get("action", "")
        full_event = f"{event_type}.{action}" if action else event_type

        installation_id = str(data.get("installation", {}).get("id", ""))
        repo = data.get("repository", {}).get("full_name", "")
        organization_id = repo.split("/")[0] if "/" in repo else ""

        metadata = self._extract_metadata(data, event_type)

        return WebhookPayload(
            provider="github",
            event_type=full_event,
            installation_id=installation_id,
            organization_id=organization_id,
            raw_payload=data,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )

    async def should_process(self, payload: WebhookPayload) -> bool:
        if self._has_agent_mention(payload):
            return True

        if self._has_agent_label(payload):
            return True

        if self._is_auto_review_event(payload):
            return True

        return False

    async def create_task_request(
        self, payload: WebhookPayload
    ) -> TaskCreationRequest:
        input_message = self._extract_input_message(payload)

        return TaskCreationRequest(
            provider="github",
            event_type=payload.event_type,
            installation_id=payload.installation_id,
            organization_id=payload.organization_id,
            input_message=input_message,
            source_metadata=payload.metadata,
            priority=self._determine_priority(payload),
        )

    def _extract_metadata(self, data: dict, event_type: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        repo = data.get("repository", {})
        metadata["repo"] = repo.get("full_name", "")
        metadata["default_branch"] = repo.get("default_branch", "main")

        if "pull_request" in data:
            pr = data["pull_request"]
            metadata["pr_number"] = str(pr.get("number", ""))
            metadata["pr_title"] = pr.get("title", "")
            metadata["pr_body"] = pr.get("body", "") or ""
            metadata["head_ref"] = pr.get("head", {}).get("ref", "")
            metadata["head_sha"] = pr.get("head", {}).get("sha", "")
            metadata["base_ref"] = pr.get("base", {}).get("ref", "")

        if "comment" in data:
            comment = data["comment"]
            metadata["comment_body"] = comment.get("body", "")
            metadata["comment_user"] = comment.get("user", {}).get("login", "")

        if "issue" in data:
            issue = data["issue"]
            metadata["issue_number"] = str(issue.get("number", ""))
            if not metadata.get("pr_number") and "pull_request" in issue:
                metadata["pr_number"] = metadata["issue_number"]

        if "label" in data:
            metadata["label"] = data["label"].get("name", "")

        labels = data.get("pull_request", {}).get("labels", [])
        if labels:
            metadata["labels"] = ",".join(l.get("name", "") for l in labels)

        return metadata

    def _has_agent_mention(self, payload: WebhookPayload) -> bool:
        comment_body = payload.metadata.get("comment_body", "")
        pr_body = payload.metadata.get("pr_body", "")

        return bool(
            AGENT_MENTION_PATTERN.search(comment_body)
            or AGENT_MENTION_PATTERN.search(pr_body)
        )

    def _has_agent_label(self, payload: WebhookPayload) -> bool:
        labels_str = payload.metadata.get("labels", "")
        labels = set(labels_str.lower().split(","))
        return bool(labels & AGENT_LABELS)

    def _is_auto_review_event(self, payload: WebhookPayload) -> bool:
        return payload.event_type == "pull_request.opened"

    def _extract_input_message(self, payload: WebhookPayload) -> str:
        comment_body = payload.metadata.get("comment_body", "")
        match = AGENT_MENTION_PATTERN.search(comment_body)
        if match:
            return match.group(1).strip()

        if payload.event_type == "pull_request.opened":
            return f"Review PR #{payload.metadata.get('pr_number')}: {payload.metadata.get('pr_title')}"

        return f"Process {payload.event_type}"

    def _determine_priority(self, payload: WebhookPayload) -> int:
        if "critical" in payload.metadata.get("labels", "").lower():
            return 0
        if "urgent" in payload.metadata.get("labels", "").lower():
            return 1
        return 2
```

---

## Phase 10: Webhook Router Integration

### Step 10.1: Write Tests FIRST - Webhook Router

**File: `api-gateway/tests/webhooks/test_router.py`** (< 150 lines)

```python
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json
import hmac
import hashlib

from webhooks.router import create_webhook_router
from webhooks.registry.registry import WebhookRegistry
from webhooks.handlers.github import GitHubWebhookHandler
from token_service import TokenService, TokenInfo, Platform


@pytest.fixture
def mock_token_service() -> AsyncMock:
    service = AsyncMock(spec=TokenService)
    service.get_token.return_value = TokenInfo(
        access_token="gho_xxxx",
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        scopes=["repo"],
    )
    service.get_webhook_secret.return_value = "test_secret"
    return service


@pytest.fixture
def mock_queue() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def registry() -> WebhookRegistry:
    reg = WebhookRegistry()
    reg.register("github", GitHubWebhookHandler())
    return reg


@pytest.fixture
def app(
    registry: WebhookRegistry,
    mock_token_service: AsyncMock,
    mock_queue: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    router = create_webhook_router(
        registry=registry,
        token_service=mock_token_service,
        queue=mock_queue,
    )
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestWebhookRouterGitHub:
    def test_valid_webhook_accepted(
        self,
        client: TestClient,
        mock_queue: AsyncMock,
    ):
        payload = {
            "action": "created",
            "comment": {"body": "@agent review", "user": {"login": "dev"}},
            "issue": {"number": 42, "pull_request": {"url": "..."}},
            "repository": {"full_name": "owner/repo"},
            "installation": {"id": 12345},
            "sender": {"login": "dev"},
        }
        payload_bytes = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(
            b"test_secret", payload_bytes, hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "x-github-event": "issue_comment",
                "x-hub-signature-256": signature,
                "content-type": "application/json",
            },
        )

        assert response.status_code == 200
        mock_queue.enqueue.assert_called_once()

    def test_invalid_signature_rejected(
        self,
        client: TestClient,
    ):
        payload = {"test": "data"}
        payload_bytes = json.dumps(payload).encode()

        response = client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "x-github-event": "push",
                "x-hub-signature-256": "sha256=invalid",
                "content-type": "application/json",
            },
        )

        assert response.status_code == 401

    def test_unknown_provider_returns_404(
        self,
        client: TestClient,
    ):
        response = client.post(
            "/webhooks/unknown",
            content=b"{}",
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 404


class TestWebhookRouterSkipped:
    def test_non_agent_comment_skipped(
        self,
        client: TestClient,
        mock_queue: AsyncMock,
    ):
        payload = {
            "action": "created",
            "comment": {"body": "Just a comment", "user": {"login": "dev"}},
            "issue": {"number": 42},
            "repository": {"full_name": "owner/repo"},
            "installation": {"id": 12345},
            "sender": {"login": "dev"},
        }
        payload_bytes = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(
            b"test_secret", payload_bytes, hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "x-github-event": "issue_comment",
                "x-hub-signature-256": signature,
                "content-type": "application/json",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skipped"] is True
        mock_queue.enqueue.assert_not_called()
```

### Step 10.2: Implement Webhook Router

**File: `api-gateway/webhooks/router.py`** (< 150 lines)

```python
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException, status
import structlog

from .registry.registry import WebhookRegistry
from .registry.protocol import (
    WebhookResponse,
    SignatureValidationError,
    PayloadParseError,
)
from token_service import TokenService, Platform
from ports.queue import QueuePort, TaskQueueMessage, TaskPriority

logger = structlog.get_logger()


def create_webhook_router(
    registry: WebhookRegistry,
    token_service: TokenService,
    queue: QueuePort,
) -> APIRouter:
    router = APIRouter(prefix="/webhooks", tags=["webhooks"])

    @router.post("/{provider}")
    async def handle_webhook(provider: str, request: Request) -> dict:
        handler = registry.get_handler(provider)
        if not handler:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown webhook provider: {provider}",
            )

        payload_bytes = await request.body()
        headers = dict(request.headers)

        logger.info(
            "webhook_received",
            provider=provider,
            content_length=len(payload_bytes),
        )

        try:
            parsed = await handler.parse(payload_bytes, headers)
        except PayloadParseError as e:
            logger.error("webhook_parse_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        try:
            webhook_secret = await token_service.get_webhook_secret(
                platform=Platform(provider),
                organization_id=parsed.organization_id,
            )
        except Exception as e:
            logger.error(
                "webhook_secret_lookup_failed",
                organization_id=parsed.organization_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Installation not found",
            )

        is_valid = await handler.validate(payload_bytes, headers, webhook_secret)
        if not is_valid:
            logger.warning(
                "webhook_signature_invalid",
                provider=provider,
                installation_id=parsed.installation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

        should_process = await handler.should_process(parsed)
        if not should_process:
            logger.info(
                "webhook_skipped",
                provider=provider,
                event_type=parsed.event_type,
                reason="no_trigger_pattern",
            )
            return {
                "success": True,
                "skipped": True,
                "reason": "Event does not require processing",
            }

        task_request = await handler.create_task_request(parsed)
        task_id = f"task-{uuid4().hex[:12]}"

        token_info = await token_service.get_token(
            platform=Platform(provider),
            organization_id=parsed.organization_id,
        )

        message = TaskQueueMessage(
            task_id=task_id,
            installation_id=parsed.installation_id,
            provider=provider,
            input_message=task_request.input_message,
            priority=TaskPriority(task_request.priority),
            source_metadata=task_request.source_metadata,
            created_at=datetime.now(timezone.utc),
        )

        await queue.enqueue(message)

        logger.info(
            "webhook_task_created",
            task_id=task_id,
            provider=provider,
            event_type=parsed.event_type,
        )

        return {
            "success": True,
            "task_id": task_id,
            "skipped": False,
        }

    @router.get("/health")
    async def health() -> dict:
        return {
            "status": "healthy",
            "providers": registry.list_providers(),
        }

    return router
```

---

## Phase 11: Agent Configuration Files

### Step 11.1: Create Agent Definitions

**File: `agent-container/.claude/agents/planning-agent.md`**

```markdown
# Planning Agent

## Role
Decompose complex tasks into actionable steps and coordinate execution.

## Activation Triggers
- Multi-file changes requested
- Tasks requiring multiple tools
- Complex analysis requests

## Required Skills
- code-analysis
- knowledge-graph
- repo-context

## Process
1. Analyze request scope and intent
2. Query knowledge graph for affected components
3. Create execution plan with dependencies
4. Assign tasks to appropriate sub-agents
5. Aggregate and verify results

## Output Format
Structured plan with tasks, dependencies, and estimated duration.

## Escalation
- More than 10 tasks needed: Ask user to narrow scope
- Circular dependencies: Report and halt
- Unknown patterns: Ask for clarification
```

**File: `agent-container/.claude/agents/code-review-agent.md`**

```markdown
# Code Review Agent

## Role
Perform comprehensive code review with actionable feedback.

## Activation Triggers
- @agent review command
- PR opened with agent-review label
- Review request via webhook

## Focus Areas
1. Code quality and best practices
2. Potential bugs and edge cases
3. Security vulnerabilities
4. Test coverage gaps
5. Performance concerns

## Required Skills
- code-analysis
- knowledge-graph
- test-execution

## Process
1. Fetch PR diff and context
2. Query knowledge graph for affected code paths
3. Analyze each changed file
4. Check test coverage for changes
5. Generate review with line-specific comments

## Output Format
GitHub review comment with summary, issues, and suggestions.

## Quality Criteria
- Specific line references for all issues
- Severity levels: critical, warning, suggestion
- Actionable recommendations
```

**File: `agent-container/.claude/agents/bug-fix-agent.md`**

```markdown
# Bug Fix Agent

## Role
Investigate, diagnose, and fix bugs with minimal code changes.

## Activation Triggers
- Sentry error events
- @agent fix command
- Bug reports from Jira

## Required Skills
- code-analysis
- knowledge-graph
- git-operations
- test-execution

## Process
1. Parse error context (stack trace, logs)
2. Query knowledge graph for affected functions
3. Identify root cause via static analysis
4. Generate minimal fix
5. Create regression test
6. Verify existing tests pass

## Success Criteria
- Root cause identified and documented
- Fix under 50 lines changed
- Regression test added
- All tests pass

## Escalation
- Cannot reproduce: Request more context
- Fix over 100 lines: Suggest refactor first
- Security bug: Flag for human review
```

### Step 11.2: Create Skills Definitions

**File: `agent-container/.claude/skills/knowledge-graph.md`**

```markdown
# Knowledge Graph Skill

## Purpose
Query code relationships for context and impact analysis.

## Available Queries

### Find Function Callers
find_callers(function_name) -> list of calling locations

### Get Class Hierarchy
get_hierarchy(class_name) -> parents and children

### Impact Analysis
find_affected(file_path) -> files depending on this file

### Test Coverage
find_tests(function_name) -> tests covering this function

## Usage Guidelines
- Query before reading large files
- Use for change risk assessment
- Combine with AST for detail

## MCP Tool Mapping
- get_function_callers -> knowledge_graph_mcp.find_callers
- get_class_hierarchy -> knowledge_graph_mcp.get_hierarchy
- find_affected_by_change -> knowledge_graph_mcp.impact_analysis
```

**File: `agent-container/.claude/skills/git-operations.md`**

```markdown
# Git Operations Skill

## Purpose
Manage git operations for code changes.

## Available Operations

### Branch Management
- create_branch(name, from_ref)
- checkout(ref)
- delete_branch(name)

### Commit Operations
- stage_files(paths)
- commit(message)
- amend(message)

### PR Operations
- create_pr(title, body, base, head)
- update_pr(number, title, body)

## Safety Rules
- Never force push to main/master
- Always create feature branches
- Require meaningful commit messages
- Validate changes before commit

## MCP Tool Mapping
- Operations via github_mcp server
```

### Step 11.3: Create Command Definitions

**File: `agent-container/.claude/commands/review.md`**

```markdown
# Review Command

## Trigger Patterns
- @agent review
- @agent review this PR
- @agent please review
- Label: agent-review

## Parameters
- --focus security: Security-focused review
- --focus performance: Performance-focused review
- --strict: Apply stricter standards

## Behavior
1. Fetch PR diff
2. Activate code-review-agent
3. Post review comment to PR

## Output
Review comment with:
- Summary with status emoji
- Specific issues with line refs
- Improvement suggestions
```

**File: `agent-container/.claude/commands/fix.md`**

```markdown
# Fix Command

## Trigger Patterns
- @agent fix
- @agent fix this bug
- @agent please fix issue #N
- Sentry webhook

## Parameters
- --create-pr: Create PR with fix
- --test: Include regression test

## Behavior
1. Parse error context
2. Activate bug-fix-agent
3. Generate fix
4. Optionally create PR

## Output
- Root cause analysis
- Fix commit or PR
- Regression test
```

### Step 11.4: Create Hook Definitions

**File: `agent-container/.claude/hooks/pre-execution.md`**

```markdown
# Pre-Execution Hook

## Purpose
Prepare environment before task execution.

## Actions
1. Validate task inputs
2. Check resource availability
3. Load organization context
4. Clone/update repository
5. Index for knowledge graph
6. Log task start

## Validation Checks
- Task ID format valid
- Installation active
- Required skills available
- Repository accessible
- Resources sufficient

## Failure Handling
- Missing inputs: Return specific error
- Inactive installation: Log and skip
- Resource shortage: Queue for retry
- Repository inaccessible: Retry with backoff
```

**File: `agent-container/.claude/hooks/post-execution.md`**

```markdown
# Post-Execution Hook

## Purpose
Finalize task and deliver results.

## Actions
1. Validate output format
2. Post result to source platform
3. Update task status
4. Log completion metrics
5. Trigger cleanup if needed

## Metrics Logged
- Duration
- Tokens used
- Cost
- Success/failure
- Output size
```

**File: `agent-container/.claude/hooks/on-error.md`**

```markdown
# On-Error Hook

## Purpose
Handle errors gracefully.

## Actions
1. Log error with context
2. Determine if retryable
3. Post error to source (if appropriate)
4. Update task status
5. Trigger alerts if critical

## Retry Logic
- Network errors: Retry 3x with backoff
- Rate limits: Retry after delay
- Auth errors: Refresh token and retry once
- Validation errors: No retry, report

## Escalation
- Repeated failures: Alert team
- Security issues: Immediate notification
- Data loss risk: Stop and notify
```

---

## Run Tests to Verify Phase 9-11

```bash
cd api-gateway
pytest -v tests/webhooks/

# Expected: All tests pass < 5 seconds
```

---

## Checkpoint 5 Complete ✅

Before proceeding, verify:
- [ ] Webhook registry supports extension
- [ ] GitHub handler validates signatures
- [ ] Router integrates with token service
- [ ] Agent configs define clear behavior
- [ ] All files < 300 lines
- [ ] All tests pass

Continue to Part 6 for Final Integration and Database Migrations...
