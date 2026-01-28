---
name: Webhook Refactoring with TDD
overview: Refactor webhook handlers to use strict Pydantic types, YAML configuration, modular CLI runner, domain-specific organization, and full test coverage. Each todo follows TDD cycle (RED → GREEN → REFACTOR) with code cleanup (remove comments, unused code, dead code, unused imports/args/parameters).
todos:
  - id: "1.1"
    content: "RED: Write tests for GitHub Pydantic models (discriminated unions, validation, text extraction)"
    status: completed
  - id: "1.2"
    content: "RED: Write tests for Jira Pydantic models"
    status: completed
  - id: "1.3"
    content: "RED: Write tests for Slack Pydantic models"
    status: completed
  - id: "1.4"
    content: "RED: Write tests for domain error classes with context"
    status: completed
  - id: "1.5"
    content: "RED: Write tests for YAML config loader"
    status: completed
  - id: "2.1"
    content: "GREEN: Implement GitHub Pydantic models, run tests, cleanup unused code"
    status: completed
  - id: "2.2"
    content: "GREEN: Implement Jira Pydantic models, run tests, cleanup unused code"
    status: completed
  - id: "2.3"
    content: "GREEN: Implement Slack Pydantic models, run tests, cleanup unused code"
    status: completed
  - id: "2.4"
    content: "GREEN: Implement domain error classes, run tests, cleanup unused code"
    status: completed
  - id: "2.5"
    content: "GREEN: Create YAML configs and loader, run tests, cleanup unused code"
    status: completed
  - id: "3.1"
    content: "RED→GREEN→REFACTOR: Create domain constants files, replace magic strings"
    status: completed
  - id: "3.2"
    content: "RED→GREEN→REFACTOR: Refactor text extraction to Strategy pattern"
    status: completed
  - id: "4.1"
    content: "RED: Write tests for modular CLI runner"
    status: pending
  - id: "4.2"
    content: "GREEN: Implement modular CLI runner (base protocol + Claude implementation)"
    status: pending
  - id: "4.3"
    content: "REFACTOR: Break down run_claude_cli into smaller functions"
    status: pending
  - id: "5.1"
    content: "RED: Write tests for domain response handlers"
    status: pending
  - id: "5.2"
    content: "GREEN: Implement domain response handlers (move from response_poster.py)"
    status: pending
  - id: "5.3"
    content: "REFACTOR: Make response_poster.py a simple dispatcher"
    status: pending
  - id: "6.1"
    content: "RED: Write tests for domain routing extractors"
    status: pending
  - id: "6.2"
    content: "GREEN: Implement domain routing extractors with strict Pydantic models"
    status: pending
  - id: "6.3"
    content: "REFACTOR: Make routing_metadata.py a simple dispatcher"
    status: pending
  - id: "7.1"
    content: "RED→GREEN→REFACTOR: Refactor post_github_task_comment into smaller functions"
    status: pending
  - id: "7.2"
    content: "RED→GREEN→REFACTOR: Refactor send_github_immediate_response (extract event handlers)"
    status: pending
  - id: "7.3"
    content: "RED→GREEN→REFACTOR: Refactor handle_github_task_completion (extract error/approval/Slack logic)"
    status: pending
  - id: "8.1"
    content: "RED→GREEN→REFACTOR: Refactor GitHub route to show full flow, use errors/constants"
    status: pending
  - id: "8.2"
    content: "RED→GREEN→REFACTOR: Refactor Jira route to show full flow"
    status: pending
  - id: "8.3"
    content: "RED→GREEN→REFACTOR: Refactor Slack route to show full flow"
    status: pending
  - id: "9.1"
    content: "RED→GREEN→REFACTOR: Remove all dead code (verify reachability)"
    status: pending
  - id: "9.2"
    content: "RED→GREEN→REFACTOR: Remove unused imports/args/parameters"
    status: pending
  - id: "9.3"
    content: "RED→GREEN→REFACTOR: Remove all comments (code self-documenting)"
    status: pending
  - id: "9.4"
    content: "RED→GREEN→REFACTOR: Validate type safety (mypy --strict, no Any)"
    status: pending
  - id: "10.1"
    content: "RED→GREEN→REFACTOR: Write and run integration tests (full webhook flow)"
    status: pending
  - id: "10.2"
    content: "RED→GREEN→REFACTOR: Run regression tests (ensure no breaking changes)"
    status: pending
isProject: false
---

# Webhook Refactoring Plan - TDD Approach

## Overview

Refactor webhook handlers to eliminate `Any` types, use strict Pydantic models, move commands to YAML configuration, modularize CLI runner and response handlers, and ensure full test coverage. Each task follows TDD cycle: RED (write failing tests) → GREEN (implement) → REFACTOR (clean up).

## Key Principles

- **TDD Cycle**: Every todo follows RED → GREEN → REFACTOR
- **Code Cleanup**: Remove comments, unused code, dead code, unused imports/args/parameters
- **Reachability**: All code must be reachable (no dead code)
- **Test Coverage**: Business logic and requirements validated by tests
- **Strict Types**: No `Any`, all Pydantic models
- **Domain Organization**: Each webhook domain has its own models, errors, handlers, utils, constants
- **Full Flow Visible**: Route functions show step-by-step flow explicitly

## Architecture Changes

### Domain Structure (per webhook: github, jira, slack)

```
api/webhooks/{domain}/
├── models.py          # Strict Pydantic models (no Dict[str, Any])
├── errors.py          # Domain-specific errors with structured context
├── constants.py       # All magic strings/numbers
├── handlers.py        # Response posting handlers (lives in domain)
├── utils.py           # Signature verification, command matching, task creation
├── text_extractors.py # Strategy pattern for text extraction
├── validation.py      # Webhook validation logic
└── routes.py          # Main route with FULL FLOW visible
```

### Core Modularization

- `core/cli/` - Modular CLI runner (base protocol + implementations)
- `core/response_poster.py` - Dispatcher delegating to domain handlers
- `core/routing_metadata.py` - Dispatcher delegating to domain extractors

### Configuration

- `config/webhooks/{domain}.yaml` - YAML-based command configuration
- `config/webhooks/schema.yaml` - JSON Schema for validation
- `config/webhooks/README.md` - Configuration guide

## Implementation Plan

### Phase 1: Test Infrastructure & Models (TDD RED)

#### Todo 1.1: Create GitHub Pydantic Models (RED)

- **RED**: Write tests for GitHub webhook payload models
  - Test `GitHubWebhookPayload` with discriminated unions
  - Test `GitHubIssueCommentPayload`, `GitHubIssuesPayload`, `GitHubPullRequestPayload`
  - Test validation errors for invalid payloads
  - Test text extraction from each payload type
- **File**: `tests/unit/test_github_models.py`
- **Dependencies**: None

#### Todo 1.2: Create Jira Pydantic Models (RED)

- **RED**: Write tests for Jira webhook payload models
  - Test `JiraWebhookPayload` with all event types
  - Test validation and text extraction
- **File**: `tests/unit/test_jira_models.py`
- **Dependencies**: None

#### Todo 1.3: Create Slack Pydantic Models (RED)

- **RED**: Write tests for Slack webhook payload models
  - Test `SlackWebhookPayload` for Events API and slash commands
  - Test validation and text extraction
- **File**: `tests/unit/test_slack_models.py`
- **Dependencies**: None

#### Todo 1.4: Create Domain Error Classes (RED)

- **RED**: Write tests for domain-specific error classes
  - Test `GitHubErrorContext`, `JiraErrorContext`, `SlackErrorContext` dataclasses
  - Test error classes with context serialization
- **Files**:
  - `tests/unit/test_github_errors.py`
  - `tests/unit/test_jira_errors.py`
  - `tests/unit/test_slack_errors.py`
- **Dependencies**: None

#### Todo 1.5: Create YAML Config Loader Tests (RED)

- **RED**: Write tests for YAML configuration loading
  - Test loading `config/webhooks/github.yaml`
  - Test validation against JSON Schema
  - Test error messages for invalid configs
- **File**: `tests/unit/test_webhook_config_loader.py`
- **Dependencies**: None

### Phase 2: Implement Models & Configuration (TDD GREEN)

#### Todo 2.1: Implement GitHub Pydantic Models (GREEN)

- **GREEN**: Create strict Pydantic models
  - `api/webhooks/github/models.py`
  - Replace `Dict[str, Any]` with nested Pydantic models
  - Use discriminated unions for event types
  - Implement text extraction methods
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 2.2: Implement Jira Pydantic Models (GREEN)

- **GREEN**: Create strict Pydantic models
  - `api/webhooks/jira/models.py`
  - Replace `Dict[str, Any]` with nested Pydantic models
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 2.3: Implement Slack Pydantic Models (GREEN)

- **GREEN**: Create strict Pydantic models
  - `api/webhooks/slack/models.py`
  - Replace `Dict[str, Any]` with nested Pydantic models
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 2.4: Implement Domain Error Classes (GREEN)

- **GREEN**: Create error classes with structured context
  - `api/webhooks/github/errors.py` - `GitHubErrorContext`, `GitHubValidationError`, etc.
  - `api/webhooks/jira/errors.py` - `JiraErrorContext`, `JiraValidationError`, etc.
  - `api/webhooks/slack/errors.py` - `SlackErrorContext`, `SlackValidationError`, etc.
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 2.5: Create YAML Configuration Files (GREEN)

- **GREEN**: Create YAML configs and loader
  - `config/webhooks/github.yaml` - Commands from `core/webhook_configs.py`
  - `config/webhooks/jira.yaml` - Commands from `core/webhook_configs.py`
  - `config/webhooks/slack.yaml` - Commands from `core/webhook_configs.py`
  - `config/webhooks/schema.yaml` - JSON Schema for validation
  - `config/webhooks/README.md` - Configuration guide
  - `core/webhook_config_loader.py` - Load and validate YAML configs
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

### Phase 3: Domain Constants & Text Extraction (TDD)

#### Todo 3.1: Create Domain Constants (RED → GREEN → REFACTOR)

- **RED**: Write tests for constants usage
  - Test constants are used instead of magic strings
- **GREEN**: Create constants files
  - `api/webhooks/github/constants.py` - All magic strings (event types, headers, etc.)
  - `api/webhooks/jira/constants.py` - All magic strings
  - `api/webhooks/slack/constants.py` - All magic strings
- **REFACTOR**: Replace all magic strings with constants
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 3.2: Refactor Text Extraction Strategy (RED → GREEN → REFACTOR)

- **RED**: Write tests for text extraction strategy
  - Test priority-based extraction (comment > PR body > PR title > issue body > issue title)
  - Test each strategy independently
- **GREEN**: Implement strategy pattern
  - `api/webhooks/github/text_extractors.py` - `GitHubTextExtractionStrategy` with priority chain
  - Replace `if/elif` chain in `validation.py:38-48`
- **REFACTOR**: Simplify strategy implementation
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

### Phase 4: Modular CLI Runner (TDD)

#### Todo 4.1: Create CLI Runner Tests (RED)

- **RED**: Write tests for modular CLI runner
  - Test `CLIRunner` protocol
  - Test `ClaudeCLIRunner` implementation
  - Test easy switching of CLI implementation
- **File**: `tests/unit/test_cli_runner_modular.py`
- **Dependencies**: None

#### Todo 4.2: Implement Modular CLI Runner (GREEN)

- **GREEN**: Refactor CLI runner to be modular
  - `core/cli/base.py` - `CLIRunner` protocol, `CLIResult` dataclass
  - `core/cli/claude.py` - `ClaudeCLIRunner` implementation (extract from `cli_runner.py`)
  - `core/cli_runner.py` - Simple wrapper using `_default_cli_runner = ClaudeCLIRunner()`
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments from `cli_runner.py`

#### Todo 4.3: Refactor CLI Runner (REFACTOR)

- **REFACTOR**: Break down `run_claude_cli` into smaller functions
  - Extract subprocess creation
  - Extract stdout/stderr reading
  - Extract JSON parsing
  - Extract error handling
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

### Phase 5: Domain Response Handlers (TDD)

#### Todo 5.1: Create Response Handler Tests (RED)

- **RED**: Write tests for domain-specific response handlers
  - Test `GitHubResponseHandler.post_response()`
  - Test `JiraResponseHandler.post_response()`
  - Test `SlackResponseHandler.post_response()`
- **Files**:
  - `tests/unit/test_github_response_handler.py`
  - `tests/unit/test_jira_response_handler.py`
  - `tests/unit/test_slack_response_handler.py`
- **Dependencies**: Models (Todo 2.1-2.3)

#### Todo 5.2: Implement Domain Response Handlers (GREEN)

- **GREEN**: Create domain-specific response handlers
  - `api/webhooks/github/handlers.py` - `GitHubResponseHandler` (move from `response_poster.py`)
  - `api/webhooks/jira/handlers.py` - `JiraResponseHandler` (move from `response_poster.py`)
  - `api/webhooks/slack/handlers.py` - `SlackResponseHandler` (move from `response_poster.py`)
  - Use strict Pydantic models for routing metadata
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 5.3: Refactor Response Poster Dispatcher (REFACTOR)

- **REFACTOR**: Make `response_poster.py` a simple dispatcher
  - `core/response_poster.py` - Dispatcher delegating to domain handlers
  - Remove `if/elif` chain, use dispatch table
  - Use strict `SourceMetadata` Pydantic model
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

### Phase 6: Domain Routing Metadata Extractors (TDD)

#### Todo 6.1: Create Routing Metadata Tests (RED)

- **RED**: Write tests for domain-specific routing extractors
  - Test `extract_github_routing_metadata()` returns strict Pydantic model
  - Test `extract_jira_routing_metadata()` returns strict Pydantic model
  - Test `extract_slack_routing_metadata()` returns strict Pydantic model
- **File**: `tests/unit/test_routing_metadata.py`
- **Dependencies**: Models (Todo 2.1-2.3)

#### Todo 6.2: Implement Domain Routing Extractors (GREEN)

- **GREEN**: Create domain-specific routing extractors
  - `api/webhooks/github/utils.py` - `extract_github_routing_metadata()` returns `GitHubRoutingMetadata`
  - `api/webhooks/jira/utils.py` - `extract_jira_routing_metadata()` returns `JiraRoutingMetadata`
  - `api/webhooks/slack/utils.py` - `extract_slack_routing_metadata()` returns `SlackRoutingMetadata`
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 6.3: Refactor Routing Metadata Dispatcher (REFACTOR)

- **REFACTOR**: Make `routing_metadata.py` a simple dispatcher
  - `core/routing_metadata.py` - Dispatcher delegating to domain extractors
  - Remove `dict.get()` chains, use strict Pydantic models
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

### Phase 7: Refactor Complex Functions (TDD)

#### Todo 7.1: Refactor `post_github_task_comment` (RED → GREEN → REFACTOR)

- **RED**: Write tests for refactored function
  - Test each extracted function: `extract_repository_info`, `format_task_message`, `determine_comment_target`, `post_comment_to_target`
- **GREEN**: Extract into smaller functions
  - Move to `api/webhooks/github/comment_poster.py`
  - Break down into single-responsibility functions
  - Use strict Pydantic models
- **REFACTOR**: Simplify logic, remove duplication
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 7.2: Refactor `send_github_immediate_response` (RED → GREEN → REFACTOR)

- **RED**: Write tests for refactored function
  - Test event-specific handlers (issue_comment, issues, pull_request)
  - Test token setup extraction
- **GREEN**: Extract event handlers and token setup
  - Extract `_setup_github_token()` function
  - Extract `_handle_issue_comment_response()`, `_handle_issues_response()`, `_handle_pull_request_response()`
- **REFACTOR**: Remove duplication, simplify
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 7.3: Refactor `handle_github_task_completion` (RED → GREEN → REFACTOR)

- **RED**: Write tests for refactored function
  - Test error handling extraction
  - Test approval logic extraction
  - Test Slack notification extraction
- **GREEN**: Extract into smaller functions
  - Extract error handling, approval logic, Slack notifications
- **REFACTOR**: Simplify, remove duplication
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

### Phase 8: Route Functions - Full Flow Visible (TDD)

#### Todo 8.1: Refactor GitHub Route (RED → GREEN → REFACTOR)

- **RED**: Write integration tests for route function
  - Test full flow: signature → parse → validate → match → respond → create task → log
  - Test error handling at each step
- **GREEN**: Refactor route to show full flow
  - `api/webhooks/github/routes.py` - Numbered steps, explicit function calls
  - Use domain-specific errors with context
  - Use constants instead of magic strings
- **REFACTOR**: Simplify, ensure all code is reachable
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 8.2: Refactor Jira Route (RED → GREEN → REFACTOR)

- **RED**: Write integration tests for route function
- **GREEN**: Refactor route to show full flow
  - `api/webhooks/jira/routes.py` - Numbered steps, explicit function calls
- **REFACTOR**: Simplify, ensure all code is reachable
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

#### Todo 8.3: Refactor Slack Route (RED → GREEN → REFACTOR)

- **RED**: Write integration tests for route function
- **GREEN**: Refactor route to show full flow
  - `api/webhooks/slack/routes.py` - Numbered steps, explicit function calls
- **REFACTOR**: Simplify, ensure all code is reachable
- **Run tests**: Verify all tests pass
- **Cleanup**: Remove unused imports, dead code, comments

### Phase 9: Code Cleanup & Validation (TDD)

#### Todo 9.1: Remove Dead Code (RED → GREEN → REFACTOR)

- **RED**: Write tests to verify no dead code exists
  - Use coverage tool to identify unreachable code
- **GREEN**: Remove all dead code
  - Remove unreachable branches
  - Remove unused functions
  - Remove commented-out code
- **REFACTOR**: Verify all code is reachable
- **Run tests**: Verify all tests pass

#### Todo 9.2: Remove Unused Imports/Args/Parameters (RED → GREEN → REFACTOR)

- **RED**: Write tests to verify no unused imports/args
  - Use linter to identify unused imports/args
- **GREEN**: Remove all unused imports/args/parameters
  - Run `mypy --strict` to catch unused
  - Remove unused function parameters
- **REFACTOR**: Verify code still works
- **Run tests**: Verify all tests pass

#### Todo 9.3: Remove Comments (RED → GREEN → REFACTOR)

- **RED**: Verify code is self-documenting (no comments needed)
- **GREEN**: Remove all comments
  - Code should be self-documenting through names and structure
- **REFACTOR**: Improve naming if needed for clarity
- **Run tests**: Verify all tests pass

#### Todo 9.4: Type Safety Validation (RED → GREEN → REFACTOR)

- **RED**: Write tests that verify no `Any` types
  - Use `mypy --strict` to catch `Any` usage
- **GREEN**: Replace all `Any` with strict types
  - Fix all `mypy` errors
- **REFACTOR**: Improve type definitions if needed
- **Run tests**: Verify all tests pass

### Phase 10: Integration & Regression Testing

#### Todo 10.1: Integration Tests (RED → GREEN → REFACTOR)

- **RED**: Write end-to-end integration tests
  - Test full webhook flow from request to response
  - Test all three webhook types (GitHub, Jira, Slack)
- **GREEN**: Ensure all integration tests pass
- **REFACTOR**: Optimize test performance
- **Run tests**: Verify all tests pass

#### Todo 10.2: Regression Tests (RED → GREEN → REFACTOR)

- **RED**: Run all existing tests to establish baseline
- **GREEN**: Ensure all existing tests still pass
- **REFACTOR**: Update tests if behavior changed (intentionally)
- **Run tests**: Verify no regressions

## File Structure After Refactoring

```
api/webhooks/
├── github/
│   ├── __init__.py
│   ├── models.py              # Strict Pydantic models
│   ├── errors.py              # Domain errors with context
│   ├── constants.py           # All magic strings
│   ├── handlers.py            # Response posting (lives here)
│   ├── utils.py               # Signature, command matching, task creation
│   ├── text_extractors.py     # Strategy pattern for text extraction
│   ├── comment_poster.py      # Extracted from utils.py
│   ├── validation.py          # Webhook validation
│   └── routes.py              # Full flow visible
├── jira/
│   └── [same structure]
└── slack/
    └── [same structure]

core/
├── cli/
│   ├── __init__.py
│   ├── base.py                # CLIRunner protocol, CLIResult
│   └── claude.py              # ClaudeCLIRunner implementation
├── cli_runner.py             # Simple wrapper (modular)
├── response_poster.py        # Dispatcher (delegates to domains)
└── routing_metadata.py       # Dispatcher (delegates to domains)

config/
└── webhooks/
    ├── github.yaml
    ├── jira.yaml
    ├── slack.yaml
    ├── schema.yaml
    └── README.md

tests/
├── unit/
│   ├── test_github_models.py
│   ├── test_github_errors.py
│   ├── test_github_response_handler.py
│   ├── test_jira_models.py
│   ├── test_slack_models.py
│   ├── test_cli_runner_modular.py
│   └── [other unit tests]
└── integration/
    ├── test_webhook_full_flow.py
    └── [other integration tests]
```

## Success Criteria

1. ✅ No `Any` types - all strict Pydantic models
2. ✅ No `dict` parameters - all typed models
3. ✅ No `if/elif` chains - use Strategy/Dispatch patterns
4. ✅ No comments - code is self-documenting
5. ✅ No unused code - all code is reachable
6. ✅ No unused imports/args/parameters
7. ✅ All tests pass - business logic validated
8. ✅ YAML configuration - easy to maintain
9. ✅ Modular CLI runner - easy to switch implementations
10. ✅ Domain organization - everything lives together
11. ✅ Full flow visible - route functions show every step
12. ✅ Type safety - `mypy --strict` passes

## Testing Strategy

- **Unit Tests**: Test each function/class in isolation
- **Integration Tests**: Test full webhook flow
- **Regression Tests**: Ensure existing functionality preserved
- **Type Tests**: `mypy --strict` to catch type errors
- **Coverage**: Aim for >90% coverage on business logic

## Code Examples

### Example 1: GitHub Pydantic Models (api/webhooks/github/models.py)

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, Discriminator

class GitHubUser(BaseModel):
    login: str
    id: int
    type: str

class GitHubRepository(BaseModel):
    id: int
    name: str
    full_name: str
    owner: GitHubUser
    private: bool

class GitHubIssue(BaseModel):
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    user: GitHubUser
    pull_request: Optional[dict] = None

class GitHubComment(BaseModel):
    id: int
    body: str
    user: GitHubUser
    created_at: str

class GitHubPullRequest(BaseModel):
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    user: GitHubUser

class GitHubIssueCommentPayload(BaseModel):
    action: Literal["created", "edited", "deleted"]
    issue: GitHubIssue
    comment: GitHubComment
    repository: GitHubRepository
    sender: GitHubUser

class GitHubIssuesPayload(BaseModel):
    action: Literal["opened", "edited", "closed", "reopened"]
    issue: GitHubIssue
    repository: GitHubRepository
    sender: GitHubUser

class GitHubPullRequestPayload(BaseModel):
    action: Literal["opened", "edited", "closed", "synchronize"]
    pull_request: GitHubPullRequest
    repository: GitHubRepository
    sender: GitHubUser

GitHubWebhookPayload = GitHubIssueCommentPayload | GitHubIssuesPayload | GitHubPullRequestPayload
```

### Example 2: Domain Error Classes (api/webhooks/github/errors.py)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class GitHubErrorContext:
    repo: Optional[str] = None
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None
    comment_id: Optional[int] = None
    task_id: Optional[str] = None
    event_type: Optional[str] = None

class GitHubValidationError(Exception):
    def __init__(self, message: str, context: Optional[GitHubErrorContext] = None):
        super().__init__(message)
        self.context = context or GitHubErrorContext()

class GitHubProcessingError(Exception):
    def __init__(self, message: str, context: Optional[GitHubErrorContext] = None):
        super().__init__(message)
        self.context = context or GitHubErrorContext()

class GitHubResponseError(Exception):
    def __init__(self, message: str, context: Optional[GitHubErrorContext] = None):
        super().__init__(message)
        self.context = context or GitHubErrorContext()

class GitHubSignatureError(Exception):
    def __init__(self, message: str, context: Optional[GitHubErrorContext] = None):
        super().__init__(message)
        self.context = context or GitHubErrorContext()
```

### Example 3: Domain Constants (api/webhooks/github/constants.py)

```python
GITHUB_EVENT_ISSUE_COMMENT = "issue_comment"
GITHUB_EVENT_ISSUES = "issues"
GITHUB_EVENT_PULL_REQUEST = "pull_request"

GITHUB_ACTION_CREATED = "created"
GITHUB_ACTION_OPENED = "opened"
GITHUB_ACTION_CLOSED = "closed"

GITHUB_HEADER_EVENT = "X-GitHub-Event"
GITHUB_HEADER_SIGNATURE = "X-Hub-Signature-256"

GITHUB_REACTION_EYES = "eyes"
GITHUB_REACTION_THUMBS_DOWN = "-1"

GITHUB_MAX_COMMENT_LENGTH_SUCCESS = 4000
GITHUB_MAX_COMMENT_LENGTH_ERROR = 8000
```

### Example 4: Route Function - Full Flow Visible (api/webhooks/github/routes.py)

```python
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB
from core.webhook_configs import GITHUB_WEBHOOK

from api.webhooks.github.models import (
    GitHubWebhookPayload,
    GitHubIssueCommentPayload,
    GitHubIssuesPayload,
    GitHubPullRequestPayload,
)
from api.webhooks.github.errors import (
    GitHubValidationError,
    GitHubProcessingError,
    GitHubResponseError,
    GitHubSignatureError,
    GitHubErrorContext,
)
from api.webhooks.github.constants import (
    GITHUB_EVENT_ISSUE_COMMENT,
    GITHUB_EVENT_ISSUES,
    GITHUB_EVENT_PULL_REQUEST,
    GITHUB_HEADER_EVENT,
)
from api.webhooks.github.utils import (
    verify_github_signature,
    match_github_command,
    create_github_task,
)
from api.webhooks.github.handlers import (
    send_github_immediate_response,
    handle_github_task_completion,
)
from api.webhooks.github.validation import validate_github_webhook

logger = structlog.get_logger()
router = APIRouter()

COMPLETION_HANDLER = "api.webhooks.github.routes.handle_github_task_completion"

@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    repo_info: str | None = None
    issue_number: int | None = None
    task_id: str | None = None
    event_type: str = "unknown"

    try:
        body = await request.body()

        try:
            await verify_github_signature(request, body)
        except GitHubSignatureError as e:
            context = GitHubErrorContext(event_type=event_type)
            logger.warning("github_signature_verification_failed", error=str(e), context=context)
            raise HTTPException(status_code=401, detail=str(e))

        try:
            raw_payload = json.loads(body.decode())
            raw_payload["provider"] = "github"
        except json.JSONDecodeError as e:
            logger.error("github_payload_parse_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")

        event_type = request.headers.get(GITHUB_HEADER_EVENT, "unknown")
        action = raw_payload.get("action", "")
        if action:
            event_type = f"{event_type}.{action}"

        try:
            payload = GitHubWebhookPayload.parse_obj(raw_payload)
        except Exception as e:
            logger.error("github_payload_validation_failed", error=str(e), event_type=event_type)
            raise GitHubValidationError(f"Invalid payload structure: {str(e)}")

        repo = payload.repository
        repo_info = f"{repo.owner.login}/{repo.name}"

        if isinstance(payload, GitHubIssueCommentPayload):
            issue_number = payload.issue.number
        elif isinstance(payload, GitHubIssuesPayload):
            issue_number = payload.issue.number
        elif isinstance(payload, GitHubPullRequestPayload):
            issue_number = payload.pull_request.number

        logger.info(
            "github_webhook_received",
            event_type=event_type,
            repo=repo_info,
            issue_number=issue_number,
        )

        validation_result = validate_github_webhook(payload)
        if not validation_result.is_valid:
            logger.info(
                "github_webhook_rejected_by_validation",
                event_type=event_type,
                repo=repo_info,
                issue_number=issue_number,
                reason=validation_result.error_message,
            )
            return {
                "status": "rejected",
                "actions": 0,
                "message": validation_result.error_message,
            }

        command = await match_github_command(payload, event_type)
        if not command:
            logger.warning(
                "github_no_command_matched",
                event_type=event_type,
                repo=repo_info,
                issue_number=issue_number,
            )
            return {
                "status": "received",
                "actions": 0,
                "message": "No command matched",
            }

        logger.info(
            "github_command_matched",
            command=command.name,
            event_type=event_type,
            repo=repo_info,
        )

        immediate_response_sent = await send_github_immediate_response(
            payload=payload,
            command=command,
            event_type=event_type,
        )

        if not immediate_response_sent:
            logger.error(
                "github_immediate_response_failed",
                repo=repo_info,
                issue_number=issue_number,
                event_type=event_type,
            )
            return {
                "status": "rejected",
                "message": "Failed to send immediate response. Check GITHUB_TOKEN configuration.",
                "error": "immediate_response_failed",
            }

        task_id = await create_github_task(
            command=command,
            payload=payload,
            db=db,
            completion_handler=COMPLETION_HANDLER,
        )

        logger.info(
            "github_task_created_success",
            task_id=task_id,
            repo=repo_info,
            issue_number=issue_number,
        )

        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=GITHUB_WEBHOOK.name,
            provider="github",
            event_type=event_type,
            payload_json=json.dumps(raw_payload),
            matched_command=command.name,
            task_id=task_id,
            response_sent=immediate_response_sent,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event_db)
        await db.commit()

        logger.info(
            "github_event_logged",
            event_id=event_id,
            task_id=task_id,
            repo=repo_info,
            issue_number=issue_number,
        )

        logger.info(
            "github_webhook_processed",
            task_id=task_id,
            command=command.name,
            event_type=event_type,
            repo=repo_info,
            issue_number=issue_number,
            immediate_response_sent=immediate_response_sent,
        )

        return {
            "status": "accepted",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent,
            "completion_handler": COMPLETION_HANDLER,
            "message": "Task queued for processing",
        }

    except HTTPException:
        raise

    except GitHubValidationError as e:
        logger.warning(
            "github_webhook_validation_failed",
            error=str(e),
            context=e.context.__dict__ if e.context else None,
            repo=repo_info,
            issue_number=issue_number,
        )
        raise HTTPException(status_code=400, detail=str(e))

    except GitHubProcessingError as e:
        logger.error(
            "github_webhook_processing_failed",
            error=str(e),
            context=e.context.__dict__ if e.context else None,
            repo=repo_info,
            issue_number=issue_number,
            task_id=task_id,
        )
        raise HTTPException(status_code=500, detail=str(e))

    except GitHubResponseError as e:
        logger.error(
            "github_webhook_response_failed",
            error=str(e),
            context=e.context.__dict__ if e.context else None,
            repo=repo_info,
            issue_number=issue_number,
            task_id=task_id,
        )
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        context = GitHubErrorContext(
            repo=repo_info,
            issue_number=issue_number,
            task_id=task_id,
            event_type=event_type,
        )
        logger.error(
            "github_webhook_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
            context=context.__dict__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Example 5: YAML Configuration (config/webhooks/github.yaml)

```yaml
name: github
endpoint: /webhooks/github
source: github
command_prefix: "@agent"
requires_signature: true
signature_header: "X-Hub-Signature-256"
secret_env_var: "GITHUB_WEBHOOK_SECRET"
default_command: analyze
commands:
  - name: analyze
    aliases: [analysis, analyze-issue]
    description: Analyze an issue or PR
    target_agent: planning
    prompt_template: |
      You are analyzing GitHub {{event_type}} #{{issue.number}}...
    requires_approval: false
  - name: plan
    aliases: [plan-fix, create-plan]
    description: Create a plan to fix an issue
    target_agent: planning
    prompt_template: |
      You are creating an implementation plan for GitHub issue #{{issue.number}}...
    requires_approval: false
  - name: fix
    aliases: [implement, execute]
    description: Implement a fix for an issue
    target_agent: executor
    prompt_template: |
      You are implementing a fix for GitHub issue #{{issue.number}}...
    requires_approval: true
```

### Example 6: Modular CLI Runner (core/cli/base.py)

```python
from typing import Protocol
from pathlib import Path
from dataclasses import dataclass
import asyncio

@dataclass
class CLIResult:
    success: bool
    output: str
    clean_output: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    error: str | None = None

class CLIRunner(Protocol):
    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue,
        task_id: str = "",
        timeout_seconds: int = 3600,
        model: str | None = None,
        allowed_tools: str | None = None,
        agents: str | None = None,
        debug_mode: str | None = None,
    ) -> CLIResult:
        ...
```

### Example 7: CLI Runner Implementation (core/cli/claude.py)

```python
from pathlib import Path
import asyncio
from core.cli.base import CLIRunner, CLIResult

class ClaudeCLIRunner:
    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue,
        task_id: str = "",
        timeout_seconds: int = 3600,
        model: str | None = None,
        allowed_tools: str | None = None,
        agents: str | None = None,
        debug_mode: str | None = None,
    ) -> CLIResult:
        cmd = self._build_command(
            prompt=prompt,
            model=model,
            allowed_tools=allowed_tools,
            agents=agents,
            debug_mode=debug_mode,
        )
        process = await self._create_process(cmd, working_dir, task_id)
        result = await self._run_process(process, output_queue, timeout_seconds)
        return result

    def _build_command(self, prompt: str, model: str | None, ...) -> list[str]:
        ...

    async def _create_process(self, cmd: list[str], working_dir: Path, task_id: str):
        ...

    async def _run_process(self, process, output_queue: asyncio.Queue, timeout: int) -> CLIResult:
        ...
```

### Example 8: CLI Runner Wrapper (core/cli_runner.py)

```python
from pathlib import Path
import asyncio
from core.cli.base import CLIResult
from core.cli.claude import ClaudeCLIRunner

_default_cli_runner = ClaudeCLIRunner()

async def run_claude_cli(
    prompt: str,
    working_dir: Path,
    output_queue: asyncio.Queue,
    task_id: str = "",
    timeout_seconds: int = 3600,
    model: str | None = None,
    allowed_tools: str | None = None,
    agents: str | None = None,
    debug_mode: str | None = None,
) -> CLIResult:
    return await _default_cli_runner.run(
        prompt=prompt,
        working_dir=working_dir,
        output_queue=output_queue,
        task_id=task_id,
        timeout_seconds=timeout_seconds,
        model=model,
        allowed_tools=allowed_tools,
        agents=agents,
        debug_mode=debug_mode,
    )
```

### Example 9: Domain Response Handler (api/webhooks/github/handlers.py)

```python
from api.webhooks.github.models import GitHubRoutingMetadata
from api.webhooks.github.errors import GitHubResponseError, GitHubErrorContext
from api.webhooks.github.constants import GITHUB_MAX_COMMENT_LENGTH_SUCCESS
from core.github_client import github_client
import structlog

logger = structlog.get_logger()

class GitHubResponseHandler:
    async def post_response(
        self,
        routing: GitHubRoutingMetadata,
        result: str,
    ) -> bool:
        if not routing.owner or not routing.repo:
            logger.error("github_routing_missing", routing=routing)
            return False

        try:
            if routing.pr_number:
                await github_client.post_pr_comment(
                    routing.owner,
                    routing.repo,
                    routing.pr_number,
                    result[:GITHUB_MAX_COMMENT_LENGTH_SUCCESS],
                )
                logger.info("github_response_posted", type="pr", number=routing.pr_number)
                return True
            elif routing.issue_number:
                await github_client.post_issue_comment(
                    routing.owner,
                    routing.repo,
                    routing.issue_number,
                    result[:GITHUB_MAX_COMMENT_LENGTH_SUCCESS],
                )
                logger.info("github_response_posted", type="issue", number=routing.issue_number)
                return True
            else:
                logger.error("github_no_pr_or_issue", routing=routing)
                return False
        except Exception as e:
            context = GitHubErrorContext(
                repo=f"{routing.owner}/{routing.repo}",
                issue_number=routing.issue_number,
                pr_number=routing.pr_number,
            )
            raise GitHubResponseError(f"Failed to post response: {str(e)}", context=context)
```

### Example 10: Response Poster Dispatcher (core/response_poster.py)

```python
from api.webhooks.github.handlers import GitHubResponseHandler
from api.webhooks.jira.handlers import JiraResponseHandler
from api.webhooks.slack.handlers import SlackResponseHandler
from api.webhooks.github.models import SourceMetadata
import structlog

logger = structlog.get_logger()

class ResponsePoster:
    def __init__(self):
        self._handlers = {
            "github": GitHubResponseHandler(),
            "jira": JiraResponseHandler(),
            "slack": SlackResponseHandler(),
        }

    async def post(self, source_metadata: SourceMetadata, result: str) -> bool:
        handler = self._handlers.get(source_metadata.webhook_source)
        if not handler:
            logger.warning("unknown_webhook_source", source=source_metadata.webhook_source)
            return False

        try:
            return await handler.post_response(source_metadata.routing, result)
        except Exception as e:
            logger.error("response_post_failed", source=source_metadata.webhook_source, error=str(e))
            return False

response_poster = ResponsePoster()

async def post_response(source_metadata: SourceMetadata, result: str) -> bool:
    return await response_poster.post(source_metadata, result)
```

### Example 11: Text Extraction Strategy (api/webhooks/github/text_extractors.py)

```python
from abc import ABC, abstractmethod
from api.webhooks.github.models import GitHubWebhookPayload

class GitHubTextExtractionStrategy(ABC):
    @abstractmethod
    def extract(self, payload: GitHubWebhookPayload) -> str:
        pass

class CommentBodyStrategy(GitHubTextExtractionStrategy):
    def extract(self, payload: GitHubWebhookPayload) -> str:
        if isinstance(payload, GitHubIssueCommentPayload):
            return payload.comment.body or ""
        return ""

class PullRequestBodyStrategy(GitHubTextExtractionStrategy):
    def extract(self, payload: GitHubWebhookPayload) -> str:
        if isinstance(payload, GitHubPullRequestPayload):
            title = payload.pull_request.title or ""
            body = payload.pull_request.body or ""
            return f"{title}{body}"
        return ""

class IssueBodyStrategy(GitHubTextExtractionStrategy):
    def extract(self, payload: GitHubWebhookPayload) -> str:
        if isinstance(payload, GitHubIssuesPayload):
            title = payload.issue.title or ""
            body = payload.issue.body or ""
            return f"{title}{body}"
        return ""

class GitHubTextExtractor:
    def __init__(self):
        self.strategies = [
            CommentBodyStrategy(),
            PullRequestBodyStrategy(),
            IssueBodyStrategy(),
        ]

    def extract(self, payload: GitHubWebhookPayload) -> str:
        for strategy in self.strategies:
            text = strategy.extract(payload)
            if text:
                return text
        return ""
```

### Example 12: Routing Metadata Models (api/webhooks/github/models.py - additional)

```python
class GitHubRoutingMetadata(BaseModel):
    owner: str
    repo: str
    issue_number: int | None = None
    pr_number: int | None = None
    comment_id: int | None = None
    sender: str | None = None
```

### Example 13: WebhookCommand Pydantic Model (shared/machine_models.py - simplified)

```python
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Literal, Optional
from pathlib import Path
from datetime import datetime, timezone
import re

NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")

def validate_name_format(value: str) -> str:
    if not NAME_PATTERN.match(value):
        raise ValueError("must be lowercase alphanumeric with hyphens")
    return value

class WebhookCommand(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    aliases: List[str] = Field(default_factory=list)
    description: str = Field(default="")
    target_agent: str = Field(...)
    prompt_template: str = Field(..., min_length=1)
    requires_approval: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_name_format(v)

    @field_validator("aliases")
    @classmethod
    def validate_aliases(cls, v: List[str]) -> List[str]:
        for alias in v:
            validate_name_format(alias)
        return v

def validate_no_duplicate_commands(command_names: List[str]) -> None:
    unique_names = set(command_names)
    if len(command_names) != len(unique_names):
        duplicates = [name for name in unique_names if command_names.count(name) > 1]
        raise ValueError(f"duplicate command names: {duplicates}")

def validate_default_command_exists(default_command: Optional[str], command_names: List[str]) -> None:
    if default_command and default_command not in command_names:
        raise ValueError(f"default_command '{default_command}' not found in commands")

class WebhookConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=64)
    endpoint: str = Field(..., pattern=r"^/webhooks/[a-z0-9-]+$")
    source: Literal["github", "jira", "sentry", "slack", "gitlab", "custom"] = "custom"
    commands: List[WebhookCommand] = Field(default_factory=list)
    command_prefix: str = Field(default="@agent")
    requires_signature: bool = Field(default=True)
    signature_header: Optional[str] = None
    secret_env_var: Optional[str] = None
    default_command: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_name_format(v)

    @model_validator(mode="after")
    def validate_commands(self) -> "WebhookConfig":
        if not self.commands:
            raise ValueError("webhook must have at least one command")
        
        command_names = [cmd.name for cmd in self.commands]
        validate_no_duplicate_commands(command_names)
        validate_default_command_exists(self.default_command, command_names)
        
        return self
```

### Example 14: YAML Config Loader (core/webhook_config_loader.py)

```python
from pathlib import Path
import yaml
import json
from typing import Dict, List
from shared.machine_models import WebhookConfig, WebhookCommand
import structlog

logger = structlog.get_logger()

class WebhookConfigLoader:
    def __init__(self, config_dir: Path = Path("config/webhooks")):
        self.config_dir = config_dir
        self.schema_path = config_dir / "schema.yaml"

    def load_webhook_config(self, webhook_name: str) -> WebhookConfig:
        yaml_path = self.config_dir / f"{webhook_name}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"webhook config not found: {yaml_path}")

        with open(yaml_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        self._validate_against_schema(yaml_data, webhook_name)

        commands = [
            WebhookCommand(**cmd_data) for cmd_data in yaml_data.get("commands", [])
        ]

        config = WebhookConfig(
            name=yaml_data["name"],
            endpoint=yaml_data["endpoint"],
            source=yaml_data["source"],
            commands=commands,
            command_prefix=yaml_data.get("command_prefix", "@agent"),
            requires_signature=yaml_data.get("requires_signature", True),
            signature_header=yaml_data.get("signature_header"),
            secret_env_var=yaml_data.get("secret_env_var"),
            default_command=yaml_data.get("default_command"),
        )

        logger.info("webhook_config_loaded", webhook=webhook_name, commands_count=len(commands))
        return config

    def load_all_webhook_configs(self) -> Dict[str, WebhookConfig]:
        configs = {}
        for yaml_file in self.config_dir.glob("*.yaml"):
            if yaml_file.name == "schema.yaml":
                continue
            webhook_name = yaml_file.stem
            try:
                configs[webhook_name] = self.load_webhook_config(webhook_name)
            except Exception as e:
                logger.error("webhook_config_load_failed", webhook=webhook_name, error=str(e))
                raise
        return configs

    def _validate_against_schema(self, yaml_data: dict, webhook_name: str) -> None:
        if not self.schema_path.exists():
            logger.warning("schema_not_found", schema_path=self.schema_path)
            return

        import jsonschema
        with open(self.schema_path, "r") as f:
            schema = yaml.safe_load(f)

        try:
            jsonschema.validate(yaml_data, schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"invalid webhook config for {webhook_name}: {e.message}")

webhook_config_loader = WebhookConfigLoader()
```

### Example 15: Command Matching with Strict Types (api/webhooks/github/utils.py)

```python
from api.webhooks.github.models import GitHubWebhookPayload, GitHubIssueCommentPayload
from api.webhooks.github.constants import GITHUB_EVENT_ISSUE_COMMENT
from shared.machine_models import WebhookCommand
from core.webhook_configs import GITHUB_WEBHOOK
from core.command_matcher import is_bot_comment, extract_command
from api.webhooks.github.text_extractors import GitHubTextExtractor
import structlog

logger = structlog.get_logger()

async def match_github_command(
    payload: GitHubWebhookPayload,
    event_type: str,
) -> WebhookCommand | None:
    sender = payload.sender
    if is_bot_comment(sender.login, sender.type):
        logger.info(
            "github_skipped_bot_comment",
            sender=sender.login,
            sender_type=sender.type,
            event_type=event_type,
        )
        return None

    if isinstance(payload, GitHubIssueCommentPayload):
        comment_id = payload.comment.id
        if await is_agent_posted_comment(comment_id):
            logger.info(
                "github_skipped_posted_comment",
                comment_id=comment_id,
                event_type=event_type,
            )
            return None

    text_extractor = GitHubTextExtractor()
    text = text_extractor.extract(payload)

    if not text:
        logger.debug("github_no_text_extracted", event_type=event_type)
        return None

    result = extract_command(text)
    if result is None:
        logger.debug(
            "github_no_agent_command",
            event_type=event_type,
            text_preview=text[:100] if text else "",
            sender=sender.login,
        )
        return None

    command_name, user_content = result
    if not isinstance(command_name, str):
        logger.warning(
            "github_command_name_not_string",
            command_name=command_name,
            command_name_type=type(command_name).__name__,
        )
        return None

    command_name_lower = command_name.lower()

    for cmd in GITHUB_WEBHOOK.commands:
        if cmd.name.lower() == command_name_lower:
            return cmd
        for alias in cmd.aliases:
            if isinstance(alias, str) and alias.lower() == command_name_lower:
                return cmd

    logger.warning("github_command_not_configured", command=command_name)
    return None
```

### Example 16: Command Usage in Task Creation (api/webhooks/github/utils.py)

```python
from shared.machine_models import WebhookCommand
from api.webhooks.github.models import GitHubWebhookPayload
from api.webhooks.github.utils import extract_github_routing_metadata
from core.webhook_engine import render_template, create_webhook_conversation
from core.database.models import SessionDB, TaskDB
from shared import TaskStatus, AgentType
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone

async def create_github_task(
    command: WebhookCommand,
    payload: GitHubWebhookPayload,
    db: AsyncSession,
    completion_handler: str,
) -> str:
    task_id = f"task-{uuid.uuid4().hex[:12]}"

    base_message = render_template(command.prompt_template, payload.model_dump(), task_id=task_id)

    from core.webhook_engine import wrap_prompt_with_brain_instructions
    message = wrap_prompt_with_brain_instructions(base_message, task_id=task_id)

    webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
    session_db = SessionDB(
        session_id=webhook_session_id,
        user_id="webhook-system",
        machine_id="claude-agent-001",
        connected_at=datetime.now(timezone.utc),
    )
    db.add(session_db)

    try:
        agent_type = AgentType(command.target_agent)
    except ValueError:
        agent_type = AgentType.CUSTOM

    routing = extract_github_routing_metadata(payload)

    task_db = TaskDB(
        task_id=task_id,
        session_id=webhook_session_id,
        user_id="webhook-system",
        assigned_agent=command.target_agent,
        agent_type=agent_type,
        status=TaskStatus.QUEUED,
        input_message=message,
        source="webhook",
        source_metadata=json.dumps({
            "webhook_source": "github",
            "webhook_name": GITHUB_WEBHOOK.name,
            "command": command.name,
            "original_target_agent": command.target_agent,
            "routing": routing.model_dump(),
            "payload": payload.model_dump(),
            "completion_handler": completion_handler,
        }),
    )
    db.add(task_db)
    await db.flush()

    from core.webhook_engine import generate_external_id, generate_flow_id
    external_id = generate_external_id("github", payload.model_dump())
    flow_id = generate_flow_id(external_id)

    source_metadata = json.loads(task_db.source_metadata or "{}")
    source_metadata["flow_id"] = flow_id
    source_metadata["external_id"] = external_id
    task_db.source_metadata = json.dumps(source_metadata)
    task_db.flow_id = flow_id

    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("github_conversation_created", conversation_id=conversation_id, task_id=task_id)

    await db.commit()

    from core.database.redis_client import redis_client
    await redis_client.push_task(task_id)

    logger.info("github_task_created", task_id=task_id, command=command.name)

    return task_id
```


### Example 17: YAML Schema for Validation (config/webhooks/schema.yaml)

```yaml
$schema: http://json-schema.org/draft-07/schema#
type: object
required:
  - name
  - endpoint
  - source
  - target_agent
  - commands
properties:
  name:
    type: string
    pattern: "^[a-z0-9-]+$"
    minLength: 1
    maxLength: 64
  endpoint:
    type: string
    pattern: "^/webhooks/[a-z0-9-]+$"
  source:
    type: string
    enum: [github, jira, sentry, slack, gitlab, custom]
  command_prefix:
    type: string
    default: "@agent"
  commands:
    type: array
    minItems: 1
    items:
      type: object
      required:
        - name
        - target_agent
        - prompt_template
      properties:
        name:
          type: string
          pattern: "^[a-z0-9-]+$"
          minLength: 1
          maxLength: 64
        aliases:
          type: array
          items:
            type: string
            pattern: "^[a-z0-9-]+$"
        description:
          type: string
          default: ""
        target_agent:
          type: string
          minLength: 1
        prompt_template:
          type: string
          minLength: 1
        requires_approval:
          type: boolean
          default: false
  requires_signature:
    type: boolean
    default: true
  signature_header:
    type: string
  secret_env_var:
    type: string
  default_command:
    type: string
```

### Example 18: Routing Metadata Extractor (api/webhooks/github/utils.py - extract function)

```python
from api.webhooks.github.models import (
    GitHubWebhookPayload,
    GitHubRoutingMetadata,
    GitHubIssueCommentPayload,
    GitHubIssuesPayload,
    GitHubPullRequestPayload,
)

def extract_github_routing_metadata(payload: GitHubWebhookPayload) -> GitHubRoutingMetadata:
    repo = payload.repository
    owner = repo.owner.login
    repo_name = repo.name

    issue_number = None
    pr_number = None
    comment_id = None
    sender = payload.sender.login

    if isinstance(payload, GitHubIssueCommentPayload):
        issue_number = payload.issue.number
        comment_id = payload.comment.id
    elif isinstance(payload, GitHubIssuesPayload):
        issue_number = payload.issue.number
        if payload.issue.pull_request:
            pr_number = payload.issue.number
    elif isinstance(payload, GitHubPullRequestPayload):
        pr_number = payload.pull_request.number

    return GitHubRoutingMetadata(
        owner=owner,
        repo=repo_name,
        issue_number=issue_number,
        pr_number=pr_number,
        comment_id=comment_id,
        sender=sender,
    )
```

## Notes

- Each todo must follow TDD cycle: RED → GREEN → REFACTOR
- Run tests after each change
- Remove dead code, unused imports, comments as you go
- Ensure all code is reachable
- Business logic must be validated by tests
