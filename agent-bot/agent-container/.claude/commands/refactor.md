# Refactor Command

## Trigger Patterns
- `@agent refactor [target]`
- `@agent simplify [code]`
- `@agent improve [code]`
- Code complexity > 20 (automatic suggestion)
- Duplicate code detected (automatic suggestion)

## Behavior
Refactor code to improve quality, maintainability, and performance while preserving functionality.

## Parameters
- `--target <scope>`: Refactoring scope
  - `function`: Single function
  - `class`: Entire class
  - `module`: Whole module
  - `auto`: Auto-detect (default)
- `--focus <area>`: Refactoring focus
  - `complexity`: Reduce complexity
  - `duplication`: Remove code duplication
  - `performance`: Optimize performance
  - `types`: Improve type safety
  - `structure`: Improve organization
- `--conservative`: Make minimal changes only
- `--test-first`: Generate tests before refactoring (recommended)

## Execution Flow

### 1. Analysis Phase
- Parse target code into AST
- Calculate complexity metrics
- Detect code smells and anti-patterns
- Identify duplication
- Query knowledge graph for dependencies
- Run existing tests for baseline

### 2. Planning Phase
- Identify refactoring opportunities
- Prioritize by impact vs. risk
- Create refactoring plan
- Estimate test coverage needs
- Check for breaking changes

### 3. Test Generation (if --test-first)
- Generate comprehensive tests for current behavior
- Verify all tests pass
- Achieve ≥90% coverage of refactoring target

### 4. Refactoring Execution
- Apply transformations incrementally
- Run tests after each change
- Rollback if tests fail
- Verify no behavioral changes

### 5. Verification
- Run full test suite
- Measure complexity improvement
- Verify type safety
- Check performance impact
- Generate refactoring report

## Refactoring Patterns

### Reduce Complexity
**Before (Complexity: 25):**
```python
def process_webhook(payload: dict) -> bool:
    if payload.get("type") == "github":
        if "pull_request" in payload:
            if payload["pull_request"].get("state") == "open":
                if payload["action"] in ["opened", "synchronize"]:
                    # ... 30 more lines
                    return True
    return False
```

**After (Complexity: 8):**
```python
def process_webhook(payload: dict) -> bool:
    if not is_github_pr_event(payload):
        return False

    return process_github_pr(payload)

def is_github_pr_event(payload: dict) -> bool:
    return (
        payload.get("type") == "github"
        and "pull_request" in payload
        and payload["pull_request"].get("state") == "open"
        and payload["action"] in ["opened", "synchronize"]
    )

def process_github_pr(payload: dict) -> bool:
    # ... extracted logic
    return True
```

### Remove Duplication
**Before:**
```python
# In file1.py
def post_to_github(data: dict) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(url, json=data, headers=headers)
    return response.status_code == 200

# In file2.py
def update_github_status(status: str) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(url, json={"status": status}, headers=headers)
    return response.status_code == 200
```

**After:**
```python
# In github_client.py
class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def post(self, endpoint: str, data: dict) -> bool:
        response = requests.post(endpoint, json=data, headers=self.headers)
        return response.status_code == 200

# In file1.py
def post_to_github(data: dict) -> bool:
    return github_client.post(url, data)

# In file2.py
def update_github_status(status: str) -> bool:
    return github_client.post(url, {"status": status})
```

### Improve Type Safety
**Before:**
```python
def process_data(data: dict) -> dict:
    result = {}
    for key, value in data.items():
        if isinstance(value, int):
            result[key] = value * 2
    return result
```

**After:**
```python
from pydantic import BaseModel, ConfigDict

class InputData(BaseModel):
    model_config = ConfigDict(strict=True)
    values: dict[str, int]

class OutputData(BaseModel):
    model_config = ConfigDict(strict=True)
    results: dict[str, int]

def process_data(data: InputData) -> OutputData:
    return OutputData(
        results={k: v * 2 for k, v in data.values.items()}
    )
```

## Refactoring Safety Rules
1. **Tests first:** Generate/verify tests before refactoring
2. **Incremental:** Make small, verifiable changes
3. **No behavioral changes:** Preserve exact functionality
4. **Always test:** Run tests after each transformation
5. **No mixed changes:** Separate refactoring from feature changes
6. **Preserve types:** Maintain or improve type safety
7. **Document intent:** Explain why, not what

## Output Format
```markdown
## Refactoring Report 🔧

**Target:** `core/webhook_handler.py::process_webhook()`
**Focus:** Complexity Reduction
**Approach:** Extract Method + Guard Clauses

### Before
- **Complexity:** 25 (Very High)
- **Lines:** 87
- **Test Coverage:** 65%

### After
- **Complexity:** 8 (Good) ⬇️ 68% reduction
- **Lines:** 45 ⬇️ 48% reduction
- **Test Coverage:** 92% ⬆️ +27%

### Changes Applied

#### 1. Extract Helper Functions
Created 3 new functions:
- `is_github_pr_event()`: Validate event type
- `extract_pr_metadata()`: Parse PR data
- `should_process_pr()`: Business logic check

#### 2. Early Returns
Replaced nested conditionals with guard clauses for clearer flow.

#### 3. Type Safety
Added Pydantic models for webhook payload structure.

### Tests Generated: 8
✅ All new tests passing
✅ All existing tests passing (42/42)
✅ No behavioral changes detected

### Files Modified
- `core/webhook_handler.py` (-42 lines, refactored)
- `core/webhook_models.py` (+35 lines, new types)
- `tests/test_webhook_handler.py` (+60 lines, new tests)

### Impact Analysis
**Affected Files:** 2
- `workers/task_worker.py`: Imports webhook_handler
- `tests/integration/test_e2e.py`: Integration test

**Breaking Changes:** None
**Migration Required:** No

### Quality Metrics
- ✅ Complexity reduced by 68%
- ✅ Test coverage increased 27%
- ✅ No duplication detected
- ✅ Type safety improved (100% annotated)
- ✅ All tests passing

### Recommendations
1. Consider extracting `GitHubClient` as separate class
2. Add integration test for full PR workflow
3. Document the webhook processing flow

**Refactoring Status:** ✅ Complete and Verified

---
*Refactoring follows TDD and maintains 100% backward compatibility*
```

## Example Usage

### Refactor Complex Function
```
@agent refactor --target function --focus complexity
```

### Remove Duplication
```
@agent refactor process_webhook --focus duplication --test-first
```

### Conservative Refactor
```
@agent refactor --conservative --focus types
```

## Success Criteria
- Complexity reduced by ≥30% (if focus=complexity)
- Duplication eliminated (if focus=duplication)
- All tests pass before and after
- No behavioral changes introduced
- Test coverage maintained or improved
- Refactoring completed within 10 minutes

## Escalation Conditions
- Complexity cannot be reduced → Explain architectural limitations
- Tests fail after refactoring → Rollback and report issue
- Breaking changes required → Request approval from maintainer
- Large refactoring (>200 lines) → Suggest breaking into phases
- Unclear intent → Request clarification on goals
