# Implementation Plan: Close Business Requirements Gaps

> **Methodology**: Test-Driven Development (TDD)
> **Workflow**: Red → Green → Refactor → Resilience → Acceptance → Regression
> **Date**: January 2026

---

## Table of Contents

1. [Gap 1: Webhook Creator Agent](#gap-1-webhook-creator-agent)
2. [Gap 2: Skill webhook_config Synchronization](#gap-2-skill-webhook_config-synchronization)
3. [Gap 3: Dynamic Webhook Signature Verification](#gap-3-dynamic-webhook-signature-verification)
4. [Gap 4: Response to Webhook Source](#gap-4-response-to-webhook-source)
5. [Gap 5: Static + Dynamic Command Merging](#gap-5-static--dynamic-command-merging)
6. [Code Cleanup: Remove Redundant Comments](#code-cleanup-remove-redundant-comments)

---

## Gap 1: Webhook Creator Agent

### Objective
Create the missing `webhook-creator` agent that enables users to create webhooks via natural language chat.

### Files to Create
```
.claude/agents/webhook-creator.md
tests/unit/test_webhook_creator_agent.py
tests/integration/test_webhook_creator_flow.py
```

### Files to Modify
```
.claude/CLAUDE.md                    # Add webhook-creator to available agents
core/subagent_config.py              # Register webhook-creator in default subagents
```

---

### Phase 1: RED - Write Failing Tests First

#### Test File: `tests/unit/test_webhook_creator_agent.py`

```python
import pytest
from pathlib import Path

class TestWebhookCreatorAgentExists:
    def test_webhook_creator_agent_file_exists(self):
        agent_path = Path(".claude/agents/webhook-creator.md")
        assert agent_path.exists(), "webhook-creator.md must exist"

    def test_webhook_creator_has_required_frontmatter(self):
        agent_path = Path(".claude/agents/webhook-creator.md")
        content = agent_path.read_text()

        assert content.startswith("---"), "Must have frontmatter"
        assert "name: webhook-creator" in content
        assert "description:" in content
        assert "tools:" in content
        assert "model:" in content

    def test_webhook_creator_has_webhook_management_skill(self):
        agent_path = Path(".claude/agents/webhook-creator.md")
        content = agent_path.read_text()

        assert "webhook-management" in content.lower()

    def test_webhook_creator_references_static_webhooks(self):
        agent_path = Path(".claude/agents/webhook-creator.md")
        content = agent_path.read_text()

        assert "api/webhooks/github.py" in content or "static webhook" in content.lower()
```

#### Test File: `tests/integration/test_webhook_creator_flow.py`

```python
import pytest
from pathlib import Path

class TestWebhookCreatorIntegration:
    def test_webhook_creator_registered_in_subagent_config(self):
        from core.subagent_config import get_default_subagents

        subagents = get_default_subagents()
        agent_names = [s.get("name") for s in subagents] if subagents else []

        assert "webhook-creator" in agent_names

    def test_webhook_creator_in_claude_md(self):
        claude_md = Path(".claude/CLAUDE.md")
        content = claude_md.read_text()

        assert "webhook-creator" in content.lower()
```

---

### Phase 2: GREEN - Implement Minimum Code

#### Create: `.claude/agents/webhook-creator.md`

```markdown
---
name: webhook-creator
description: Creates webhooks with companion skills and sub-agents by learning from static webhook implementations
tools: Read, Write, Edit, Grep, Bash
model: sonnet
permissionMode: default
context: inherit
skills: webhook-management
---

Create webhooks dynamically by learning from existing static implementations.

## Capabilities

1. Learn from static webhook handlers in `api/webhooks/`
2. Create skill with `webhook_config` in frontmatter
3. Create companion sub-agent for webhook management
4. Register webhook in database via API

## Process

### Step 1: Analyze Request
- Extract provider (github, jira, slack, sentry, custom)
- Extract trigger events (issues.opened, pull_request.created, etc.)
- Extract command prefix (@agent, /claude, etc.)
- Extract desired commands and their templates

### Step 2: Learn from Static Webhooks
Read and understand patterns from:
- `api/webhooks/github.py` - signature verification, immediate response, command matching
- `api/webhooks/jira.py` - Jira-specific payload handling
- `api/webhooks/slack.py` - Slack challenge/response, message formatting
- `api/webhooks/sentry.py` - Error event processing
- `core/webhook_configs.py` - WebhookConfig and WebhookCommand structure

### Step 3: Create Skill with webhook_config
Create skill at `.claude/skills/{webhook-name}/SKILL.md` with frontmatter:

```yaml
---
name: {webhook-name}
description: {description}
webhook_config:
  provider: {provider}
  endpoint: /webhooks/{provider}/{webhook-id}
  commands:
    - name: {command-name}
      trigger: {event-type}
      template: |
        {prompt-template}
      action: create_task
      agent: planning
---
```

### Step 4: Create Companion Agent (Optional)
If webhook requires specialized handling, create agent at `.claude/agents/{webhook-name}.md`

### Step 5: Register via API
Call `POST /api/webhooks` to register in database

## Output Format

Always provide:
1. Created skill path
2. Webhook endpoint URL
3. Required environment variables (secrets)
4. Test curl command

## Example

User: "Create a webhook for GitHub that reviews PRs when @bot is mentioned"

Result:
- Skill: `.claude/skills/github-pr-reviewer/SKILL.md`
- Endpoint: `/webhooks/github/pr-reviewer`
- Secret env var: `GITHUB_PR_REVIEWER_SECRET`
```

#### Modify: `core/subagent_config.py`

Add webhook-creator to default subagents list.

#### Modify: `.claude/CLAUDE.md`

Add webhook-creator to Available Sub-Agents section.

---

### Phase 3: REFACTOR

- Ensure agent markdown follows same structure as other agents
- Verify frontmatter is valid YAML
- Check skill reference is correct

---

### Phase 4: ACCEPTANCE CRITERIA

```gherkin
Feature: Webhook Creator Agent

Scenario: Agent file exists with correct structure
  Given the webhook-creator agent
  When I read .claude/agents/webhook-creator.md
  Then it has valid frontmatter with name, description, tools, model
  And it references webhook-management skill
  And it documents learning from static webhooks

Scenario: Agent is registered in system
  Given the system starts
  When subagent config is loaded
  Then webhook-creator is in the list

Scenario: CLAUDE.md documents the agent
  Given .claude/CLAUDE.md
  When I read the file
  Then webhook-creator is listed as available sub-agent
```

---

## Gap 2: Skill webhook_config Synchronization

### Objective
Parse skill frontmatter on upload/edit and sync `webhook_config` to database.

### Files to Create
```
core/skill_webhook_sync.py
tests/unit/test_skill_webhook_sync.py
tests/integration/test_skill_webhook_sync_api.py
```

### Files to Modify
```
api/registry.py                      # Add sync calls to upload/edit/delete
```

---

### Phase 1: RED - Write Failing Tests First

#### Test File: `tests/unit/test_skill_webhook_sync.py`

```python
import pytest
from core.skill_webhook_sync import parse_skill_frontmatter, extract_webhook_config

class TestParseFrontmatter:
    def test_parse_valid_frontmatter(self):
        content = """---
name: test-skill
description: A test skill
webhook_config:
  provider: github
  endpoint: /webhooks/github/test
  commands:
    - name: analyze
      trigger: issues.opened
      template: "Analyze {{issue.title}}"
      action: create_task
      agent: planning
---

# Skill Content
"""
        frontmatter = parse_skill_frontmatter(content)

        assert frontmatter is not None
        assert frontmatter["name"] == "test-skill"
        assert "webhook_config" in frontmatter

    def test_parse_no_frontmatter(self):
        content = "# Just a title\n\nSome content"
        frontmatter = parse_skill_frontmatter(content)

        assert frontmatter is None

    def test_parse_frontmatter_without_webhook_config(self):
        content = """---
name: simple-skill
description: No webhook
---

Content here
"""
        frontmatter = parse_skill_frontmatter(content)

        assert frontmatter is not None
        assert "webhook_config" not in frontmatter


class TestExtractWebhookConfig:
    def test_extract_valid_webhook_config(self):
        frontmatter = {
            "name": "github-analyzer",
            "webhook_config": {
                "provider": "github",
                "endpoint": "/webhooks/github/analyzer",
                "commands": [
                    {
                        "name": "analyze",
                        "trigger": "issues.opened",
                        "template": "Analyze this",
                        "action": "create_task",
                        "agent": "planning"
                    }
                ]
            }
        }

        config = extract_webhook_config(frontmatter)

        assert config is not None
        assert config.provider == "github"
        assert len(config.commands) == 1

    def test_extract_no_webhook_config(self):
        frontmatter = {"name": "simple-skill"}

        config = extract_webhook_config(frontmatter)

        assert config is None

    def test_extract_invalid_webhook_config(self):
        frontmatter = {
            "name": "bad-skill",
            "webhook_config": {
                "provider": "github"
                # Missing required fields
            }
        }

        config = extract_webhook_config(frontmatter)

        assert config is None  # Should return None for invalid config
```

#### Test File: `tests/integration/test_skill_webhook_sync_api.py`

```python
import pytest
from httpx import AsyncClient
from io import BytesIO

@pytest.mark.asyncio
class TestSkillWebhookSyncAPI:
    async def test_upload_skill_with_webhook_config_creates_webhook(
        self,
        async_client: AsyncClient,
        db_session
    ):
        skill_content = """---
name: test-webhook-skill
description: Skill with webhook
webhook_config:
  provider: custom
  endpoint: /webhooks/custom/test-sync
  secret_env_var: TEST_WEBHOOK_SECRET
  commands:
    - name: process
      trigger: event.created
      template: "Process {{event.data}}"
      action: create_task
      agent: planning
---

# Test Webhook Skill
"""
        files = [
            ("files", ("SKILL.md", BytesIO(skill_content.encode()), "text/markdown"))
        ]

        response = await async_client.post(
            "/api/registry/skills/upload",
            data={"name": "test-webhook-skill"},
            files=files
        )

        assert response.status_code == 200

        # Verify webhook was created in database
        from sqlalchemy import select
        from core.database.models import WebhookConfigDB

        result = await db_session.execute(
            select(WebhookConfigDB).where(
                WebhookConfigDB.name == "test-webhook-skill"
            )
        )
        webhook = result.scalar_one_or_none()

        assert webhook is not None
        assert webhook.provider == "custom"

    async def test_delete_skill_with_webhook_config_deletes_webhook(
        self,
        async_client: AsyncClient,
        db_session
    ):
        # First create the skill
        # ... (setup code)

        response = await async_client.delete(
            "/api/registry/skills/test-webhook-skill"
        )

        assert response.status_code == 200

        # Verify webhook was deleted
        from sqlalchemy import select
        from core.database.models import WebhookConfigDB

        result = await db_session.execute(
            select(WebhookConfigDB).where(
                WebhookConfigDB.name == "test-webhook-skill"
            )
        )
        webhook = result.scalar_one_or_none()

        assert webhook is None
```

---

### Phase 2: GREEN - Implement Minimum Code

#### Create: `core/skill_webhook_sync.py`

```python
"""Skill to webhook configuration synchronization."""

import re
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError
import yaml
import structlog

logger = structlog.get_logger()


class SkillWebhookCommand(BaseModel):
    name: str
    trigger: str
    template: str
    action: str = "create_task"
    agent: str = "planning"
    conditions: Optional[Dict[str, Any]] = None
    priority: int = 0


class SkillWebhookConfig(BaseModel):
    provider: str
    endpoint: str
    secret_env_var: Optional[str] = None
    command_prefix: str = "@agent"
    commands: list[SkillWebhookCommand]


def parse_skill_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        logger.warning("invalid_frontmatter_yaml", error=str(e))
        return None


def extract_webhook_config(frontmatter: Dict[str, Any]) -> Optional[SkillWebhookConfig]:
    if not frontmatter or "webhook_config" not in frontmatter:
        return None

    try:
        return SkillWebhookConfig(**frontmatter["webhook_config"])
    except ValidationError as e:
        logger.warning("invalid_webhook_config", error=str(e))
        return None


async def sync_skill_webhook_to_db(
    skill_name: str,
    skill_content: str,
    db_session,
    created_by: str = "skill-upload"
) -> Optional[str]:
    from core.database.models import WebhookConfigDB, WebhookCommandDB
    from sqlalchemy import select, delete

    frontmatter = parse_skill_frontmatter(skill_content)
    if not frontmatter:
        return None

    webhook_config = extract_webhook_config(frontmatter)
    if not webhook_config:
        return None

    webhook_id = f"skill-{skill_name}"

    existing = await db_session.execute(
        select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
    )
    existing_webhook = existing.scalar_one_or_none()

    if existing_webhook:
        await db_session.execute(
            delete(WebhookCommandDB).where(WebhookCommandDB.webhook_id == webhook_id)
        )
        await db_session.delete(existing_webhook)
        await db_session.flush()

    webhook_db = WebhookConfigDB(
        webhook_id=webhook_id,
        name=skill_name,
        provider=webhook_config.provider,
        endpoint=webhook_config.endpoint,
        secret=None,
        enabled=True,
        config_json=json.dumps({
            "command_prefix": webhook_config.command_prefix,
            "secret_env_var": webhook_config.secret_env_var,
            "source": "skill"
        }),
        created_at=datetime.now(timezone.utc),
        created_by=created_by
    )
    db_session.add(webhook_db)

    for cmd in webhook_config.commands:
        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        command_db = WebhookCommandDB(
            command_id=command_id,
            webhook_id=webhook_id,
            trigger=cmd.trigger,
            action=cmd.action,
            agent=cmd.agent,
            template=cmd.template,
            conditions_json=json.dumps(cmd.conditions) if cmd.conditions else None,
            priority=cmd.priority
        )
        db_session.add(command_db)

    logger.info(
        "skill_webhook_synced",
        skill_name=skill_name,
        webhook_id=webhook_id,
        commands_count=len(webhook_config.commands)
    )

    return webhook_id


async def delete_skill_webhook_from_db(skill_name: str, db_session) -> bool:
    from core.database.models import WebhookConfigDB
    from sqlalchemy import select

    webhook_id = f"skill-{skill_name}"

    result = await db_session.execute(
        select(WebhookConfigDB).where(WebhookConfigDB.webhook_id == webhook_id)
    )
    webhook = result.scalar_one_or_none()

    if webhook:
        await db_session.delete(webhook)
        logger.info("skill_webhook_deleted", skill_name=skill_name, webhook_id=webhook_id)
        return True

    return False
```

#### Modify: `api/registry.py`

Add sync calls to `upload_skill`, `update_asset_content`, and `delete_skill`:

```python
# In upload_skill function, after saving files:
from core.skill_webhook_sync import sync_skill_webhook_to_db

skill_md_path = skill_dir / "SKILL.md"
if skill_md_path.exists():
    skill_content = skill_md_path.read_text()
    async with async_session_factory() as db_session:
        webhook_id = await sync_skill_webhook_to_db(name, skill_content, db_session)
        await db_session.commit()
        if webhook_id:
            logger.info("skill_webhook_created", skill_name=name, webhook_id=webhook_id)

# In delete_skill function, before deleting:
from core.skill_webhook_sync import delete_skill_webhook_from_db

async with async_session_factory() as db_session:
    await delete_skill_webhook_from_db(skill_name, db_session)
    await db_session.commit()
```

---

### Phase 3: ACCEPTANCE CRITERIA

```gherkin
Feature: Skill webhook_config Synchronization

Scenario: Upload skill with webhook_config creates webhook
  Given a SKILL.md with valid webhook_config in frontmatter
  When I upload via POST /api/registry/skills/upload
  Then webhook is created in webhook_configs table
  And webhook commands are created in webhook_commands table

Scenario: Upload skill without webhook_config does not create webhook
  Given a SKILL.md without webhook_config
  When I upload via POST /api/registry/skills/upload
  Then no webhook is created

Scenario: Delete skill removes associated webhook
  Given a skill with webhook_config exists
  When I delete via DELETE /api/registry/skills/{name}
  Then webhook is removed from database
  And webhook commands are removed

Scenario: Update skill updates webhook
  Given a skill with webhook_config exists
  When I update SKILL.md content with new commands
  Then webhook commands are updated in database
```

---

## Gap 3: Dynamic Webhook Signature Verification

### Objective
Implement signature verification for Jira and Slack in dynamic webhook receiver.

### Files to Modify
```
api/webhooks_dynamic.py              # Add verification implementations
```

### Files to Create
```
tests/unit/test_dynamic_webhook_signatures.py
```

---

### Phase 1: RED - Write Failing Tests First

#### Test File: `tests/unit/test_dynamic_webhook_signatures.py`

```python
import pytest
import hmac
import hashlib
import time
from unittest.mock import MagicMock, AsyncMock
from fastapi import HTTPException

class TestSlackSignatureVerification:
    def test_valid_slack_signature(self):
        from api.webhooks_dynamic import verify_slack_signature

        secret = "test_slack_secret"
        timestamp = str(int(time.time()))
        body = b'{"type":"event_callback","event":{"type":"message"}}'

        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        expected_sig = "v0=" + hmac.new(
            secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-Slack-Signature": expected_sig,
            "X-Slack-Request-Timestamp": timestamp
        }

        result = verify_slack_signature(body, headers, secret)
        assert result is True

    def test_invalid_slack_signature(self):
        from api.webhooks_dynamic import verify_slack_signature

        secret = "test_slack_secret"
        timestamp = str(int(time.time()))
        body = b'{"type":"event_callback"}'

        headers = {
            "X-Slack-Signature": "v0=invalid_signature",
            "X-Slack-Request-Timestamp": timestamp
        }

        with pytest.raises(HTTPException) as exc_info:
            verify_slack_signature(body, headers, secret)

        assert exc_info.value.status_code == 401

    def test_slack_timestamp_too_old(self):
        from api.webhooks_dynamic import verify_slack_signature

        secret = "test_slack_secret"
        timestamp = str(int(time.time()) - 600)  # 10 minutes old
        body = b'{"type":"event_callback"}'

        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        expected_sig = "v0=" + hmac.new(
            secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-Slack-Signature": expected_sig,
            "X-Slack-Request-Timestamp": timestamp
        }

        with pytest.raises(HTTPException) as exc_info:
            verify_slack_signature(body, headers, secret)

        assert exc_info.value.status_code == 401


class TestJiraSignatureVerification:
    def test_valid_jira_hmac_signature(self):
        from api.webhooks_dynamic import verify_jira_signature

        secret = "test_jira_secret"
        body = b'{"webhookEvent":"jira:issue_created"}'

        expected_sig = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        headers = {"X-Hub-Signature": f"sha256={expected_sig}"}

        result = verify_jira_signature(body, headers, secret)
        assert result is True

    def test_invalid_jira_signature(self):
        from api.webhooks_dynamic import verify_jira_signature

        secret = "test_jira_secret"
        body = b'{"webhookEvent":"jira:issue_created"}'

        headers = {"X-Hub-Signature": "sha256=invalid"}

        with pytest.raises(HTTPException) as exc_info:
            verify_jira_signature(body, headers, secret)

        assert exc_info.value.status_code == 401
```

---

### Phase 2: GREEN - Implement Minimum Code

#### Modify: `api/webhooks_dynamic.py`

Replace placeholder `pass` statements:

```python
import time

def verify_slack_signature(body: bytes, headers: dict, secret: str) -> bool:
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")

    if not timestamp or not signature:
        raise HTTPException(status_code=401, detail="Missing Slack signature headers")

    try:
        request_timestamp = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp format")

    if abs(time.time() - request_timestamp) > 300:
        raise HTTPException(status_code=401, detail="Request timestamp too old")

    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected_signature = "v0=" + hmac.new(
        secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    return True


def verify_jira_signature(body: bytes, headers: dict, secret: str) -> bool:
    signature_header = headers.get("X-Hub-Signature", "")

    if not signature_header:
        signature_header = headers.get("X-Atlassian-Webhook-Signature", "")

    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing Jira signature header")

    if signature_header.startswith("sha256="):
        provided_sig = signature_header[7:]
        expected_sig = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
    else:
        provided_sig = signature_header
        expected_sig = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise HTTPException(status_code=401, detail="Invalid Jira signature")

    return True


async def verify_webhook_signature(
    request: Request,
    webhook: WebhookConfigDB,
    provider: str
):
    if not webhook.secret:
        return

    body = await request.body()
    headers = dict(request.headers)

    if provider == "github":
        signature_header = headers.get("x-hub-signature-256", "")
        if not signature_header:
            raise HTTPException(status_code=401, detail="Missing signature header")

        expected = hmac.new(
            webhook.secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(f"sha256={expected}", signature_header):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    elif provider == "jira":
        verify_jira_signature(body, headers, webhook.secret)

    elif provider == "slack":
        verify_slack_signature(body, headers, webhook.secret)

    elif provider == "sentry":
        signature_header = headers.get("sentry-hook-signature", "")
        if signature_header:
            expected = hmac.new(
                webhook.secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, signature_header):
                raise HTTPException(status_code=401, detail="Invalid Sentry signature")

    logger.debug("webhook_signature_verified", webhook_id=webhook.webhook_id, provider=provider)
```

---

### Phase 3: ACCEPTANCE CRITERIA

```gherkin
Feature: Dynamic Webhook Signature Verification

Scenario: Valid Slack signature passes verification
  Given a Slack webhook with secret configured
  When request arrives with valid X-Slack-Signature and X-Slack-Request-Timestamp
  Then verification passes
  And request is processed

Scenario: Invalid Slack signature fails verification
  Given a Slack webhook with secret configured
  When request arrives with invalid signature
  Then HTTP 401 is returned
  And "Invalid Slack signature" message is returned

Scenario: Slack timestamp too old fails verification
  Given a Slack webhook with secret configured
  When request arrives with timestamp older than 5 minutes
  Then HTTP 401 is returned

Scenario: Valid Jira signature passes verification
  Given a Jira webhook with secret configured
  When request arrives with valid X-Hub-Signature
  Then verification passes

Scenario: Invalid Jira signature fails verification
  Given a Jira webhook with secret configured
  When request arrives with invalid signature
  Then HTTP 401 is returned
```

---

## Gap 4: Response to Webhook Source

### Objective
Implement actual comment posting for GitHub, Jira, and Slack in `action_comment`.

### Files to Modify
```
core/webhook_engine.py               # Implement action_comment
```

### Files to Create
```
core/jira_client.py                  # Jira REST API client
core/slack_client.py                 # Slack API client
tests/unit/test_webhook_response.py
tests/integration/test_webhook_response_flow.py
```

---

### Phase 1: RED - Write Failing Tests First

#### Test File: `tests/unit/test_webhook_response.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestActionComment:
    @pytest.mark.asyncio
    async def test_github_comment_posts_to_issue(self):
        from core.webhook_engine import action_comment

        payload = {
            "provider": "github",
            "repository": {"owner": {"login": "owner"}, "name": "repo"},
            "issue": {"number": 123}
        }
        message = "Task completed successfully"

        with patch("core.webhook_engine.github_client") as mock_client:
            mock_client.post_issue_comment = AsyncMock(return_value=True)

            result = await action_comment(payload, message)

            assert result["status"] == "sent"
            mock_client.post_issue_comment.assert_called_once_with(
                "owner", "repo", 123, message
            )

    @pytest.mark.asyncio
    async def test_jira_comment_posts_to_ticket(self):
        from core.webhook_engine import action_comment

        payload = {
            "provider": "jira",
            "issue": {"key": "PROJ-123"}
        }
        message = "Analysis complete"

        with patch("core.webhook_engine.jira_client") as mock_client:
            mock_client.add_comment = AsyncMock(return_value=True)

            result = await action_comment(payload, message)

            assert result["status"] == "sent"
            mock_client.add_comment.assert_called_once_with("PROJ-123", message)

    @pytest.mark.asyncio
    async def test_slack_comment_posts_to_channel(self):
        from core.webhook_engine import action_comment

        payload = {
            "provider": "slack",
            "event": {"channel": "C123456", "ts": "1234567890.123456"}
        }
        message = "Here are the results"

        with patch("core.webhook_engine.slack_client") as mock_client:
            mock_client.post_message = AsyncMock(return_value=True)

            result = await action_comment(payload, message)

            assert result["status"] == "sent"
            mock_client.post_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_error(self):
        from core.webhook_engine import action_comment

        payload = {"provider": "unknown"}
        message = "Test"

        result = await action_comment(payload, message)

        assert result["status"] == "error"
        assert "unsupported provider" in result["error"].lower()
```

#### Test File: `tests/unit/test_jira_client.py`

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestJiraClient:
    @pytest.mark.asyncio
    async def test_add_comment_success(self):
        from core.jira_client import JiraClient

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=201))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = JiraClient(
                base_url="https://example.atlassian.net",
                email="test@example.com",
                api_token="token123"
            )

            result = await client.add_comment("PROJ-123", "Test comment")

            assert result is True

    @pytest.mark.asyncio
    async def test_add_comment_failure(self):
        from core.jira_client import JiraClient

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=401))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = JiraClient(
                base_url="https://example.atlassian.net",
                email="test@example.com",
                api_token="token123"
            )

            result = await client.add_comment("PROJ-123", "Test comment")

            assert result is False
```

---

### Phase 2: GREEN - Implement Minimum Code

#### Create: `core/jira_client.py`

```python
"""Jira REST API client for posting comments."""

import os
import base64
import httpx
import structlog

logger = structlog.get_logger()


class JiraClient:
    def __init__(
        self,
        base_url: str = None,
        email: str = None,
        api_token: str = None
    ):
        self.base_url = base_url or os.getenv("JIRA_BASE_URL")
        self.email = email or os.getenv("JIRA_EMAIL")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN")

    def _get_auth_header(self) -> dict:
        if not self.email or not self.api_token:
            return {}

        credentials = base64.b64encode(
            f"{self.email}:{self.api_token}".encode()
        ).decode()

        return {"Authorization": f"Basic {credentials}"}

    async def add_comment(self, issue_key: str, comment: str) -> bool:
        if not self.base_url:
            logger.warning("jira_base_url_not_configured")
            return False

        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"

        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": comment}
                        ]
                    }
                ]
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=body,
                    headers={
                        **self._get_auth_header(),
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )

                if response.status_code in (200, 201):
                    logger.info("jira_comment_posted", issue_key=issue_key)
                    return True

                logger.error(
                    "jira_comment_failed",
                    issue_key=issue_key,
                    status_code=response.status_code,
                    response=response.text[:200]
                )
                return False

        except Exception as e:
            logger.error("jira_comment_error", issue_key=issue_key, error=str(e))
            return False


jira_client = JiraClient()
```

#### Create: `core/slack_client.py`

```python
"""Slack API client for posting messages."""

import os
import httpx
import structlog

logger = structlog.get_logger()


class SlackClient:
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")

    async def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: str = None
    ) -> bool:
        if not self.bot_token:
            logger.warning("slack_bot_token_not_configured")
            return False

        url = "https://slack.com/api/chat.postMessage"

        body = {
            "channel": channel,
            "text": text
        }

        if thread_ts:
            body["thread_ts"] = thread_ts

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {self.bot_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )

                result = response.json()

                if result.get("ok"):
                    logger.info("slack_message_posted", channel=channel)
                    return True

                logger.error(
                    "slack_message_failed",
                    channel=channel,
                    error=result.get("error")
                )
                return False

        except Exception as e:
            logger.error("slack_message_error", channel=channel, error=str(e))
            return False


slack_client = SlackClient()
```

#### Modify: `core/webhook_engine.py`

Replace placeholder `action_comment`:

```python
from core.github_client import github_client
from core.jira_client import jira_client
from core.slack_client import slack_client


async def action_comment(payload: dict, message: str) -> dict:
    provider = payload.get("provider", "unknown")

    try:
        if provider == "github":
            repo = payload.get("repository", {})
            owner = repo.get("owner", {}).get("login")
            repo_name = repo.get("name")

            issue = payload.get("issue") or payload.get("pull_request")
            issue_number = issue.get("number") if issue else None

            if not all([owner, repo_name, issue_number]):
                return {"action": "comment", "status": "error", "error": "Missing GitHub context"}

            success = await github_client.post_issue_comment(
                owner, repo_name, issue_number, message
            )

            return {
                "action": "comment",
                "status": "sent" if success else "error",
                "provider": provider
            }

        elif provider == "jira":
            issue = payload.get("issue", {})
            issue_key = issue.get("key")

            if not issue_key:
                return {"action": "comment", "status": "error", "error": "Missing Jira issue key"}

            success = await jira_client.add_comment(issue_key, message)

            return {
                "action": "comment",
                "status": "sent" if success else "error",
                "provider": provider
            }

        elif provider == "slack":
            event = payload.get("event", {})
            channel = event.get("channel")
            thread_ts = event.get("ts") or event.get("thread_ts")

            if not channel:
                return {"action": "comment", "status": "error", "error": "Missing Slack channel"}

            success = await slack_client.post_message(channel, message, thread_ts)

            return {
                "action": "comment",
                "status": "sent" if success else "error",
                "provider": provider
            }

        else:
            return {
                "action": "comment",
                "status": "error",
                "error": f"Unsupported provider: {provider}"
            }

    except Exception as e:
        logger.error("action_comment_error", provider=provider, error=str(e))
        return {"action": "comment", "status": "error", "error": str(e)}
```

---

### Phase 3: ACCEPTANCE CRITERIA

```gherkin
Feature: Response to Webhook Source

Scenario: GitHub issue receives comment after task completion
  Given a task from GitHub webhook completes successfully
  When action_comment is called with GitHub payload
  Then comment is posted to the GitHub issue
  And result status is "sent"

Scenario: Jira ticket receives comment after task completion
  Given a task from Jira webhook completes successfully
  When action_comment is called with Jira payload
  Then comment is posted to the Jira ticket
  And result status is "sent"

Scenario: Slack channel receives message after task completion
  Given a task from Slack webhook completes successfully
  When action_comment is called with Slack payload
  Then message is posted to the Slack channel/thread
  And result status is "sent"

Scenario: Missing credentials returns error
  Given JIRA_API_TOKEN is not set
  When action_comment is called with Jira payload
  Then result status is "error"
  And error message indicates missing credentials
```

---

## Gap 5: Static + Dynamic Command Merging

### Objective
Merge static webhook commands with dynamic commands from database.

### Files to Modify
```
api/webhooks/github.py               # Use merged commands
api/webhooks/jira.py                 # Use merged commands
api/webhooks/slack.py                # Use merged commands
api/webhooks/sentry.py               # Use merged commands
```

### Files to Create
```
core/command_merger.py               # Command merging logic
tests/unit/test_command_merger.py
tests/integration/test_command_merging.py
```

---

### Phase 1: RED - Write Failing Tests First

#### Test File: `tests/unit/test_command_merger.py`

```python
import pytest
from shared.machine_models import WebhookCommand

class TestCommandMerger:
    def test_merge_no_dynamic_commands(self):
        from core.command_merger import merge_commands

        static_commands = [
            WebhookCommand(
                name="analyze",
                aliases=["analysis"],
                description="Analyze issue",
                target_agent="planning",
                prompt_template="Analyze {{issue.title}}"
            )
        ]
        dynamic_commands = []

        merged = merge_commands(static_commands, dynamic_commands)

        assert len(merged) == 1
        assert merged[0].name == "analyze"

    def test_merge_adds_dynamic_commands(self):
        from core.command_merger import merge_commands

        static_commands = [
            WebhookCommand(
                name="analyze",
                aliases=[],
                description="Analyze",
                target_agent="planning",
                prompt_template="Analyze"
            )
        ]
        dynamic_commands = [
            {"name": "deploy", "target_agent": "executor", "template": "Deploy"}
        ]

        merged = merge_commands(static_commands, dynamic_commands)

        assert len(merged) == 2
        command_names = [c.name for c in merged]
        assert "analyze" in command_names
        assert "deploy" in command_names

    def test_dynamic_overrides_static(self):
        from core.command_merger import merge_commands

        static_commands = [
            WebhookCommand(
                name="analyze",
                aliases=[],
                description="Static analyze",
                target_agent="planning",
                prompt_template="Static template"
            )
        ]
        dynamic_commands = [
            {
                "name": "analyze",
                "target_agent": "executor",
                "template": "Dynamic template"
            }
        ]

        merged = merge_commands(static_commands, dynamic_commands)

        assert len(merged) == 1
        assert merged[0].target_agent == "executor"
        assert "Dynamic" in merged[0].prompt_template

    def test_merge_preserves_static_is_builtin(self):
        from core.command_merger import merge_commands

        static_commands = [
            WebhookCommand(
                name="analyze",
                aliases=[],
                description="Analyze",
                target_agent="planning",
                prompt_template="Template"
            )
        ]
        dynamic_commands = []

        merged = merge_commands(static_commands, dynamic_commands, mark_builtin=True)

        assert merged[0]._is_builtin is True
```

---

### Phase 2: GREEN - Implement Minimum Code

#### Create: `core/command_merger.py`

```python
"""Merge static and dynamic webhook commands."""

from typing import List, Dict, Any
from shared.machine_models import WebhookCommand
from core.database.models import WebhookCommandDB
import structlog

logger = structlog.get_logger()


def db_command_to_webhook_command(db_cmd: WebhookCommandDB) -> WebhookCommand:
    return WebhookCommand(
        name=db_cmd.trigger.split(".")[-1] if "." in db_cmd.trigger else db_cmd.trigger,
        aliases=[],
        description=f"Dynamic command for {db_cmd.trigger}",
        target_agent=db_cmd.agent or "planning",
        prompt_template=db_cmd.template,
        requires_approval=False
    )


def dict_to_webhook_command(cmd_dict: Dict[str, Any]) -> WebhookCommand:
    return WebhookCommand(
        name=cmd_dict.get("name", "unknown"),
        aliases=cmd_dict.get("aliases", []),
        description=cmd_dict.get("description", ""),
        target_agent=cmd_dict.get("target_agent", cmd_dict.get("agent", "planning")),
        prompt_template=cmd_dict.get("template", cmd_dict.get("prompt_template", "")),
        requires_approval=cmd_dict.get("requires_approval", False)
    )


def merge_commands(
    static_commands: List[WebhookCommand],
    dynamic_commands: List[Dict[str, Any] | WebhookCommandDB],
    mark_builtin: bool = False
) -> List[WebhookCommand]:
    command_map = {}

    for cmd in static_commands:
        cmd_copy = cmd.model_copy()
        if mark_builtin:
            object.__setattr__(cmd_copy, "_is_builtin", True)
        command_map[cmd.name.lower()] = cmd_copy

    for dyn_cmd in dynamic_commands:
        if isinstance(dyn_cmd, WebhookCommandDB):
            webhook_cmd = db_command_to_webhook_command(dyn_cmd)
        elif isinstance(dyn_cmd, dict):
            webhook_cmd = dict_to_webhook_command(dyn_cmd)
        else:
            continue

        if mark_builtin:
            object.__setattr__(webhook_cmd, "_is_builtin", False)

        command_map[webhook_cmd.name.lower()] = webhook_cmd

    merged = list(command_map.values())

    logger.debug(
        "commands_merged",
        static_count=len(static_commands),
        dynamic_count=len(dynamic_commands),
        merged_count=len(merged)
    )

    return merged


async def get_merged_commands_for_provider(
    provider: str,
    static_config,
    db_session
) -> List[WebhookCommand]:
    from sqlalchemy import select
    from core.database.models import WebhookConfigDB, WebhookCommandDB

    result = await db_session.execute(
        select(WebhookConfigDB).where(WebhookConfigDB.provider == provider)
    )
    dynamic_webhooks = result.scalars().all()

    dynamic_commands = []
    for webhook in dynamic_webhooks:
        cmd_result = await db_session.execute(
            select(WebhookCommandDB).where(
                WebhookCommandDB.webhook_id == webhook.webhook_id
            )
        )
        dynamic_commands.extend(cmd_result.scalars().all())

    return merge_commands(
        static_config.commands,
        dynamic_commands,
        mark_builtin=True
    )
```

#### Modify: `api/webhooks/github.py`

Update `match_github_command` to use merged commands:

```python
from core.command_merger import get_merged_commands_for_provider
from core.database import async_session_factory

async def match_github_command_merged(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    async with async_session_factory() as db:
        merged_commands = await get_merged_commands_for_provider(
            "github",
            GITHUB_WEBHOOK,
            db
        )

    text = ""
    if event_type.startswith("issue_comment"):
        text = payload.get("comment", {}).get("body", "")
    elif event_type.startswith("issues"):
        text = payload.get("issue", {}).get("body", "") or payload.get("issue", {}).get("title", "")
    elif event_type.startswith("pull_request"):
        text = payload.get("pull_request", {}).get("body", "") or payload.get("pull_request", {}).get("title", "")

    if not text:
        for cmd in merged_commands:
            if cmd.name == GITHUB_WEBHOOK.default_command:
                return cmd
        return merged_commands[0] if merged_commands else None

    prefix = GITHUB_WEBHOOK.command_prefix.lower()
    text_lower = text.lower()

    if prefix not in text_lower:
        for cmd in merged_commands:
            if cmd.name == GITHUB_WEBHOOK.default_command:
                return cmd
        return merged_commands[0] if merged_commands else None

    for cmd in merged_commands:
        if cmd.name.lower() in text_lower:
            return cmd
        for alias in cmd.aliases:
            if alias.lower() in text_lower:
                return cmd

    for cmd in merged_commands:
        if cmd.name == GITHUB_WEBHOOK.default_command:
            return cmd

    return merged_commands[0] if merged_commands else None
```

---

### Phase 3: ACCEPTANCE CRITERIA

```gherkin
Feature: Static + Dynamic Command Merging

Scenario: Static commands work when no dynamic commands exist
  Given GITHUB_WEBHOOK has commands [analyze, plan, fix, review]
  And no dynamic commands in database for github
  When webhook arrives with "@agent analyze"
  Then "analyze" command is matched

Scenario: Dynamic command is added to static commands
  Given GITHUB_WEBHOOK has commands [analyze, plan]
  And dynamic command "deploy" exists in database
  When webhook arrives with "@agent deploy"
  Then "deploy" command is matched

Scenario: Dynamic command overrides static command
  Given GITHUB_WEBHOOK has "analyze" command with planning agent
  And dynamic "analyze" command exists with executor agent
  When webhook arrives with "@agent analyze"
  Then executor agent handles the task (dynamic takes precedence)

Scenario: Built-in commands marked appropriately
  Given merged commands
  When checking command metadata
  Then static commands have _is_builtin=True
  And dynamic commands have _is_builtin=False
```

---

## Code Cleanup: Remove Redundant Comments

### Objective
Remove comments that duplicate what the code already expresses. Code should be self-explanatory.

### Cleanup Rules

**REMOVE these patterns:**
1. Numbered step comments: `# 1. Do X`, `# 2. Do Y`
2. Emoji-prefixed obvious comments: `# ✅ Update Redis`
3. Comments restating the next line: `# Get task` followed by `get_task()`
4. Section header comments for obvious functions: `# ✅ Verification function (GitHub webhook ONLY)`

**KEEP these patterns:**
1. Comments explaining WHY, not WHAT
2. Security-related explanations
3. Non-obvious algorithm explanations
4. Business logic decisions

---

### File: `api/webhooks/github.py`

**Remove these comments (lines):**
```
Line 32:  # ✅ Verification function (GitHub webhook ONLY)
Line 62:  # ✅ Immediate response function (GitHub webhook ONLY)
Line 145: # ✅ Command matching function (GitHub webhook ONLY)
Line 192: # ✅ Task creation function (GitHub webhook ONLY)
Line 256: # ✅ Route handler (GitHub webhook - handles all GitHub events)
Line 272: # 1. Read body
Line 279: # 2. Verify signature
Line 288: # 3. Parse payload
Line 306: # 4. Extract event type (issues.opened, pull_request.opened, issue_comment.created, etc.)
Line 314: # 5. Match command based on event type and payload
Line 324: # 6. Send immediate response
Line 332: # 7. Create task
Line 340: # 8. Log event
```

**Keep:** Docstrings that provide API documentation.

---

### File: `api/webhooks/jira.py`

**Remove these comments (lines):**
```
Line 33:  # ✅ Verification function (Jira webhook ONLY)
Line 59:  # ✅ Helper function: Check if assignee changed to AI Agent
Line 94:  # ✅ Helper function: Generate immediate response message
Line 107: # ✅ Immediate response function (Jira webhook ONLY)
Line 149: # ✅ Command matching function (Jira webhook ONLY)
Line 200: # ✅ Task creation function (Jira webhook ONLY)
Line 357: # ✅ Route handler (Jira webhook - handles all Jira events)
Line 372: # 1. Read body
Line 379: # 2. Verify signature
Line 388: # 3. Parse payload
Line 402: # 4. Extract event type
Line 407: # 5. Match command based on event type and payload
Line 424: # 6. Send immediate response
Line 432: # 7. Create task
Line 440: # 8. Log event
```

---

### File: `api/webhooks/slack.py`

**Remove these comments (lines):**
```
Line 31:  # ✅ Verification function (Slack webhook ONLY)
Line 63:  # ✅ Immediate response function (Slack webhook ONLY)
Line 108: # ✅ Command matching function (Slack webhook ONLY)
Line 149: # ✅ Task creation function (Slack webhook ONLY)
Line 213: # ✅ Route handler (Slack webhook - handles all Slack events)
Line 228: # 1. Read body
Line 235: # 2. Verify signature
Line 244: # 3. Parse payload
Line 255: # 4. Handle Slack URL verification
Line 263: # 5. Extract event type
Line 268: # 6. Match command based on event type and payload
Line 278: # 7. Send immediate response
Line 286: # 8. Create task
Line 294: # 9. Log event
```

---

### File: `api/webhooks/sentry.py`

**Remove these comments (lines):**
```
Line 30:  # ✅ Verification function (Sentry webhook ONLY)
Line 56:  # ✅ Immediate response function (Sentry webhook ONLY)
Line 84:  # ✅ Command matching function (Sentry webhook ONLY)
Line 106: # ✅ Task creation function (Sentry webhook ONLY)
Line 170: # ✅ Route handler (Sentry webhook - handles all Sentry events)
Line 182: # 1. Read body
Line 185: # 2. Verify signature
Line 188: # 3. Parse payload
Line 192: # 4. Extract event type
Line 198: # 5. Match command based on event type and payload
Line 203: # 6. Send immediate response
Line 206: # 7. Create task
Line 209: # 8. Log event
```

---

### File: `api/webhooks_dynamic.py`

**Remove these comments (lines):**
```
Line 91:  # 1. Load webhook config from database
Line 104: # 2. Check if webhook is enabled
Line 109: # 3. Verify signature if secret configured
Line 113: # 4. Parse payload
Line 126: # 5. Match event to commands
Line 154: # 6. Execute actions
Line 165: # 7. Log event
```

---

### File: `workers/task_worker.py`

**Remove these comments (lines):**
```
Line 63:  # ✅ Launch task concurrently (don't await)
Line 142: # ✅ Update Redis first (fast ~1ms) to minimize inconsistency window
Line 227: # ✅ Update Redis first (fast)
Line 280: # ✅ Update Redis first (fast)
Line 401: # ✅ Update Redis first (fast)
```

**Keep:** Comments explaining concurrency patterns and zombie process handling.

---

### File: `api/credentials.py`

**Remove these comments (lines):**
```
Line 65:  # 1. Check if Claude CLI is available
Line 81:  # 2. Check if credentials file exists
Line 113: # 3. Handle CLI-only state or Missing state
```

---

### File: `core/cli_runner.py`

**Keep these comments (they explain WHY):**
```
Line 221: await process.wait()  # ✅ CRITICAL: Wait for zombie cleanup
Line 235: await process.wait()  # ✅ CRITICAL: Wait for zombie cleanup
```

These explain a non-obvious requirement (zombie process prevention).

---

### Cleanup Command

After removing comments, run:
```bash
# Verify no syntax errors
python -m py_compile api/webhooks/github.py
python -m py_compile api/webhooks/jira.py
python -m py_compile api/webhooks/slack.py
python -m py_compile api/webhooks/sentry.py
python -m py_compile api/webhooks_dynamic.py
python -m py_compile workers/task_worker.py
python -m py_compile api/credentials.py

# Run tests to ensure nothing broke
pytest tests/ -x -q
```

---

## Execution Order

1. **Gap 3**: Dynamic Webhook Signature Verification (security first)
2. **Gap 4**: Response to Webhook Source (completes webhook flow)
3. **Gap 5**: Static + Dynamic Command Merging (extends functionality)
4. **Gap 2**: Skill webhook_config Synchronization (automation)
5. **Gap 1**: Webhook Creator Agent (ties everything together)
6. **Code Cleanup**: Remove redundant comments (final polish)

---

## Test Execution Commands

```bash
# Run all new tests
pytest tests/unit/test_webhook_creator_agent.py -v
pytest tests/unit/test_skill_webhook_sync.py -v
pytest tests/unit/test_dynamic_webhook_signatures.py -v
pytest tests/unit/test_webhook_response.py -v
pytest tests/unit/test_jira_client.py -v
pytest tests/unit/test_command_merger.py -v

# Run integration tests
pytest tests/integration/test_webhook_creator_flow.py -v
pytest tests/integration/test_skill_webhook_sync_api.py -v
pytest tests/integration/test_command_merging.py -v

# Run all tests with coverage
pytest --cov=core --cov=api --cov-report=html

# Run specific gap tests
pytest -k "webhook_creator" -v
pytest -k "skill_webhook" -v
pytest -k "signature" -v
pytest -k "action_comment" -v
pytest -k "merge" -v
```

---

## Definition of Done

For each gap:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No regression in existing tests
- [ ] Code reviewed and self-explanatory
- [ ] No redundant comments
- [ ] Acceptance criteria verified
- [ ] Documentation updated if needed
