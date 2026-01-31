---
name: testing
description: Complete testing workflow covering test creation, validation, regression prevention, resilience, and E2E patterns. Use when writing tests, running test suites, or following TDD methodology.
---

Complete testing workflow covering all phases from test creation to validation, regression prevention, resilience testing, and E2E patterns.

## Quick Reference

- **Templates**: See [templates.md](templates.md) for reporting test results

## Testing Workflow Phases

### 1. Test Creation (TDD Red Phase)

Write failing tests BEFORE implementation based on requirements.

**Process:**

1. Parse requirement - Read user story, identify functionality, extract acceptance criteria
2. Identify test cases - Happy path, error cases, edge cases, boundary conditions, invalid inputs
3. Write failing tests - Create test file, write test functions with descriptive names, assert expected behavior
4. Verify tests fail - Run tests, confirm they fail for the RIGHT reason (not syntax errors, but because functionality doesn't exist)
5. Document expected behavior - Test names describe what should happen, comments link to requirements

**Test Types:**

- Unit Tests - Individual functions/methods in isolation
- Integration Tests - Component interactions
- Contract Tests - API boundaries
- Acceptance Tests - Business requirements

**Best Practices:**

- Test one thing per test
- Use descriptive names (e.g., `test_user_registration_creates_account`)
- Arrange-Act-Assert structure
- No implementation - tests only
- Verify failure before implementing
- Link to requirements in comments

### 2. Acceptance Validation

Validates that implementation meets business requirements and acceptance criteria.

**Process:**

1. Parse original requirement - Extract business need and acceptance criteria
2. Map criteria to tests - Link each criterion to specific test(s)
3. Verify all criteria met - Run tests and confirm each passes
4. Generate acceptance report - Create report showing criteria status

**Acceptance Criteria Formats:**

- User Story Format: "As a [role] I want [feature] So that [benefit]"
- Given-When-Then Format: "Given [context] When [action] Then [outcome]"

**Validation Checks:**

- All criteria have tests
- All tests pass
- Tests match criteria (verify test actually tests the criterion)
- Edge cases covered (negative, boundary, performance)

**Output Format:**

- Requirement summary
- Criteria status table (✅/❌/⚠️)
- Overall verdict (ACCEPTED/REJECTED/PARTIAL)
- Test coverage percentage
- Outstanding issues
- Recommendations

### 3. Regression Prevention

Ensures changes don't break existing functionality by verifying all tests pass and coverage doesn't decrease.

**Checks Performed:**

1. All existing tests pass - Every test must pass before changes accepted
2. Coverage doesn't decrease - Code coverage should not drop below current level
3. No new warnings - New code should not introduce warnings
4. Performance benchmarks maintained - Critical operations should not become slower
5. API contracts unchanged - Public APIs should remain compatible

**Blocking Conditions:**
Changes are BLOCKED if:

- ❌ Any test failure
- ❌ Coverage drop > 2%
- ❌ New deprecation warnings
- ❌ Performance regression > 10%
- ❌ Breaking API changes (unintentional)

**Workflow:**

- Before Changes: Run all tests, measure coverage baseline, run performance benchmarks
- After Changes: Run all tests, compare results with baseline, check coverage hasn't dropped, verify performance maintained

**Best Practices:**

- Run regression checks before every commit
- Maintain high test coverage (>80%)
- Fix flaky tests immediately
- Monitor performance trends
- Keep tests fast
- Test in isolation
- Version APIs for graceful deprecation

### 4. Resilience Testing

Tests system resilience - error handling, edge cases, load, recovery.

**Resilience Categories:**

1. Error Handling - Invalid inputs, type mismatches, missing fields
2. Network Resilience - Timeouts, transient failures, circuit breakers
3. Database Resilience - Connection failures, transaction rollbacks, deadlocks
4. Load Resilience - Concurrent requests, rate limiting, queue overflow
5. Recovery & Idempotency - State recovery, graceful degradation, idempotent operations
6. Edge Cases & Boundaries - Empty input, large input, boundary values, unicode

**Test Patterns:**

- Retry Pattern - Exponential backoff on failures
- Circuit Breaker - Fail fast when service is down
- Bulkhead - Isolate failures to prevent cascading

**Best Practices:**

- Test failure scenarios, not just happy path
- Use realistic failures (network timeouts, database errors)
- Test recovery mechanisms
- Test under load (concurrent requests, high volume)
- Test boundaries (min/max values, empty inputs)
- Test idempotency
- Verify error messages are clear and actionable

### 5. E2E Testing Patterns

End-to-end testing patterns and examples for browser, API, and CLI workflows.

**Test Types:**

- Browser-Based E2E (Playwright) - Full UI workflows testing complete user journeys
- API-Based E2E - Complete API workflows from authentication to data operations
- CLI-Based E2E - Command-line workflows from initialization to deployment

**Test Patterns:**

- Happy Path Test - Test successful completion of user workflow
- Error Recovery Test - Test user recovery from error scenarios
- Multi-User Scenario - Test collaborative workflows with multiple users

**Best Practices:**

- Test real user flows, not just API endpoints
- Use realistic test data
- Test error scenarios, not just happy path
- Keep tests independent
- Clean up after tests
- Run against staging environment
- Monitor test duration
- Use page objects for browser tests
- Verify visual elements with screenshots
- Test accessibility

## Complete TDD Workflow

1. **Red:** Create failing tests (Test Creation phase)
2. **Green:** Implement minimum code to pass tests
3. **Refactor:** Improve code while keeping tests green
4. **Resilience:** Add error handling and edge case tests (Resilience Testing phase)
5. **Validate:** Verify acceptance criteria met (Acceptance Validation phase)
6. **Guard:** Ensure no regressions (Regression Prevention phase)
7. **E2E:** Validate complete user flows (E2E Testing Patterns phase)

See `docs/TDD-METHODOLOGY.md` for detailed TDD methodology guide including Red-Green-Refactor cycle, todo creation templates, best practices, and common mistakes.

See examples.md for complete code examples and patterns.
