# Review Command

## Trigger Patterns
- `@agent review`
- `@agent review this PR`
- `@agent code review`
- GitHub PR labeled with `agent-review`
- Pull request opened (if auto-review enabled)

## Behavior
Perform comprehensive code review focusing on quality, security, performance, and best practices.

## Parameters
- `--focus <area>`: Focus review on specific area
  - `security`: Security-focused review
  - `performance`: Performance-focused review
  - `types`: Type safety review
  - `tests`: Test coverage review
- `--strict`: Apply stricter review standards
- `--files <pattern>`: Review only matching files

## Execution Flow

### 1. Context Loading
- Fetch PR metadata (author, description, labels)
- Get PR diff and changed files list
- Load repository context and conventions
- Index changed files in knowledge graph

### 2. Analysis Phase
- Parse each changed file into AST
- Run security scan (if `--focus security` or default)
- Analyze code quality and complexity
- Check test coverage for changes
- Verify type safety and annotations
- Query knowledge graph for impact

### 3. Review Generation
- Categorize findings by severity
- Generate line-specific comments
- Create summary with recommendations
- Calculate quality score (0-10)

### 4. Result Posting
- Post review comment to PR
- Add inline comments for specific issues
- Add reaction emoji based on score:
  - 9-10: 🚀 (rocket)
  - 7-8: ✅ (check)
  - 5-6: ⚠️ (warning)
  - < 5: ❌ (x)

## Review Criteria

### Code Quality (Weight: 30%)
- Adherence to conventions
- Code clarity and readability
- Proper error handling
- No code smells
- Function complexity < 20

### Security (Weight: 25%)
- No OWASP vulnerabilities
- No hardcoded secrets
- Proper input validation
- Safe dependency usage

### Type Safety (Weight: 20%)
- All functions have type hints
- No `Any` types used
- Pydantic models use `strict=True`
- Type constraints enforced

### Test Coverage (Weight: 15%)
- Changed code has ≥ 80% coverage
- Edge cases tested
- Error conditions tested

### Performance (Weight: 10%)
- No obvious inefficiencies
- Proper async usage
- Database queries optimized
- No N+1 queries

## Output Format
```markdown
## Code Review by Agent 🤖

**Quality Score:** 8/10 ✅

**Review Focus:** General + Security
**Files Reviewed:** 5
**Issues Found:** 3 (0 critical, 2 medium, 1 low)

---

### 🟡 Medium Priority Issues

#### Type Safety Violation
**File:** `core/task_worker.py:28`
```python
async def process_task(task_data: dict, mcp_client: Any) -> None:
```
**Issue:** Using `Any` type violates strict typing policy.
**Recommendation:** Replace with `MCPClientProtocol` interface.

#### Missing Error Handling
**File:** `api/routes.py:45`
**Issue:** No exception handling for external API call.
**Recommendation:** Wrap in try/except with appropriate error response.

---

### 🔵 Low Priority / Suggestions

#### Code Clarity
**File:** `utils/parser.py:12`
**Issue:** Complex nested comprehension reduces readability.
**Recommendation:** Extract to named function for clarity.

---

### ✅ Strengths
- Excellent test coverage (92%)
- Proper async/await usage throughout
- Clear function names and structure
- Good separation of concerns

### 📊 Coverage Report
- Overall: 92% (+5% from base)
- New code: 88%
- Files with < 80%: None

### 🎯 Recommendations
1. Replace `Any` type with `MCPClientProtocol` ✓ Required
2. Add error handling for external API calls ✓ Required
3. Simplify complex comprehension → Optional

**Merge Recommendation:** ✅ Approve with minor changes

---
*Automated review by agent-bot • [View full report](#)*
```

## Example Usage

### Basic Review
```
@agent review
```
Triggers full review with all checks.

### Security-Focused
```
@agent review --focus security --strict
```
Detailed security analysis with strict standards.

### Specific Files
```
@agent review --files "*.py" --focus types
```
Type safety review for Python files only.

## Success Criteria
- Review completed within 5 minutes
- All critical issues identified
- Actionable feedback provided
- False positive rate < 10%
- Quality score accurate to ±1 point

## Escalation Conditions
- Critical security vulnerability → Block merge + notify team
- Test coverage < 50% → Require tests before review
- Unable to parse files → Report error and request manual review
- Review takes > 5 minutes → Cancel and suggest file scope reduction
