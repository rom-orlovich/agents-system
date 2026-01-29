# Webhook Utils Refactoring Plan

## Executive Summary

The webhook utility files have grown to be bloated and contain significant code duplication across three domains: Slack (946 lines), GitHub (645 lines), and Jira (824 lines). This refactoring plan outlines a systematic approach to extract common patterns, eliminate duplication, improve testability, and create a more maintainable architecture.

## Current Problems and Code Smells

### 1. Massive Code Duplication (DRY Violation)

**Text Extraction Functions** - Nearly identical implementations:
- `extract_slack_text()` - Slack utils, lines 32-52 (21 lines)
- `extract_github_text()` - GitHub utils, lines 47-85 (39 lines)
- `extract_jira_comment_text()` - Jira utils, lines 60-94 (35 lines)
- `_safe_string()` - Jira utils, lines 33-57 (25 lines)

All perform the same task: safely extract text from webhook payloads that might be strings, dicts, lists, or None.

**Signature Verification** - Nearly identical HMAC logic:
- `verify_slack_signature()` - Slack utils, lines 55-79 (25 lines)
- `verify_github_signature()` - GitHub utils, lines 88-108 (21 lines)
- `verify_jira_signature()` - Jira utils, lines 113-131 (19 lines)

**Agent Loop Prevention** - Duplicated Redis checks:
- `is_agent_posted_slack_message()` - Slack utils, lines 117-140 (24 lines)
- `is_agent_posted_comment()` - GitHub utils, lines 246-269 (24 lines)
- `is_agent_posted_jira_comment()` - Jira utils, lines 220-243 (24 lines)

**Task Creation** - 95% identical implementation:
- `create_slack_task()` - 99 lines
- `create_github_task()` - 101 lines
- `create_jira_task()` - 112 lines

### 2. Long Functions (>50 lines)

- `build_task_completion_blocks()` - 160 lines
- `create_task_from_button_action()` - 169 lines
- `send_slack_notification()` - 238 lines (Jira)

### 3. Scattered Responsibilities (SRP Violation)

Each utils file mixes:
- Signature verification (security)
- Text extraction (data transformation)
- Command matching (business logic)
- Task creation (orchestration)
- Response posting (API interaction)
- Loop prevention (caching)
- Message formatting (presentation)

## Proposed File Structure

```
api/webhooks/
├── common/
│   ├── signature/                  # NEW: Signature verification
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract signature verifier
│   │   └── hmac_verifier.py        # HMAC SHA256 implementation
│   │
│   ├── text_extraction/            # NEW: Text extraction utilities
│   │   ├── __init__.py
│   │   └── extractors.py           # Safe text extraction
│   │
│   ├── loop_prevention/            # NEW: Infinite loop prevention
│   │   ├── __init__.py
│   │   └── tracking.py             # Redis-based message tracking
│   │
│   ├── task_creation/              # NEW: Task creation orchestration
│   │   ├── __init__.py
│   │   ├── factory.py              # Task factory
│   │   └── sync.py                 # Claude Tasks sync
│   │
│   ├── formatting/                 # NEW: Message formatting
│   │   ├── __init__.py
│   │   ├── truncation.py           # Text truncation utilities
│   │   └── summary.py              # Task summary extraction
│   │
│   ├── notifications/              # NEW: Slack notifications
│   │   ├── __init__.py
│   │   ├── builder.py              # Block Kit block builder
│   │   └── sender.py               # Notification sender
│   │
│   └── constants.py                # NEW: Shared constants
│
├── slack/utils.py                  # Slim, Slack-specific only
├── github/utils.py                 # Slim, GitHub-specific only
└── jira/utils.py                   # Slim, Jira-specific only
```

## Refactoring Patterns

### Pattern 1: Extract Common Text Extractor

**Before:** Duplicated in each webhook utils file

**After:**
```python
# api/webhooks/common/text_extraction/extractors.py
class TextExtractor:
    @staticmethod
    def extract(value: Any, default: str = "", text_keys: list[str] = None) -> str:
        if value is None:
            return default
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return " ".join(str(item) for item in value if item) if value else default
        if isinstance(value, dict):
            text_keys = text_keys or ["text", "body", "content"]
            for key in text_keys:
                if key in value:
                    nested = value.get(key)
                    if isinstance(nested, str):
                        return nested
                    return TextExtractor.extract(nested, default, text_keys)
        return str(value) if value else default
```

**Benefit:** Eliminates 95 lines of duplication

### Pattern 2: Strategy Pattern for Signature Verification

**Before:** Three nearly identical HMAC functions

**After:**
```python
# api/webhooks/common/signature/hmac_verifier.py
class HmacSha256Verifier(SignatureVerifier):
    def __init__(self, secret: str, header_name: str,
                 prefix: str = "", timestamp_header: str = None):
        super().__init__(secret, header_name)
        self.prefix = prefix
        self.timestamp_header = timestamp_header

    def verify(self, request: Request, body: bytes) -> None:
        # Unified verification logic
        pass

# Usage
def create_slack_verifier() -> HmacSha256Verifier:
    return HmacSha256Verifier(
        secret=settings.slack_webhook_secret,
        header_name="X-Slack-Signature",
        prefix="v0=",
        timestamp_header="X-Slack-Request-Timestamp"
    )
```

**Benefit:** Reduces 65 lines to ~60 shared + 3 per domain

### Pattern 3: Template Method for Task Creation

**Before:** 100+ line functions with 95% identical code

**After:**
```python
# api/webhooks/common/task_creation/factory.py
class TaskFactory:
    async def create_task(self, command, payload, db, completion_handler, routing):
        # Common orchestration: ID generation, template loading, session creation,
        # task creation, flow ID, conversation, Claude Tasks sync, Redis push
        pass

# Usage in slack/utils.py (10 lines vs 99 lines)
async def create_slack_task(command, payload, db, completion_handler):
    factory = TaskFactory("slack", SLACK_WEBHOOK)
    routing = extract_slack_metadata(payload)
    return await factory.create_task(command, payload, db, completion_handler, routing)
```

**Benefit:** Reduces ~300 lines to ~100 shared + ~10 per domain

### Pattern 4: Builder Pattern for Block Kit

**Before:** 160-line function with nested dict construction

**After:**
```python
# api/webhooks/common/notifications/builder.py
class BlockKitBuilder:
    def header(self, text: str) -> 'BlockKitBuilder':
        self.blocks.append({"type": "header", "text": {"type": "plain_text", "text": text}})
        return self

    def section(self, text: str, markdown: bool = True) -> 'BlockKitBuilder':
        self.blocks.append({"type": "section", "text": {"type": "mrkdwn" if markdown else "plain_text", "text": text}})
        return self

class TaskCompletionBlockBuilder:
    def build(self, requires_approval: bool = False) -> list[dict]:
        self._add_header()
        self._add_summary()
        if requires_approval:
            self._add_approval_buttons()
        return self.builder.build()
```

**Benefit:** Cleaner, testable, reusable block construction

### Pattern 5: Consolidate Loop Prevention

**Before:** Three identical Redis tracking functions

**After:**
```python
# api/webhooks/common/loop_prevention/tracking.py
class MessageTracker:
    def __init__(self, domain: str):
        self.domain = domain

    async def is_posted_by_agent(self, message_id: str) -> bool:
        key = f"{self.domain}:posted_message:{message_id}"
        return await redis_client.exists(key)

    async def track_posted_message(self, message_id: str, ttl: int = 3600):
        key = f"{self.domain}:posted_message:{message_id}"
        await redis_client._client.setex(key, ttl, "1")

# Usage
slack_tracker = MessageTracker("slack")
await slack_tracker.is_posted_by_agent(message_ts)
```

**Benefit:** Single source of truth for loop prevention

### Pattern 6: Extract Formatting Utilities

**Before:** Truncation logic duplicated and inconsistent

**After:**
```python
# api/webhooks/common/formatting/truncation.py
class TextTruncator:
    @staticmethod
    def truncate(text: str, max_length: int, threshold: float = 0.8) -> str:
        if len(text) <= max_length:
            return text

        truncated = text[:max_length]
        last_period = truncated.rfind(".")
        last_newline = truncated.rfind("\n")
        truncate_at = max(last_period, last_newline)

        if truncate_at > max_length * threshold:
            truncated = truncated[:truncate_at + 1]

        return truncated + "\n\n_(message truncated)_"
```

**Benefit:** Consistent truncation across all webhooks

## Migration Strategy (TDD Approach)

### Phase 1: Extract Common Utilities (Week 1)
- Create new directory structure
- Implement shared utilities with comprehensive tests
- **No changes to existing code**
- Success: All new utilities have >90% test coverage

### Phase 2: Refactor Slack Utils (Week 2)
- Pilot refactoring using shared utilities
- Run existing tests to ensure no regressions
- Manual verification in staging
- Success: Slack utils reduced 30%+, all tests pass

### Phase 3: Refactor GitHub Utils (Week 3)
- Apply same patterns to GitHub
- Run tests and staging verification
- Success: GitHub utils reduced 30%+

### Phase 4: Refactor Jira Utils (Week 4)
- Complete refactoring with Jira
- Handle Jira-specific complexity
- Success: Jira utils reduced 30%+

### Phase 5: Extract Task Creation Factory (Week 5)
- Implement TaskFactory
- Update all three domains
- Success: Each create_*_task() < 20 lines

### Phase 6: Extract Block Kit Builder (Week 6)
- Implement BlockKitBuilder
- Refactor notification code
- Success: Block building code reduced 50%+

### Phase 7: Final Cleanup (Week 7)
- Remove dead code
- Update documentation
- Performance benchmarking
- Production deployment with monitoring

## Expected Outcomes

### Quantitative
- **Total line reduction: 2415 → 1900 lines (21% net reduction)**
- Slack: 946 → ~400 lines (58% reduction)
- GitHub: 645 → ~300 lines (53% reduction)
- Jira: 824 → ~400 lines (51% reduction)
- New shared: ~800 lines
- **Eliminate ~15 duplicated functions**
- **Reduce average complexity from 8 → 4**
- **Increase test coverage from ~60% to >85%**

### Qualitative
- Single source of truth for common logic
- Easier to fix bugs (one place vs three)
- Consistent patterns across webhooks
- Better testability and maintainability
- Clear separation of concerns
- Easy to add new webhook domains

## Rollback Plan

### Phase-by-Phase Rollback
- Each phase can be independently reverted
- Monitoring alerts trigger rollback if:
  - Webhook success rate < 95%
  - Task creation latency increase > 20%
  - New exception types in logs
  - Redis errors spike

## Critical Implementation Files

1. **NEW**: `api/webhooks/common/text_extraction/extractors.py` - Core text extraction (eliminates 95 lines)
2. **NEW**: `api/webhooks/common/task_creation/factory.py` - TaskFactory (consolidates 300 lines)
3. **MODIFY**: `api/webhooks/slack/utils.py` - Pilot refactoring target (946 lines)
4. **NEW**: `api/webhooks/common/signature/hmac_verifier.py` - Signature verification (65 → 60 shared)
5. **NEW**: `api/webhooks/common/notifications/builder.py` - Block Kit builder (simplifies 160-line function)
