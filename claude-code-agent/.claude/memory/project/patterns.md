# Successful Patterns

> Learnings from verified successful implementations. Updated after confidence ≥ 90%.

---

## Code Patterns

### Async I/O
- Use async for all I/O operations (DB, HTTP, file)
- Prefer `asyncio.gather()` for parallel operations
- Always use async context managers for resource cleanup

### Error Handling
- Wrap external service calls with try/except for graceful degradation
- Log errors with full context before re-raising
- Use custom exception types for domain-specific errors

### Testing
- Write tests before implementation (TDD)
- Use fixtures for complex test data
- Test edge cases: empty, null, max values

---

## Agent Patterns

### Delegation
- Always provide context when delegating
- Include task_id for task directory lookups
- Specify expected output format

### Verification Loop
- Pass iteration count to verifier
- Only re-instruct failing criteria
- Write to memory only after successful verification

---

## Architecture Patterns

### Service Integration
- Use workflow orchestrator for cross-service operations
- Post status to originating service (Jira, GitHub)
- Send Slack notifications for async operations

---

*Last updated: System initialization*
